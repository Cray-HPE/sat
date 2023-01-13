#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
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
Client for querying the System Layout Service (SLS) API
"""
import logging

from csm_api_client.service.gateway import APIError, APIGatewayClient

LOGGER = logging.getLogger(__name__)


class SLSClient(APIGatewayClient):
    base_resource_path = 'sls/v1/'

    def get_hardware(self):
        """Get the SLS Hardware from the dumpstate.

        Returns:
            A list of dictionaries of hardware components from dumpstate.

        Raises:
            APIError: if there is a failure querying the SLS API or getting
                the required information from the response.
        """

        err_prefix = 'Failed to get SLS hardware from dumpstate'
        try:
            hardware = self.get('dumpstate').json()['Hardware']
        except APIError as err:
            raise APIError(f'{err_prefix}: {err}')
        except ValueError as err:
            raise APIError(f'{err_prefix} due to bad JSON in response: {err}')
        except KeyError as err:
            raise APIError(f'{err_prefix} due to missing {err} key in response.')

        return hardware
