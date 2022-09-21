#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
Client for querying the Job State Checker service
"""

import logging

from sat.apiclient.gateway import APIError, APIGatewayClient

LOGGER = logging.getLogger(__name__)


class JobstatClient(APIGatewayClient):
    base_resource_path = 'statechecker/jobstat/'

    def get_all(self):
        """Get all results from Job State Checker.

        Returns:
            A list of dictionaries where each dictionary pertains to a
            single job.

        Raises:
            APIError: if there is a failure querying the Job State Checker API
                or getting the required information from the response.
        """
        err_prefix = 'Failed to get State Checker data'
        try:
            response = self.get('all').json()
            if 'errorcode' in response and response['errorcode'] != 0:
                raise APIError(response.get('errormessage', 'unknown error'))
            return response['jobstat']
        except APIError as err:
            raise APIError(f'{err_prefix}: {err}')
        except ValueError as err:
            raise APIError(f'{err_prefix} due to bad JSON in response: {err}')
        except KeyError as err:
            raise APIError(f'{err_prefix} due to missing {err} key in response.')
