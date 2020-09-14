"""
Client for querying the API gateway.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
import requests
from urllib.parse import urlunparse

from sat.config import get_config_value
from sat.util import get_val_by_path


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

    def _make_req(self, *args, req_type='GET', req_param=None, json=None):
        """Perform HTTP request with type `req_type` to resource given in `args`.
        Args:
            *args: Variable length list of path components used to construct
                the path to the resource.
            req_type (str): Type of reqest (GET, POST, PUT, or DELETE).
            req_param: Parameter(s) depending on request type.
            json (dict): The data dict to encode as JSON and pass as the body of
                a POST request.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
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
                r = requester.get(url, params=req_param, verify=self.cert_verify)
            elif req_type == 'POST':
                r = requester.post(url, data=req_param, verify=self.cert_verify,
                                   json=json)
            elif req_type == 'PUT':
                r = requester.put(url, data=req_param, verify=self.cert_verify)
            elif req_type == 'DELETE':
                r = requester.delete(url, verify=self.cert_verify)
            else:
                # Internal error not expected to occur.
                raise ValueError("Request type '{}' is invalid.".format(req_type))
        except requests.exceptions.RequestException as err:
            raise APIError("{} request to URL '{}' failed: {}".format(req_type, url, err))

        if not r:
            raise APIError("{} request to URL '{}' failed with status "
                           "code {}: {}".format(req_type, url, r.status_code, r.reason))

        LOGGER.debug("Received response to %s request to URL '%s' "
                     "with status code: '%s': %s", req_type, url, r.status_code, r.reason)

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

    def put(self, *args, payload):
        """Issue an HTTP PUT request to resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to PUT target.
            payload: JSON data to put.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            APIError: if the status code of the response is >= 400 or requests.put
                raises a RequestException of any kind.
        """

        r = self._make_req(*args, req_type='PUT', req_param=payload)

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


class HSMClient(APIGatewayClient):
    base_resource_path = 'smd/hsm/v1/'


class FabricControllerClient(APIGatewayClient):
    base_resource_path = 'fc/v2/'

    def get_port_set_enabled_status(self, port_set):
        """Get the enabled status of the ports in the given port set.

        Args:
            port_set (str): the name of the given port set.

        Returns:
            A dictionary mapping from port xname (str) to enabled status (bool).

        Raises:
            APIError: if the request to the fabric controller API fails, the
                response cannot be parsed as JSON, or the response is missing
                the required 'ports' key.
        """
        enabled_by_xname = {}

        try:
            port_set_state = self.get('port-sets', port_set, 'status').json()
        except APIError as err:
            raise APIError(f'Fabric controller API request for port status of '
                           f'port set {port_set} failed: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON from fabric controller API '
                           f'response when getting status of port set {port_set}: {err}')

        try:
            port_states = port_set_state['ports']
        except KeyError as err:
            raise APIError(f'Failed to get port status for port set {port_set} due to '
                           f'missing key {err} in response from fabric controller API.')

        for port in port_states:
            port_xname = port.get('xname')
            port_enabled = get_val_by_path(port, 'status.enable')
            if port_xname is None or port_enabled is None:
                LOGGER.warning(f'Unable to get xname and/or enabled status of port '
                               f'from port entry: {port}')
            else:
                enabled_by_xname[port_xname] = port_enabled

        return enabled_by_xname

    def get_fabric_edge_ports_enabled_status(self):
        """Gets the enabled status of the ports in the fabric-ports and edge-ports port sets.

        Returns:
            HSN state information as a dictionary mapping from HSN port set name
            to a dictionary mapping from xname strings to booleans indicating
            whether that port is enabled or not. If we fail to get enabled status
            for a port set, it is omitted from the returned dictionary, and a
            warning is logged.
        """
        port_sets = ['edge-ports', 'fabric-ports']
        port_states_by_port_set = {}

        for port_set in port_sets:
            try:
                port_states_by_port_set[port_set] = self.get_port_set_enabled_status(port_set)
            except APIError as err:
                LOGGER.warning(f'Failed to get port status for port set {port_set}: {err}')
                continue

        return port_states_by_port_set


class BOSClient(APIGatewayClient):
    base_resource_path = 'bos/v1/'

    def create_session(self, session_template, operation):
        """Create a BOS session from a session template with an operation.

        Args:
            session_template (str): the name of the session template from which
                to create the session.
            operation (str): the operation to create the session with. Can be
                one of boot, configure, reboot, shutdown.

        Returns:
            The response from the POST to 'session'.

        Raises:
            APIError: if the POST request to create the session fails.
        """
        request_body = {
            'templateUuid': session_template,
            'operation': operation
        }
        return self.post('session', json=request_body)


class CFSClient(APIGatewayClient):
    base_resource_path = 'cfs/'


class CRUSClient(APIGatewayClient):
    base_resource_path = 'crus/'


class NMDClient(APIGatewayClient):
    base_resource_path = 'v2/nmd/'
