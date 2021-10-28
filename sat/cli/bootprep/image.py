"""
Implements the build and customization of IMS images from the input file.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
from collections import defaultdict, Counter
import logging
import math

from sat.apiclient import APIError, IMSClient
from sat.cached_property import cached_property
from sat.cli.bootprep.errors import ImageCreateCycleError, ImageCreateError
from sat.cli.bootprep.public_key import get_ims_public_key_id
from sat.session import SATSession
from sat.util import pester_choices
from sat.waiting import GroupWaiter, WaitingFailure

LOGGER = logging.getLogger(__name__)


class IMSImage:
    """An IMS image from a bootprep input file

    Attributes:
        image_data (dict): the data for an image from the bootprep input file
        ims_client (sat.apiclient.IMSClient): the IMSClient to make requests to
            the IMS API
        public_key_id (str): the id of the public key in IMS to use when
            building the image
        image_ids_to_delete (list of str): ids of IMS images to delete after this
            image has been successfully created
        dependent_images (list of IMSImage): the images that depend on this
            image before they can be created and customized
        dependency_images (list of IMSImage): the images that this image depends
            on before it can be created and customized
        image_create_job (dict or None): the IMS job of type 'create' for
            creating the image from a recipe, if applicable.
        image_create_success (bool): whether the image was successfully created
        image_configure_session (dict or None): the CFS session for customizing
            the image, if applicable.
        image_configure_success (bool): whether the image was successfully
            configured
    """

    def __init__(self, image_data, ims_client, public_key_id):
        """Create a new IMSImage

        Args:
            image_data (dict): the data for an image, already validated against
                the bootprep input file schema
            ims_client (sat.apiclient.IMSClient): the IMS API client to make
                requests to the IMS API
            public_key_id (str): the id of the public key in IMS to use when
                building the image
        """
        self.image_data = image_data
        self.ims_client = ims_client
        self.public_key_id = public_key_id

        # Populated by add_images_to_delete method
        # TODO (CRAYSAT-1198): Delete images after this image is fully created and configured
        self.image_ids_to_delete = []

        # These are populated later by add_dependent_image, which is called in find_image_dependencies
        self.dependent_images = []
        self.dependency_images = []

        # Set in begin_image_create and begin_image_configure
        self.image_create_job = None
        self.image_configure_session = None

        # Set by image_create_complete and image_configure_complete properties
        self._image_create_complete = False
        self.image_create_success = False
        self._image_configure_complete = False
        self.image_configure_success = False

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

    @cached_property
    def ims_base(self):
        """dict: the data for the base IMS recipe or image to build and/or customize"""
        resource_type = self.base_resource_type
        try:
            matching_base_resources = self.ims_client.get_matching_resources(
                resource_type, resource_id=self.ims_data.get('id'), name=self.ims_data.get('name'))
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

    @property
    def has_dependencies(self):
        """bool: whether this image has dependencies or not"""
        return len(self.dependency_images) > 0

    def add_dependency(self, dependency):
        """Add an image that this image depends on.

        This detects whether a cycle is created by adding this dependency.
        E.g., if image A depends on image B, and image B depends on C:

            A ---depends---> B ---depends---> C

        Then an attempt to add a dependency of image C on image A would
        introduce a cycle, or circular dependency.

        Raises:
            ImageCreateCycleError: if adding this dependency introduces a cycle
        """
        cycle_members = dependency.depends_on(self)
        if cycle_members:
            raise ImageCreateCycleError(cycle_members)

        # self depends on dependency
        self.dependency_images.append(dependency)
        # dependency has self as a dependent
        dependency.dependent_images.append(self)

    def depends_on(self, other_image, dependency_chain=None):
        """Return a chain of dependencies if this image depends on the other image.

        Args:
            other_image (IMSImage): the other image to check if this image
                depends on.
            dependency_chain (list of str): the list of image names traversed
                so far to reach this image

        Returns:
            list of str: the list of image names in the dependency string or the empty
                list if this image does not depend on the other image
        """
        # Add this image to the dependency chain being constructed
        dependency_chain = (dependency_chain or []) + [self.name]

        # Base case of recursion: an image depends on itself
        if self == other_image:
            return dependency_chain

        for dependency in self.dependency_images:
            # Find out if this dependency depends on the other image
            possible_dependency_chain = dependency.depends_on(other_image, dependency_chain)
            if possible_dependency_chain:
                return possible_dependency_chain

        # There is no chain of dependencies that leads to other_image
        return []

    def begin_image_create(self):
        """Launch the image creation job in IMS

        Returns:
            None. Sets `self.image_create_job` for querying status of job.

        Raises:
            ImageCreateError: if there is a failure to create the IMS job
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
            LOGGER.info(f'Created IMS image creation job with id={self.image_create_job.get("id")}')
        except APIError as err:
            raise ImageCreateError(str(err))

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
            raise ImageCreateError(f'Unknown image create job id for image {self.name}')

        image_create_job_id = self.image_create_job['id']
        try:
            job_details = self.ims_client.get_job(image_create_job_id)
        except APIError as err:
            raise ImageCreateError(f'Failed to get status of IMS job with ID {image_create_job_id}: {err}')

        if job_details.get('status') in ('error', 'success'):
            self._image_create_complete = True
            self.image_create_success = success = job_details.get('status') == 'success'

            LOGGER.log(logging.INFO if success else logging.ERROR,
                       f'Creation of image {self.created_image_name} '
                       f'{("failed", "succeeded")[success]}.')

        return self._image_create_complete

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

        # TODO (CRAYSAT-1198): Launch the CFS session to configure the image
        LOGGER.info(f'Image configuration not yet implemented. Image will not '
                    f'be configured.')
        self.image_configure_session = None

    @property
    def image_configure_complete(self):
        """bool: True if the image has been configured

        Raises:
            ImageCreateError: if the status of the CFS session cannot be queried
        """
        if self._image_configure_complete:
            return True

        # TODO (CRAYSAT-1198): query cfsclient to see if session is complete
        LOGGER.info(f'Image configuration status check not yet implemented.')
        self._image_configure_complete = True
        self.image_configure_success = True

        return self._image_configure_complete

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
            return self.image_configure_complete
        else:
            return False

    @property
    def completed_successfully(self):
        """bool: whether this image was created and configured successfully"""
        return self.image_create_success and self.image_configure_success


