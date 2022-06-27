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
Client for querying the API gateway.
"""
import logging
import requests
from urllib.parse import urlunparse

from sat.config import get_config_value

LOGGER = logging.getLogger(__name__)


class APIError(Exception):
    """An exception occurred when making a request to the API."""
    pass


class ReadTimeout(Exception):
    """An timeout occurred when making a request to the API."""
    pass


class APIGatewayClient:
    """A client to the API Gateway."""

    # This can be set in subclasses to make a client for a specific API
    base_resource_path = ''

    def __init__(self, session=None, host=None, cert_verify=None, timeout=None):
        """Initialize the APIGatewayClient.

        Args:
            session: The Session instance to use when making REST calls,
                or None to make connections without a session.
            host (str): The API gateway host.
            cert_verify (bool): Whether to verify the gateway's certificate.
            timeout (int): number of seconds to wait for a response before timing
                out requests made to services behind the API gateway.
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
        self.timeout = get_config_value('api_gateway.api_timeout') if timeout is None else timeout

    def set_timeout(self, timeout):
        self.timeout = timeout

    def _make_req(self, *args, req_type='GET', req_param=None, json=None):
        """Perform HTTP request with type `req_type` to resource given in `args`.
        Args:
            *args: Variable length list of path components used to construct
                the path to the resource.
            req_type (str): Type of reqest (GET, STREAM, POST, PUT, or DELETE).
            req_param: Parameter(s) depending on request type.
            json (dict): The data dict to encode as JSON and pass as the body of
                a POST request.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            ReadTimeout: if the req_type is STREAM and there is a ReadTimeout.
            APIError: if the status code of the response is >= 400 or request
                raises a RequestException of any kind.
        """
        url = urlunparse(('https', self.host, 'apis/{}{}'.format(
            self.base_resource_path, '/'.join(args)), '', '', ''))

        LOGGER.debug("Issuing %s request to URL '%s'", req_type, url)

        if self.session is None:
            requester = requests
        else:
            requester = self.session.session

        try:
            if req_type == 'GET':
                r = requester.get(url, params=req_param, verify=self.cert_verify, timeout=self.timeout)
            elif req_type == 'STREAM':
                r = requester.get(url, params=req_param, stream=True,
                                  verify=self.cert_verify, timeout=self.timeout)
            elif req_type == 'POST':
                r = requester.post(url, data=req_param, verify=self.cert_verify,
                                   json=json, timeout=self.timeout)
            elif req_type == 'PUT':
                r = requester.put(url, data=req_param, verify=self.cert_verify,
                                  json=json, timeout=self.timeout)
            elif req_type == 'PATCH':
                r = requester.patch(url, data=req_param, verify=self.cert_verify,
                                    json=json, timeout=self.timeout)
            elif req_type == 'DELETE':
                r = requester.delete(url, verify=self.cert_verify, timeout=self.timeout)
            else:
                # Internal error not expected to occur.
                raise ValueError("Request type '{}' is invalid.".format(req_type))
        except requests.exceptions.ReadTimeout as err:
            if req_type == 'STREAM':
                raise ReadTimeout("{} request to URL '{}' timeout: {}".format(req_type, url, err))
            else:
                raise APIError("{} request to URL '{}' failed: {}".format(req_type, url, err))
        except requests.exceptions.RequestException as err:
            raise APIError("{} request to URL '{}' failed: {}".format(req_type, url, err))

        LOGGER.debug("Received response to %s request to URL '%s' "
                     "with status code: '%s': %s", req_type, r.url, r.status_code, r.reason)

        if not r.ok:
            api_err_msg = (f"{req_type} request to URL '{url}' failed with status "
                           f"code {r.status_code}: {r.reason}")
            # Attempt to get more information from response
            try:
                problem = r.json()
            except ValueError:
                raise APIError(api_err_msg)

            if 'title' in problem:
                api_err_msg += f'. {problem["title"]}'
            if 'detail' in problem:
                api_err_msg += f' Detail: {problem["detail"]}'

            raise APIError(api_err_msg)

        return r

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

        r = self._make_req(*args, req_type='GET', req_param=params)

        return r

    def stream(self, *args, params=None):
        """Issue an HTTP GET stream request to resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to the resource to GET.
            params (dict): Parameters dictionary to pass through to request.get.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            ReadTimeout: if there is a ReadTimeout.
            APIError: if the status code of the response is >= 400 or requests.get
                raises a RequestException of any kind.
        """

        r = self._make_req(*args, req_type='STREAM', req_param=params)

        return r

    def post(self, *args, payload=None, json=None):
        """Issue an HTTP POST request to resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to POST target.
            payload: The encoded data to send as the POST body.
            json: The data dict to encode as JSON and send as the POST body.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            APIError: if the status code of the response is >= 400 or requests.post
                raises a RequestException of any kind.
        """

        r = self._make_req(*args, req_type='POST', req_param=payload, json=json)

        return r

    def put(self, *args, payload=None, json=None):
        """Issue an HTTP PUT request to resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to PUT target.
            payload: The encoded data to send as the PUT body.
            json: The data dict to encode as JSON and send as the PUT body.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            APIError: if the status code of the response is >= 400 or requests.put
                raises a RequestException of any kind.
        """

        r = self._make_req(*args, req_type='PUT', req_param=payload, json=json)

        return r

    def patch(self, *args, payload=None, json=None):
        """Issue an HTTP PATCH request to resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to PATCH target.
            payload: The encoded data to send as the PATCH body.
            json: The data dict to encode as JSON and send as the PATCH body.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            APIError: if the status code of the response is >= 400 or requests.put
                raises a RequestException of any kind.
        """

        r = self._make_req(*args, req_type='PATCH', req_param=payload, json=json)

        return r

    def delete(self, *args):
        """Issue an HTTP DELETE resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to DELETE target.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            APIError: if the status code of the response is >= 400 or requests.delete
                raises a RequestException of any kind.
        """

        r = self._make_req(*args, req_type='DELETE')

        return r
