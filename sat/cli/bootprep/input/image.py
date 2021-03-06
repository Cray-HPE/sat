#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Defines class for images defined in the input file.
"""
import warnings

from kubernetes.client import CoreV1Api
from kubernetes.config import load_kube_config, ConfigException
from yaml import YAMLLoadWarning

from sat.apiclient import APIError
from sat.cached_property import cached_property
from sat.cli.bootprep.errors import ImageCreateError
from sat.cli.bootprep.image import LOGGER
from sat.waiting import (
    DependencyGroupMember,
    WaitingFailure
)


class InputImage(DependencyGroupMember):
    """An IMS image from a bootprep input file

    Attributes:
        image_data (dict): the data for an image from the bootprep input file
        ims_client (sat.apiclient.IMSClient): the IMSClient to make requests to
            the IMS API
        cfs_client (sat.apiclient.CFSClient): the CFSClient to make requests to
            the CFS API
        public_key_id (str): the id of the public key in IMS to use when
            building the image
        image_ids_to_delete (list of str): ids of IMS images to delete after this
            image has been successfully created
        image_create_job (dict or None): the IMS job of type 'create' for
            creating the image from a recipe, if applicable.
        finished_job_details (dict or None): the IMS job record for the finished
            job. This is set by accessing the image_create_complete property
            once it is finished.
        image_configure_session (dict or None): the CFS session for customizing
            the image, if applicable.
        image_create_success (bool): whether the image was successfully created
        image_configure_success (bool): whether the image was successfully
            configured
        final_image_id (str): the final image ID after creation, customization,
            and renaming have been completed, as applicable
    """

    def __init__(self, image_data, ims_client, cfs_client):
        """Create a new InputImage

        Args:
            image_data (dict): the data for an image, already validated against
                the bootprep input file schema
            ims_client (sat.apiclient.IMSClient): the IMS API client to make
                requests to the IMS API
            cfs_client (sat.apiclient.CFSClient): the CFS API client to make
                requests to the CFS API
        """
        super().__init__()

        self.image_data = image_data
        self.ims_client = ims_client
        self.cfs_client = cfs_client

        # TODO: Fix up this error-prone way of requiring that we set public_key_id later
        self.public_key_id = None

        # Populated by add_images_to_delete method
        self.image_ids_to_delete = []

        # Set in begin_image_create and begin_image_configure
        self.image_create_job = None
        self.finished_job_details = None
        self.image_configure_session = None

        # Set by image_create_complete and image_configure_complete properties
        self._image_create_complete = False
        self.image_create_success = False
        self._image_configure_complete = False
        self.image_configure_success = False

        # Set by rename_configured_image
        self.final_image_id = None

    @property
    def name(self):
        """str: the name of the final resulting image"""
        # 'name' is a required property in the bootprep schema
        return self.image_data['name']

    def __str__(self):
        return f'image named {self.name}'

    @property
    def created_image_name(self):
        """str: the name of the created image prior to configuration, if applicable"""
        if self.configuration:
            return f'{self.name}-pre-configuration'
        return self.name

    @property
    def configuration(self):
        """str or None: the configuration to apply to the image"""
        return self.image_data.get('configuration')

    @property
    def configuration_group_names(self):
        """list of str or None: the name of the Ansible groups to configure

        Note that the bootprep input schema ensures this will be non-None if the
        configuration is specified.
        """
        return self.image_data.get('configuration_group_names')

    @property
    def ims_data(self):
        """dict: the data that defines the base IMS image or recipe"""
        return self.image_data['ims']

    @property
    def base_is_recipe(self):
        """bool: whether the starting point is a recipe in IMS or an image"""
        return self.ims_data['is_recipe']

    @property
    def base_resource_type(self):
        """str: the type of the base resource we are starting from, either 'image' or 'recipe'"""
        return ('image', 'recipe')[self.base_is_recipe]

    @property
    def base_description(self):
        """str: a human-readable description of the base we are starting from"""
        for param in ('id', 'name'):
            if param in self.ims_data:
                return f'{self.base_resource_type} with {param}={self.ims_data[param]}'

        # This shouldn't happen since schema requires 'id' or 'name'
        return self.base_resource_type

    # TODO: Reduce duplication of code between here and ProductInputConfigurationLayer
    @cached_property
    def k8s_api(self):
        """kubernetes.client.CoreV1Api: a kubernetes core API client"""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            raise ImageCreateError(f'Failed to load Kubernetes config which is required '
                                   f'to query image build status: {err}')

        return CoreV1Api()

    @cached_property
    def ims_base(self):
        """dict: the data for the base IMS recipe or image to build and/or customize"""
        resource_type = self.base_resource_type
        try:
            matching_base_resources = self.ims_client.get_matching_resources(
                resource_type, resource_id=self.ims_data.get('id'),
                name=self.ims_data.get('name'))
        except APIError as err:
            raise ImageCreateError(err)

        if len(matching_base_resources) == 0:
            raise ImageCreateError(f'Found no matches for {self.base_description}')
        elif len(matching_base_resources) > 1:
            raise ImageCreateError(f'Found {len(matching_base_resources)} matches for {self.base_description}. '
                                   f'This {self.base_resource_type} must be specified by "id".')

        return matching_base_resources[0]

    def add_images_to_delete(self, images_to_delete):
        """Add IMS images that should be deleted after this image is created and configured.

        Args:
            images_to_delete (list of dict): the IMS image records for IMS
                images that should be deleted after this image is created and
                configured because they have the same name.

        Returns: None

        Raises:
            ImageCreateError: if any image in `images_to_delete` is missing the
                'id' key, which is needed to delete it.
        """
        if any('id' not in image for image in images_to_delete):
            raise ImageCreateError(
                f'One or more images with name {self.name} are missing the "id" '
                f'property, which is required for deletion.'
            )

        self.image_ids_to_delete = [image['id'] for image in images_to_delete]

    def begin_image_create(self):
        """Launch the image creation job in IMS

        Returns:
            None. Sets `self.image_create_job` for querying status of job.

        Raises:
            WaitingFailure: if there is a failure to create the IMS job
        """
        if not self.base_is_recipe:
            LOGGER.info(f'Base for image with name {self.name} is a pre-built image.')
            self._image_create_complete = True
            self.image_create_success = True
            return

        LOGGER.info(f'Launching IMS job to create image')

        try:
            self.image_create_job = self.ims_client.create_image_build_job(
                self.created_image_name, self.ims_base['id'], self.public_key_id
            )
            LOGGER.info(f'Created IMS image creation job with ID {self.image_create_job.get("id")}')
        except APIError as err:
            raise WaitingFailure(str(err)) from err

    @property
    def image_create_complete(self):
        """bool: True if the base (unconfigured) image has been created

        Raises:
            ImageCreateError: if the status of the image create job can't be queried
        """
        if self._image_create_complete:
            return True

        if not self.image_create_job:
            raise ImageCreateError(f'No image create job was created for image {self.name}')
        elif 'id' not in self.image_create_job:
            raise ImageCreateError(f'Unknown image create job ID for image {self.name}')

        image_create_job_id = self.image_create_job['id']
        try:
            job_details = self.ims_client.get_job(image_create_job_id)
        except APIError as err:
            raise ImageCreateError(f'Failed to get status of IMS job with ID {image_create_job_id}: {err}')

        if job_details.get('status') in ('error', 'success'):
            self._image_create_complete = True
            self.image_create_success = job_details.get('status') == 'success'
            self.finished_job_details = job_details
            self.log_created_image_info()

        return self._image_create_complete

    @property
    def ims_resultant_image_id(self):
        """str: the id of the image resulting from the IMS image creation step"""
        if not self.finished_job_details:
            return None
        return self.finished_job_details.get('resultant_image_id')

    @property
    def image_id_to_configure(self):
        """str: the IMS id of the image to be configured"""
        # If the base is a recipe, then we want to configure the built image
        if self.base_is_recipe:
            return self.ims_resultant_image_id
        # Otherwise, we just configure the base image
        return self.ims_base['id']

    def log_created_image_info(self):
        """Log information about the created image

        Returns:
            None
        """
        log_msg = (f'Creation of image {self.created_image_name} '
                   f'{("failed", "succeeded")[self.image_create_success]}')

        if self.image_create_success:
            created_image_id = self.ims_resultant_image_id
            if created_image_id:
                LOGGER.info(f'{log_msg}: ID {created_image_id}')
            else:
                LOGGER.info(log_msg)
                LOGGER.warning(f'Failed to determine id of created image')
        else:
            LOGGER.error(log_msg)

    def clean_up_image_create_job(self):
        """Clean up the image create job if it was successful

        Returns:
            None
        """
        if not self.image_create_job:
            return

        image_create_job_id = self.image_create_job.get('id')
        if not image_create_job_id:
            LOGGER.warning(f'Unable to clean up image create job for image '
                           f'{self.created_image_name} due to missing ID.')
            return

        ims_job_description = f'completed IMS job with ID {image_create_job_id}'

        if self.image_create_success:
            LOGGER.info(f'Deleting {ims_job_description }')
            try:
                self.ims_client.delete('jobs', image_create_job_id)
            except APIError as err:
                LOGGER.warning(f'Failed to delete {ims_job_description}: {err}')
            else:
                LOGGER.info(f'Deleted {ims_job_description}')
        else:
            LOGGER.info(f'Not deleting failed {ims_job_description} to allow debugging')

    def begin_image_configure(self):
        """Launch the CFS session to configure the image

        Returns:
            None. Sets `self.image_configure_session` for querying status of session.

        Raises:
            ImageCreateError: if there is a failure to create the CFS session
        """
        if not self.configuration:
            LOGGER.info(f'Image {self.name} does not need configuration.')
            self._image_configure_complete = True
            self.image_configure_success = True
            return

        session_name = self.cfs_client.get_valid_session_name()
        LOGGER.info(f'Creating CFS session {session_name} to configure image {self.name}')

        try:
            self.image_configure_session = self.cfs_client.create_image_customization_session(
                self.configuration, self.image_id_to_configure, self.configuration_group_names, self.name)
        except APIError as err:
            raise ImageCreateError(f'Failed to launch image customization CFS session: {err}')

        LOGGER.info(f'Created CFS session {session_name} to configure image {self.name}')

    @property
    def image_configure_complete(self):
        """bool: True if the image has been configured

        Raises:
            ImageCreateError: if the status of the CFS session cannot be queried
        """
        if self._image_configure_complete:
            return True

        try:
            self.image_configure_session.update_status(self.k8s_api)
        except APIError as err:
            raise ImageCreateError(str(err))

        self._image_configure_complete = self.image_configure_session.complete
        self.image_configure_success = self.image_configure_session.succeeded

        return self._image_configure_complete

    def rename_configured_image(self):
        """Rename the image to the desired final name if it has been configured

        CFS does not allow us to specify the name of the resulting IMS image. It
        always just appends "_cfs_${CFS_CONFIGURATION_NAME}". In order to get
        a final, configured image with the desired name, rename it in IMS.
        """
        # If the image did not specify a configuration, it was already created
        # with the desired name, so no rename is necessary.
        if not self.configuration:
            LOGGER.debug(f'No rename necessary for unconfigured image named {self.name}')
            self.final_image_id = self.ims_resultant_image_id
            return

        configured_image_id = self.image_configure_session.resultant_image_id
        if not configured_image_id:
            raise ImageCreateError('Failed to determine ID of configured image.')

        LOGGER.info(f'Renaming configured image with ID {configured_image_id} to {self.name}')

        try:
            self.final_image_id = self.ims_client.rename_image(configured_image_id, self.name)
        except APIError as err:
            raise ImageCreateError(f'Failed to rename configured image with ID {configured_image_id} '
                                   f'from {self.created_image_name} to {self.name}: {err}')

    def delete_overwritten_images(self):
        """Delete the images which were marked to be overwritten

        This is called once this image is fully created and configured to delete
        any images which have the same name as this image which were requested
        to be overwritten.

        Returns:
            None
        """
        for image_id in self.image_ids_to_delete:
            try:
                LOGGER.info(f'Deleting image with ID {image_id} which was overwritten '
                            f'by a new image named {self.name}')
                self.ims_client.delete_image(image_id)
            except APIError as err:
                # This could cause a later failure when referring to images by
                # name in BOS session templates, but not necessarily.
                LOGGER.warning(f'Failed to delete image named {self.name} with ID {image_id}: {err}')

    def log_final_image_info(self):
        """Log information about the final configured image."""
        log_msg = (f'Creation of image {self.name} '
                   f'{("failed", "succeeded")[self.completed_successfully]}')

        if self.completed_successfully:
            LOGGER.info(f'{log_msg}: ID {self.final_image_id}')
        else:
            debug_command = self.image_configure_session.get_suggested_debug_command()
            if debug_command and not self.image_configure_success:
                LOGGER.info('Logs from the failed image configuration K8s container '
                            'for image %s may be viewed with \'%s\'.',
                            self.name, debug_command)

            LOGGER.error(log_msg)

    @property
    def has_completed(self):
        """Check whether image is complete, kicking off next stage if necessary

        Returns:
            bool: True if the image creation and configuration is done or failed,
                False otherwise

        Raises:
            ImageCreateError: if there is a failure checking progress or starting
                the next stage of image creation.
        """
        if self.image_create_complete:
            if not self.image_create_success:
                # If image creation was not successful do not start configuration
                return True

            if not self.image_configure_session:
                # This properly handles whether configuration is needed or not
                self.begin_image_configure()

            if self.image_configure_complete:
                if self.image_configure_success:
                    self.rename_configured_image()
                    self.delete_overwritten_images()

                self.log_final_image_info()
                return True

            return False
        else:
            return False

    @property
    def completed_successfully(self):
        """bool: whether this image was created and configured successfully"""
        return self.image_create_success and self.image_configure_success

    begin = begin_image_create