def validate_unique_image_names(input_images):
    """Validate that the input images all have unique names

    Images must have unique names, so that they can be referenced by name in the
    session templates in a bootprep input file.

    Args:
        input_images (list of IMSImage): the input images in the bootprep input instance

    Raises:
        ImageCreateError: if the images do not have unique names
    """
    counts_by_name = Counter(image.name for image in input_images)
    non_unique_names = [name for name, count in counts_by_name.items() if count > 1]
    if non_unique_names:
        raise ImageCreateError('Names of images to create must be unique. Non-unique names: '
                               f'{", ".join(non_unique_names)}')


def get_ims_images_by_name(ims_client):
    """Get a dict mapping from name to IMS image record for all existing IMS images.

    Args:
        ims_client (sat.apiclient.IMSClient): the IMS API client to query

    Returns:
        dict: a dictionary mapping from IMS image name to the IMS image record
            data dictionary

    Raises:
        ImageCreateError: if unable to query IMS for existing images
    """
    try:
        all_ims_images = ims_client.get_matching_resources('image')
    except APIError as err:
        raise ImageCreateError(f'Failed to query IMS for existing images: {err}')

    ims_images_by_name = defaultdict(list)
    for ims_image in all_ims_images:
        ims_images_by_name[ims_image.get('name')].append(ims_image)

    return dict(ims_images_by_name)


