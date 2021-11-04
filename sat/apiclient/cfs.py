"""
Client for querying the Configuration Framework Service (CFS) API

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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
import logging

from sat.apiclient.gateway import APIError, APIGatewayClient

LOGGER = logging.getLogger(__name__)


class CFSClient(APIGatewayClient):
    base_resource_path = 'cfs/v2/'

    def get_configurations(self):
        """Get the CFS configurations

        Returns:
            The CFS configurations.

        Raises:
            APIError: if there is an issue getting configurations
        """
        try:
            return self.get('configurations').json()
        except APIError as err:
            raise APIError(f'Failed to get CFS configurations: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from CFS when getting '
                           f'CFS configurations: {err}')

    def put_configuration(self, config_name, request_body):
        """Create a new configuration or update an existing configuration

        Args:
            config_name (str): the name of the configuration to create/update
            request_body (dict): the configuration data, which should have a
                'layers' key.
        """
        self.put('configurations', config_name, json=request_body)
