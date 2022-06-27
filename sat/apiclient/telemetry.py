#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Client for querying the Cray Shasta Telemetry API
"""
import logging

from sat.apiclient.gateway import APIError, APIGatewayClient, ReadTimeout

LOGGER = logging.getLogger(__name__)


class TelemetryAPIClient(APIGatewayClient):
    base_resource_path = 'sma-telemetry-api/v1/'

    def ping(self):
        """Check if endpoint is alive.

        Returns:
            True or False
        """

        try:
            self.get('ping')
        except APIError as err:
            LOGGER.error(f'Failed to ping telemetry API endpoint: {err}')
            return False

        return True

    def stream(self, topic, timeout, params=None):
        """Create a GET stream connection to the telemetry API.

        Args:
            topic (str): The name of the Kafka telemetry topic.
            timeout (int): The timeout in seconds to wait for a response.
            params (dict): Parameters dictionary to pass through to requests.get.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            ReadTimeout: if requests.get raises a ReadTimeout.
            APIError: if the status code of the response is >= 400 or requests.get
                raises a RequestException other than ReadTimeout.
        """

        self.set_timeout(timeout)
        err_prefix = 'Failed to stream telemetry data'
        try:
            response = super().stream('stream', topic, params=params)
        except ReadTimeout as err:
            raise ReadTimeout(f'{err_prefix}: {err}')
        except APIError as err:
            raise APIError(f'{err_prefix}: {err}')

        return response