def handle_existing_images(ims_client, input_images, overwrite, skip, dry_run):
    """Handle any images that have a name collision with images already in IMS.

    Although IMS identifies images by a uuid field, 'id', bootprep requires that
    all images have unique names, so that the admin can always refer to an image
    by its name rather than an non-descriptive id.

    Args:
        ims_client (sat.apiclient.IMSClient): the IMS API client to use to get
            info about existing public keys or to create new ones
        input_images (list of IMSImage): the input images in the bootprep input
            instance
        overwrite (bool): if True, existing images should be overwritten
        skip (bool): if True, existing images should be overwritten
        dry_run (bool): whether this is a dry-run or not

    Returns:
        list of IMSImage: the list of images that should be created

    Raises:
        ImageCreateError: if unable to query IMS for existing images, or if
            some images already exist and user chose to abort
    """
    ims_images_by_name = get_ims_images_by_name(ims_client)

    existing_input_images = [input_image for input_image in input_images
                             if input_image.name in ims_images_by_name]

    if not existing_input_images:
        return input_images

    verb = ('will be', 'would be')[dry_run]

    existing_input_names = [image.name for image in existing_input_images]
    if not overwrite and not skip:
        answer = pester_choices(f'One or more images already exist in IMS with the following '
                                f'names: {", ".join(existing_input_names)}. Would you like to skip, '
                                f'overwrite, or abort?', ('skip', 'overwrite', 'abort'))
        if answer == 'abort':
            raise ImageCreateError('User chose to abort')
        skip = answer == 'skip'
        overwrite = answer == 'overwrite'

    msg_template = (f'Images with the following names already exist in IMS and '
                    f'{verb} %(action)s: {", ".join(existing_input_names)}')
    if overwrite:
        failed_overwrites = []
        LOGGER.info(msg_template, {'action': 'overwritten'})
        for existing_input_image in existing_input_images:
            try:
                existing_input_image.add_images_to_delete(ims_images_by_name[existing_input_image.name])
            except ImageCreateError as err:
                LOGGER.error(str(err))
                failed_overwrites.append(existing_input_image)

        if failed_overwrites:
            raise ImageCreateError(f'Failed to set up overwrite of {len(failed_overwrites)} '
                                   f'input image(s).')

        return input_images
    elif skip:
        LOGGER.info(msg_template, {'action': 'skipped'})
        # Create all images that do not already exist
        return [image for image in input_images if image.name not in existing_input_names]


def find_image_dependencies(input_images):
    """Find and record any dependencies between images.

    For example, suppose the bootprep input file looks like this:

    images:
    - name: compute-gpu
      ims:
        is_recipe: false
        name: compute-base
      configuration: compute-gpu
      configuration_group_names:
      - Compute
    - name: compute-no-gpu
      ims:
        is_recipe: false
        name: compute-base
      configuration: compute-no-gpu
      configuration_group_names:
      - Compute
    - name: compute-base
      ims:
        is_recipe: true
        name: compute-recipe

    In this case, the compute-gpu and compute-no-gpu images both depend on the
    compute-base image being built first from recipe, and then each customizes
    it with a different configuration.

    Args:
        input_images (list of IMSImage): the list of images from the bootprep
            input file that are to be built.

    Returns:
        None. The input_images will have their dependency_images and
        dependent_images attributes populated.

    Raises:
        ImageCreateError: if the images defined in the input file have circular
            dependencies.
    """
    input_images_by_name = {input_image.name: input_image
                            for input_image in input_images}
    cycles_exist = False
    for image in input_images:
        # If it is built from a recipe, or specifies an image by its id, then
        # it does not depend on any names images in the input file.
        if image.base_is_recipe or 'id' in image.ims_data:
            continue

        # Since 'id' is not present, 'name' must be present according to the schema
        base_image_name = image.ims_data['name']
        if base_image_name in input_images_by_name:
            LOGGER.info(f'Image named {image.name} depends on image named {base_image_name} '
                        f'which will also be created by this command.')
            try:
                image.add_dependency(input_images_by_name[base_image_name])
            except ImageCreateCycleError as err:
                LOGGER.error(str(err))
                cycles_exist = True

    if cycles_exist:
        raise ImageCreateError('Circular dependencies exist in images to be created. '
                               'Resolve the circular dependencies and try again.')


def validate_image_ims_bases(input_images):
    """Validate that the ims bases are valid for the given input images

    Args:
        input_images (list of IMSImage): the IMSImages which should have their
            IMS base validated. These images should be just the images without
            dependencies on other images from the input, since an image with
            dependencies depends on images that are not yet in IMS and will be
            created by other images in the input file.

    Returns: None

    Raises:
        ImageCreateError: if any images do not have a valid IMS base
    """
    failed_images = []
    for image in input_images:
        try:
            # Accessing this property for the first time queries the IMS API
            ims_base = image.ims_base
            LOGGER.info(f'Found IMS base for {image}: {image.base_description}: ')
            LOGGER.debug(f'IMS base for {image}: {ims_base}')
        except ImageCreateError as err:
            failed_images.append(image)
            LOGGER.error(f'Failed to find match in IMS for {image.base_description}: {err}')

    if failed_images:
        raise ImageCreateError(f'Failed to find match in IMS for {len(failed_images)} '
                               f'input images')


