"""
Defines a class for the input instance loaded from the input file.

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

from sat.cached_property import cached_property
from sat.cli.bootprep.input.configuration import InputConfiguration
from sat.cli.bootprep.input.image import InputImage


class InputInstance:
    """A representation of the instance loaded from the provided input file
    """

    def __init__(self, instance_dict, cfs_client, ims_client):
        """Create a new InputInstance from the validated contents of an input file

        Args:
            instance_dict (dict): the instance from the input file. This assumes
                the instance has already been validated against the schema.
            cfs_client (sat.apiclient.CFSClient): the CFS API client to make
                requests to the CFS API
            ims_client (sat.apiclient.IMSClient): the IMS API client to make
                requests to the IMS API
        """
        self.instance_dict = instance_dict
        self.cfs_client = cfs_client
        self.ims_client = ims_client

    @cached_property
    def input_configurations(self):
        return [InputConfiguration(configuration)
                for configuration in self.instance_dict.get('configurations', [])]

    @cached_property
    def input_images(self):
        return [InputImage(image, self.ims_client, self.cfs_client)
                for image in self.instance_dict.get('images', [])]

    @cached_property
    def input_configuration_names(self):
        return [configuration.name for configuration in self.input_configurations]

    @cached_property
    def input_image_names(self):
        return [image.name for image in self.input_images]
