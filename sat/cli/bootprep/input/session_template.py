#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
Defines class for session templates defined in the input file.
"""
from abc import abstractmethod
from copy import deepcopy
import re

from sat.apiclient import APIError
from sat.cached_property import cached_property
from sat.cli.bootprep.constants import CONFIGURATIONS_KEY, IMAGES_KEY
from sat.cli.bootprep.input.base import (
    BaseInputItem,
    BaseInputItemCollection,
    Validatable,
    jinja_rendered,
    provides_context
)
from sat.cli.bootprep.errors import InputItemCreateError, InputItemValidateError, SessionTemplateCreateError
from sat.util import get_val_by_path


class InputSessionTemplate(BaseInputItem):
    """A BOS session template from a bootprep input file.

    Attributes:
        data (dict): the data for a session template, already
            validated against the bootprep schema
        bos_client (sat.apiclient.BOSClientCommon): the BOS API client to make
            requests to the BOS API
        ims_client (sat.apiclient.IMSClient): the IMS API client to make
            requests to the IMS API
        cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API client to make
            requests to the CFS API
    """
    description = 'BOS session template'
    report_attrs = ['name', 'configuration']

    def __init__(self, data, instance, index, jinja_env, bos_client, cfs_client, ims_client, **kwargs):
        """Create a new InputSessionTemplate.

        Args:
            data (dict): the data defining the item from the input file, already
                validated by the bootprep schema.
            instance (sat.cli.bootprep.input.instance.InputInstance): a reference
                to the full instance loaded from the input file
            index (int): the index of the item in the collection in the instance
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            bos_client (sat.apiclient.BOSClientCommon): the BOS API client
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API client
            ims_client (sat.apiclient.IMSClient): the IMS API client
            **kwargs: additional keyword arguments
        """
        super().__init__(data, instance, index, jinja_env, **kwargs)
        self.bos_client = bos_client
        self.cfs_client = cfs_client
        self.ims_client = ims_client

        # Additional context to be used when rendering Jinja2 templated properties
        self.jinja_context = {}

    @staticmethod
    def get_item(data, *args, **kwargs):
        """Get an instance of the appropriate subclass based on the data."""
        if isinstance(data['image'], str):
            return InputSessionTemplateV1(data, *args, **kwargs)
        else:
            return InputSessionTemplateV2(data, *args, **kwargs)

    @property
    @jinja_rendered
    def configuration(self):
        """str: the configuration specified for the session template"""
        # the 'configuration' property is required by the schema
        return self.data['configuration']

    @property
    @jinja_rendered
    def boot_sets(self):
        """dict: the boot sets specified for the session template"""
        # the 'bos_parameters' property is required, and 'boot_sets' is required within that
        return self.data['bos_parameters']['boot_sets']

    @property
    @abstractmethod
    def image_record(self):
        """dict: the image record from IMS for this session template"""

    @Validatable.validation_method()
    def validate_rootfs_provider_has_value(self, **_):
        """Validate that the rootfs_provider is not an empty string

        Raises:
            InputItemValidateError: if the rootfs_provider is an empty string
        """
        for boot_set_name, boot_set_data in self.boot_sets.items():
            if 'rootfs_provider' in boot_set_data and not boot_set_data['rootfs_provider']:
                raise InputItemValidateError(f'The value of rootfs_provider for boot set '
                                             f'{boot_set_name} cannot be an empty string')

    @Validatable.validation_method()
    def validate_rootfs_provider_passthrough_has_value(self, **_):
        """Validate that the rootfs_provider_passthrough is not an empty string

        Raises:
            InputItemValidateError: if the rootfs_provider_passthrough is an empty string
        """
        for boot_set_name, boot_set_data in self.boot_sets.items():
            if ('rootfs_provider_passthrough' in boot_set_data
                    and not boot_set_data['rootfs_provider_passthrough']):
                raise InputItemValidateError(f'The value of rootfs_provider_passthrough for boot set '
                                             f'{boot_set_name} cannot be an empty string')

    @Validatable.validation_method()
    def validate_configuration_exists(self, **_):
        """Validate that the configuration specified for this session template exists.

        Raises:
            InputItemValidateError: if the configuration does not exist
        """
        # Assume configs from input file exist when not being excluded and in dry-run mode
        input_configs_exist = CONFIGURATIONS_KEY in self.instance.limit and self.instance.dry_run

        # Check if the configuration would be created by the input file
        if input_configs_exist and self.configuration in self.instance.input_configuration_names:
            return

        try:
            resp = self.cfs_client.get('configurations', self.configuration, raise_not_ok=False)
            if not resp.ok:
                if resp.status_code == 404:
                    raise InputItemValidateError(f'Configuration {self.configuration} specified for '
                                                 f'{self} does not exist.')
                else:
                    self.cfs_client.raise_from_response(resp)
        except (APIError, ValueError) as err:
            raise InputItemValidateError(f'An error occurred while querying configuration '
                                         f'{self.configuration}: {err}')

    @abstractmethod
    def validate_image_exists(self, **_):
        """Validate that the image specified for this session template exists.

        Returns:
            dict: information about the image to make available in an `image`
                variable in Jinja2 context when rendering the name of the
                session template.

        Raises:
            InputItemValidateError: if the image cannot be verified to exist
        """

    def get_create_item_data(self):
        """Get the data to pass to the BOS API to create this session template.

        Returns:
            dict: the data to pass to the BOS API to create the session template
        """
        api_data = {
            'cfs': {'configuration': self.configuration},
            'enable_cfs': True,
            'name': self.name,
            'boot_sets': {}
        }

        for boot_set_name, boot_set_data in self.boot_sets.items():
            # Must deepcopy to avoid every boot set sharing the same dict
            boot_set_api_data = deepcopy(self.bos_client.get_base_boot_set_data())
            try:
                image_record = self.image_record
            except InputItemValidateError as err:
                # If it's a dry-run, the image may not exist yet.
                if self.instance.dry_run:
                    boot_set_etag = 'TBD'
                    boot_set_path = 'TBD'
                    boot_set_type = 'TBD'
                else:
                    raise InputItemCreateError(str(err)) from err
            else:
                boot_set_etag = get_val_by_path(image_record, 'link.etag')
                boot_set_path = get_val_by_path(image_record, 'link.path')
                boot_set_type = get_val_by_path(image_record, 'link.type')

            boot_set_api_data.update({
                'etag': boot_set_etag,
                'path': boot_set_path,
                'type': boot_set_type
            })
            boot_set_api_data.update(boot_set_data)
            api_data['boot_sets'][boot_set_name] = boot_set_api_data

        return api_data

    def get_image_record_by_id(self, ims_image_id):
        """Look up an IMS image record by its ID.

        Args:
            ims_image_id (str): the UUID of the image

        Returns:
            dict: the IMS image ID corresponding to the given UUID

        Raises:
            InputItemValidateError: if there is an issue looking up the image
                or if the image does not exist.
        """
        try:
            resp = self.ims_client.get('images', ims_image_id, raise_not_ok=False)
            if not resp.ok:
                if resp.status_code == 404:
                    raise InputItemValidateError(f'No image with name or ID {ims_image_id} exists '
                                                 f'for use by {self}')
                else:
                    self.ims_client.raise_from_response(resp)
            else:
                return resp.json()
        except (APIError, ValueError) as err:
            raise InputItemValidateError(f'An error occurred while querying the image record '
                                         f'with ID {ims_image_id}: {err}') from err

    def create(self, payload):
        """Create the session template with a request to the BOS API.

        Args:
            payload (dict): the payload to pass to the BOS API to create the
                BOS session template
        """
        try:
            self.bos_client.create_session_template(payload)
        except APIError as err:
            raise SessionTemplateCreateError(f'Failed to create session template: {err}')


class InputSessionTemplateV1(InputSessionTemplate):
    """A BOS session template that specifies its IMS image as a simple string."""

    @provides_context('image')
    @Validatable.validation_method()
    def validate_image_exists(self, **_):
        """Validate that the image specified for this session template exists.

        See docstring of InputSessionTemplate.validate_image_exists.
        """
        # First check if the image is being created anew by the same input file
        input_image_names = [image.name for image in self.instance.input_images]

        # Assume images from the input file exist when not being excluded and in dry-run mode
        input_images_exist = self.instance.dry_run and IMAGES_KEY in self.instance.limit
        if input_images_exist and self.image in input_image_names:
            image_name = self.image
        else:
            # Accessing the image_record queries IMS to find the image
            image_name = self.image_record['name']

        return {'name': image_name}

    @property
    @jinja_rendered
    def image(self):
        """str: the image specified for the session template
        """
        # the 'image' property is required by the schema
        return self.data['image']

    @property
    def image_is_uuid(self):
        """bool: True if the image value appears to be a UUID, False otherwise"""
        uuid_regex = re.compile('[a-f0-9]{8}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{4}-?[a-f0-9]{12}',
                                re.IGNORECASE)
        return bool(uuid_regex.fullmatch(self.image))

    @cached_property
    def image_record(self):
        """dict: the image record from IMS if one can be found"""
        try:
            name_matches = self.ims_client.get_matching_resources('image', name=self.image)
        except APIError as err:
            raise InputItemValidateError(f'Unable to find image with name or ID {self.image}: {err}')

        if len(name_matches) == 0:
            if self.image_is_uuid:
                return self.get_image_record_by_id(self.image)
            else:
                raise InputItemValidateError(f'No image with name {self.image} exists for '
                                             f'use by session template {self}.')

        elif len(name_matches) > 1:
            raise InputItemValidateError(f'Found multiple matches for image named {self.image} '
                                         f'for use by {self}. This image must be specified by '
                                         f'ID instead.')

        else:
            return name_matches[0]


class InputSessionTemplateV2(InputSessionTemplate):
    """A BOS session template that specifies its IMS image as a dict."""

    @provides_context('image')
    @Validatable.validation_method()
    def validate_image_exists(self, **_):
        """Validate that the image specified for this session template exists.

        See docstring of InputSessionTemplate.validate_image_exists.
        """
        # First check if the image is being created anew by the same input file
        input_image_names = [image.name for image in self.instance.input_images]
        # Assume images from the input file exist when not being excluded and in dry-run mode
        input_images_exist = self.instance.dry_run and IMAGES_KEY in self.instance.limit
        if self.ims_image_name and input_images_exist and self.ims_image_name in input_image_names:
            image_name = self.ims_image_name
        elif self.image_ref:
            if self.image_ref_input_image:
                if input_images_exist:
                    image_name = self.image_ref_input_image.name
                else:
                    # Either not a dry-run or images are being skipped via --limit,
                    # so look it up in IMS.
                    image_name = self.image_record['name']
            else:
                # If the image_ref does not exist in the input instance, this is an error
                raise InputItemValidateError(f'No image exists with ref_name={self.image_ref} '
                                             f'for use by {self}.')
        else:
            # Image is not from input instance. Access image_record to look up in IMS
            image_name = self.image_record['name']

        return {'name': image_name}

    @cached_property
    @jinja_rendered
    def ims_image_name(self):
        """str or None: the name specified for the ims image, or None if not specified"""
        return get_val_by_path(self.data, 'image.ims.name')

    @property
    def ims_image_id(self):
        """str or None: the id specified for the IMS image, or None if not specified"""
        return get_val_by_path(self.data, 'image.ims.id')

    @cached_property
    @jinja_rendered
    def image_ref(self):
        """str or None: the name specified for the image ref, or None if not specified"""
        return get_val_by_path(self.data, 'image.image_ref')

    @cached_property
    def image_ref_input_image(self):
        """BaseInputImage or None: the image referenced by image.image_ref, if it exists"""
        for input_image in self.instance.input_images:
            if self.image_ref == input_image.ref_name:
                return input_image

    @cached_property
    def image_record(self):
        """dict: the image record from IMS if one can be found"""
        if self.ims_image_id:
            return self.get_image_record_by_id(self.ims_image_id)
        else:
            # First, get the name of the image
            image_name = self.ims_image_name
            if not image_name:
                # Image must have been specified by image_ref. `validate_image_exists` already
                # checked that the ref_name exists, but be defensive anyway.
                if self.image_ref_input_image:
                    image_name = self.image_ref_input_image.name
                else:
                    raise InputItemValidateError(f'No image exists with ref_name={self.image_ref} '
                                                 f'for use by {self}.')

            try:
                name_matches = self.ims_client.get_matching_resources('image', name=image_name)
            except APIError as err:
                raise InputItemValidateError(f'Unable to find image with name {image_name} '
                                             f'for use by {self}: {err}')

            if not name_matches:
                raise InputItemValidateError(f'No image with name {image_name} exists for use by {self}.')
            elif len(name_matches) > 1:
                raise InputItemValidateError(f'Found multiple images named {image_name} for use '
                                             f'by {self}. This image must be specified by ID.')
            return name_matches[0]


class InputSessionTemplateCollection(BaseInputItemCollection):
    """The collection BOS session templates defined in the input file"""

    item_class = InputSessionTemplate

    def __init__(self, items_data, instance, jinja_env, request_dumper,
                 bos_client, cfs_client, ims_client, **kwargs):
        """Create a new InputSessionTemplateCollection.

        Args:
            items_data (list of dict): session template data from input file,
                already validated by schema
            instance (sat.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered
            request_dumper (sat.cli.bootprep.output.RequestDumper): the dumper
                for dumping request data to files.
            bos_client (sat.apiclient.BOSClientCommon): the BOS API client
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API client
            ims_client (sat.apiclient.IMSClient): the IMS API client
            **kwargs: additional keyword arguments
        """
        super().__init__(items_data, instance, jinja_env, request_dumper,
                         bos_client=bos_client, cfs_client=cfs_client, ims_client=ims_client, **kwargs)
        self.bos_client = bos_client
        self.cfs_client = cfs_client
        self.ims_client = ims_client

    def get_existing_items_by_name(self):
        """Get existing session templates by name.

        See parent class for full docstring.
        """
        try:
            session_templates = self.bos_client.get_session_templates()
        except APIError as err:
            raise InputItemCreateError(f'Unable to get existing session templates: {err}')

        # BOS session templates have unique names, so this is safe
        return {
            session_template.get('name'): [session_template]
            for session_template in session_templates
        }
