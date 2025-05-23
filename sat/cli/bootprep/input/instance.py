#
# MIT License
#
# (C) Copyright 2021-2025 Hewlett Packard Enterprise Development LP
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
Defines a class for the input instance loaded from the input file.
"""
from sat.cached_property import cached_property
from sat.cli.bootprep.constants import CONFIGURATIONS_KEY, IMAGES_KEY, SESSION_TEMPLATES_KEY
from sat.cli.bootprep.input.configuration import InputConfigurationCollection
from sat.cli.bootprep.input.image import BaseInputImage
from sat.cli.bootprep.input.session_template import InputSessionTemplateCollection


class InputInstance:
    """A representation of the instance loaded from the provided input file.
    """

    def __init__(self, instance_dict, request_dumper,
                 cfs_client, ims_client, bos_client,
                 jinja_env, product_catalog, dry_run, limit, debug_on_failure=False):
        """Create a new InputInstance from the validated contents of an input file.

        Args:
            instance_dict (dict): the instance from the input file. This assumes
                the instance has already been validated against the schema.
            request_dumper (sat.cli.bootprep.output.RequestDumper): the dumper
                for dumping request data to files.
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API client to make
                requests to the CFS API
            ims_client (sat.apiclient.IMSClient): the IMS API client to make
                requests to the IMS API
            bos_client (sat.apiclient.BOSClientCommon): the BOS API client to make
                requests to the BOS API
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            product_catalog (cray_product_catalog.query.ProductCatalog):
                the product catalog object
            dry_run (bool): True if this is a dry run, False otherwise.
            limit (list of str): the list of types of items from the input file
                to be created.
        """
        self.instance_dict = instance_dict
        self.request_dumper = request_dumper
        self.cfs_client = cfs_client
        self.ims_client = ims_client
        self.bos_client = bos_client
        self.jinja_env = jinja_env
        self.product_catalog = product_catalog
        self.dry_run = dry_run
        self.limit = limit
        self.debug_on_failure = debug_on_failure

    @cached_property
    def input_configurations(self):
        """InputConfigurationCollection: the configurations in the input instance"""
        return InputConfigurationCollection(
            self.instance_dict.get(CONFIGURATIONS_KEY, []),
            self,
            jinja_env=self.jinja_env,
            request_dumper=self.request_dumper,
            cfs_client=self.cfs_client,
            product_catalog=self.product_catalog
        )

    @cached_property
    def input_images(self):
        """list of InputImages: the images in the input instance"""
        return [BaseInputImage.get_image(image, index, self, self.jinja_env, self.product_catalog,
                                         self.ims_client, self.cfs_client, debug_on_failure=self.debug_on_failure)
                for index, image in enumerate(self.instance_dict.get(IMAGES_KEY, []))]

    @cached_property
    def input_session_templates(self):
        """InputSessionTemplateCollection: the session templates in the input instance"""
        return InputSessionTemplateCollection(
            self.instance_dict.get(SESSION_TEMPLATES_KEY, []),
            self,
            jinja_env=self.jinja_env,
            request_dumper=self.request_dumper,
            bos_client=self.bos_client,
            cfs_client=self.cfs_client,
            ims_client=self.ims_client
        )

    @cached_property
    def input_configuration_names(self):
        """list of str: the names of configurations in the input instance"""
        return [configuration.name for configuration in self.input_configurations.items]

    @cached_property
    def input_image_names(self):
        """list of str: the names of images in the input instance"""
        return [image.name for image in self.input_images]
