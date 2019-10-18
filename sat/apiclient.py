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


class APIGatewayClient:
    """A client to the API Gateway."""

    # This can be set in subclasses to make a client for a specific API
    base_resource_path = ''

    def __init__(self, session=None, host=None, cert_verify=None):
        """Initialize the APIGatewayClient.

        Args:
            session: The Session instance to use when making REST calls,
                or None to make connections without a session.
            host (str): The API gateway host.
            cert_verify (bool): Whether to verify the gateway's certificate.
        """

        # Inherit parameters from session if not passed as arguments
        # If there is no session, get the values from configuration

        if host is None:
            if session is None:
                host = get_config_value('api_gateway.host')
            else:
                host = session.host

        if cert_verify is None:
            if session is None:
                cert_verify = get_config_value('api_gateway.cert_verify')
            else:
                cert_verify = session.cert_verify

        self.session = session
        self.host = host
        self.cert_verify = cert_verify

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

        if self.session is None:
            requester = requests
        else:
            requester = self.session.session

        try:
            r = requester.get(url, params=params, verify=self.cert_verify)
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
