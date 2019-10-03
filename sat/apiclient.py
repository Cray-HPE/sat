"""
Client for querying the API gateway on a Shasta system.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging

import requests

from sat.config import get_config_value

LOGGER = logging.getLogger(__name__)


class APIError(Exception):
    """An exception occurred when making a request to the API."""
    pass


class APIGatewayClient(object):
    """A client to the API Gateway.

    TODO: This class should handle authentication. See SAT-126.
    """
    # This can be set in subclasses to make a client for a specific API
    base_resource_path = ''

    def __init__(self, host=None):
        """Initialize the APIGatewayClient.

        Args:
            host (str): The API gateway host.
        """
        if host is None:
            host = get_config_value('api_gateway_host')

        self.host = host

    def get(self, *args, params=None):
        """Issue an HTTP GET request to resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to the resource to GET.
            params (dict): Parameters dictionary to pass through to request.get.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            APIError: if the status code of the response is >= 400 or requests.get
                raises a RequestException of any kind.
        """
        url = 'https://{}/apis/{}'.format(self.host, self.base_resource_path) + '/'.join(args)
        LOGGER.debug("Issuing GET request to URL '%s'", url)

        try:
            r = requests.get(url, params=params)
        except requests.exceptions.RequestException as err:
            raise APIError("GET request to URL '{}' failed: {}".format(url, err))

        if not r:
            raise APIError("GET request to URL '{}' failed "
                           "with status code {}".format(url, r.status_code))

        LOGGER.debug("Received response to GET request to URL '%s' with status code: '%s'",
                     url, r.status_code)

        return r


class HSMClient(APIGatewayClient):
    base_resource_path = 'smd/hsm/v1/'
