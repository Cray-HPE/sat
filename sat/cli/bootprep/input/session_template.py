"""
Defines class for session templates defined in the input file.

(C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP.

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
import re

from sat.apiclient import APIError
from sat.cached_property import cached_property
from sat.cli.bootprep.input.base import BaseInputItem, BaseInputItemCollection, Validatable
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
        cfs_client (sat.apiclient.CFSClient): the CFS API client to make
            requests to the CFS API
    """
    description = 'BOS session template'

    def __init__(self, data, instance, bos_client, cfs_client, ims_client, **kwargs):
        """Create a new InputSessionTemplate.

        Args:
            data (dict): the data defining the item from the input file, already
                validated by the bootprep schema.
            instance (sat.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
            bos_client (sat.apiclient.BOSClientCommon): the BOS API client
            cfs_client (sat.apiclient.CFSClient): the CFS API client
            ims_client (sat.apiclient.IMSClient): the IMS API client
            **kwargs: additional keyword arguments
        """
        super().__init__(data, instance, **kwargs)
        self.bos_client = bos_client
        self.cfs_client = cfs_client
        self.ims_client = ims_client

    @property
    def configuration(self):
        """str: the configuration specified for the session template"""
        # the 'configuration' property is required by the schema
        return self.data['configuration']

    @property
    def boot_sets(self):
        """dict: the boot sets specified for the session template"""
        # the 'bos_parameters' property is required, and 'boot_sets' is required within that
        return self.data['bos_parameters']['boot_sets']

    @property
    def image(self):
        """str: the image specified for the session template

        Per the bootprep schema, this may be an image name or id.
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
                try:
                    return self.ims_client.get_image(self.image)
                except APIError as err:
                    # TODO: should probably differentiate between 404 Not Found and other errors
                    raise InputItemValidateError(f'No image with name or ID {self.image} exists '
                                                 f'for use by session template {self.name}: {err}')
            else:
                raise InputItemValidateError(f'No image with name {self.image} exists for '
                                             f'use by session template {self.name}.')

        elif len(name_matches) > 1:
            raise InputItemValidateError(f'Found multiple matches for image named {self.image} '
                                         f'for use by session template {self.name}. This image '
                                         f'must be specified by ID instead.')

        else:
            return name_matches[0]

    @Validatable.validation_method
    def validate_configuration_exists(self, **_):
        """Validate that the configuration specified for this session template exists.

        Raises:
            InputItemValidateError: if the configuration does not exist
        """
        # First check if the configuration is being created anew by the same input file
        input_config_names = [config.name for config in self.instance.input_configurations]
        if self.configuration in input_config_names:
            return

        try:
            self.cfs_client.get_configuration(self.configuration)
        except APIError as err:
            # TODO: should probably differentiate between 404 Not Found and other errors
            raise InputItemValidateError(f'Configuration {self.configuration} specified for '
                                         f'session template {self.name} does not exist: {err}')

    @Validatable.validation_method
    def validate_image_exists(self, **_):
        """Validate that the image specified for this session template exists.

        Raises:
            InputItemValidateError: if the image cannot be verified to exist
        """
        # First check if the image is being created anew by the same input file
        input_image_names = [image.name for image in self.instance.input_images]
        if self.image in input_image_names:
            return

        # Accessing the image_record queries IMS to find the image
        _ = self.image_record

    def get_bos_api_data(self):
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
            boot_set_api_data = self.bos_client.get_base_boot_set_data()
            image_record = self.image_record
            boot_set_api_data.update({
                'etag': get_val_by_path(image_record, 'link.etag'),
                'path': get_val_by_path(image_record, 'link.path'),
                'type': get_val_by_path(image_record, 'link.type')
            })
            boot_set_api_data.update(boot_set_data)
            api_data['boot_sets'][boot_set_name] = boot_set_api_data

        return api_data

    def create(self, dumper=None):
        """Create the session template with a request to the BOS API."""
        request_body = self.get_bos_api_data()
        if dumper is not None:
            dumper.write_request_body(self.name, request_body)

        try:
            self.bos_client.create_session_template(request_body)
        except APIError as err:
            raise SessionTemplateCreateError(f'Failed to create session template: {err}')


class InputSessionTemplateCollection(BaseInputItemCollection):
    """The collection BOS session templates defined in the input file"""

    item_class = InputSessionTemplate

    def __init__(self, items_data, instance, bos_client, cfs_client, ims_client, **kwargs):
        """Create a new InputSessionTemplateCollection.

        Args:
            items_data (list of dict): session template data from input file,
                already validated by schema
            instance (sat.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
            bos_client (sat.apiclient.BOSClientCommon): the BOS API client
            cfs_client (sat.apiclient.CFSClient): the CFS API client
            ims_client (sat.apiclient.IMSClient): the IMS API client
            **kwargs: additional keyword arguments
        """
        super().__init__(items_data, instance, bos_client=bos_client,
                         cfs_client=cfs_client, ims_client=ims_client, **kwargs)
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