class ImageCreationGroupWaiter(GroupWaiter):
    """Kicks off image creation in IMS and waits for jobs to complete

    This will also handle creating jobs for dependent images once their
    dependencies have completed.
    """

    def __init__(self, members, timeout, poll_interval=10, retries=0):
        """Create a new ImageCreationWaiter

        This just overrides the default for poll_interval from the superclass.

        Args:
            members (list of IMSImage): the list of IMSImage objects without
                dependencies to create first.
            timeout: See GroupWaiter docstring
            poll_interval: See GroupWaiter docstring
            retries: See GroupWaiter docstring
        """
        super().__init__(members, timeout, poll_interval, retries)

    def condition_name(self):
        """str: the name of the condition being waited for"""
        return 'creation of IMS images'

    def pre_wait_action(self):
        """Before beginning to wait, start the image builds"""
        for image in self.members:
            try:
                image.begin_image_create()
            except ImageCreateError as err:
                LOGGER.error(str(err))
                self.failed.add(image)

    def member_has_completed(self, member):
        """Check whether the given IMSImage member has been created and/or configured

        Args:
            member (IMSImage): the IMS image to check for completion

        Raises:
            WaitingFailure: if a fatal error occurred while getting status of
                member, or member failed at some point in creation.
        """
        # Raising WaitingFailure causes the image to be added to `self.failed`
        # and an error message will be logged that mentions which member failed
        try:
            if member.has_completed:
                if member.completed_successfully:
                    for dependent in member.dependent_images:
                        dependent.begin_image_create()
                        self.pending.add(dependent)
                    return True
                else:
                    raise WaitingFailure(f'creation failed')
            return False
        except ImageCreateError as err:
            raise WaitingFailure(f'status check failed: {err}')


def create_images(instance, args):
    """Create and customize IMS images defined in the given instance

    Args:
        instance (dict): The full bootprep input dictionary loaded from the
            input file and already validated against the schema.
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootprep subcommand.

    Returns: None

    Raises:
        ImageCreateError: if there is a failure to create images
    """
    # The 'images' key is optional in the instance
    instance_images = instance.get('images')
    if not instance_images:
        LOGGER.info('Given input did not define any IMS images')
        return

    ims_client = IMSClient(SATSession())

    ims_public_key_id = get_ims_public_key_id(ims_client, public_key_id=args.public_key_id,
                                              public_key_file_path=args.public_key_file_path,
                                              dry_run=args.dry_run)
    LOGGER.info(f'Using IMS public key with id {ims_public_key_id}')

    input_images = [IMSImage(image, ims_client, ims_public_key_id) for image in instance_images]
    validate_unique_image_names(input_images)
    images_to_create = handle_existing_images(ims_client, input_images, args.overwrite_images,
                                              args.skip_existing_images, args.dry_run)

    create_verb = ('Creating', 'Would create')[args.dry_run]
    LOGGER.info(f'{create_verb} {len(images_to_create)} images.')

    if not input_images:
        LOGGER.info('Given input did not define any IMS images')
        return

    # This can raise ImageCreateError if there are any cycles
    find_image_dependencies(images_to_create)

    images_without_dependencies = [image for image in images_to_create
                                   if not image.has_dependencies]

    verb = ("will be", "would be")[args.dry_run]
    LOGGER.info(f'Of the {len(images_to_create)} that {verb} created, '
                f'{len(images_without_dependencies)} have no dependencies '
                f'and {verb} created first.')

    # Raises ImageCreateError if validation of IMS bases fails
    validate_image_ims_bases(images_without_dependencies)

    if args.dry_run:
        LOGGER.info("Dry run, not creating images.")
        return

    # Default to no timeout since it's unknown how long image creation could take
    waiter = ImageCreationGroupWaiter(images_without_dependencies, math.inf)
    LOGGER.info('Creating images')
    waiter.wait_for_completion()
    if waiter.failed:
        raise ImageCreateError(f'Creation of {len(waiter.failed)} images failed')
    else:
        LOGGER.info('Image creation completed successfully')
