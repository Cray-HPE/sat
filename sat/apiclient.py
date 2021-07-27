"""
Client for querying the API gateway.

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
from collections import defaultdict
import logging
import requests
from urllib.parse import urlunparse

from sat.config import get_config_value
from sat.constants import BMC_TYPES
from sat.util import get_val_by_path


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
                r = requester.put(url, data=req_param, verify=self.cert_verify, timeout=self.timeout)
            elif req_type == 'PATCH':
                r = requester.patch(url, data=req_param, verify=self.cert_verify, timeout=self.timeout)
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

        if not r:
            raise APIError("{} request to URL '{}' failed with status "
                           "code {}: {}".format(req_type, url, r.status_code, r.reason))

        LOGGER.debug("Received response to %s request to URL '%s' "
                     "with status code: '%s': %s", req_type, r.url, r.status_code, r.reason)

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

    def patch(self, *args, payload):
        """Issue an HTTP PATCH request to resource given in `args`.

        Args:
            *args: Variable length list of path components used to construct
                the path to PATCH target.
            payload: JSON data to put.

        Returns:
            The requests.models.Response object if the request was successful.

        Raises:
            APIError: if the status code of the response is >= 400 or requests.put
                raises a RequestException of any kind.
        """

        r = self._make_req(*args, req_type='PATCH', req_param=payload)

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

    def get_bmcs_by_type(self, bmc_type=None, check_keys=True):
        """Get a list of BMCs, optionally of a single type.

        Args:
            bmc_type (string): Any HSM BMC type: NodeBMC, RouterBMC or ChassisBMC.
            check_keys (bool): Whether or not to filter data based on missing keys.

        Returns:
            A list of dictionaries where each dictionary describes a BMC.

        Raises:
            APIError: if the API query failed or returned an invalid response.
        """
        try:
            response = self.get(
                'Inventory', 'RedfishEndpoints', params={'type': bmc_type} if bmc_type else {}
            )
        except APIError as err:
            raise APIError(f'Failed to get BMCs from HSM API: {err}')

        try:
            redfish_endpoints = response.json()['RedfishEndpoints']
        except ValueError as err:
            raise APIError(f'API response could not be parsed as JSON: {err}')
        except KeyError as err:
            raise APIError(f'API response missing expected key: {err}')

        # Check that the returned data has expected keys, and exclude data without it.
        invalid_redfish_endpoint_xnames = []
        if check_keys:
            invalid_redfish_endpoint_xnames = [
                endpoint.get('ID') for endpoint in redfish_endpoints
                if any(required_key not in endpoint for required_key in ['ID', 'Enabled', 'DiscoveryInfo'])
                or 'LastDiscoveryStatus' not in endpoint['DiscoveryInfo']
            ]
        if invalid_redfish_endpoint_xnames:
            LOGGER.warning(
                'The following xnames were excluded due to incomplete information from HSM: %s',
                ', '.join(invalid_redfish_endpoint_xnames)
            )

        return [
            endpoint for endpoint in redfish_endpoints
            if endpoint.get('ID') not in invalid_redfish_endpoint_xnames
        ]

    def get_and_filter_bmcs(self, bmc_types=BMC_TYPES, include_disabled=False, include_failed_discovery=False,
                            xnames=None):
        """Get all BMCs of a given type, optionally filtering against a list of xnames.

        Args:
            bmc_types (tuple): Any combination of ('NodeBMC', 'RouterBMC', 'ChassisBMC')
            include_disabled (bool): if True, include disabled nodes.
            include_failed_discovery (bool): if True, include nodes which had discovery errors.
            xnames (list): A list of xnames to filter against the data from HSM.

        Returns:
            A set of xnames.

        Raises:
            APIError: if an API query failed or returned an invalid response.
        """
        if set(bmc_types) == set(BMC_TYPES):
            bmcs = self.get_bmcs_by_type()
        else:
            bmcs = []
            for bmc_type in bmc_types:
                bmcs.extend(self.get_bmcs_by_type(bmc_type))

        # Filter given xnames by type
        hsm_xnames = set(bmc['ID'] for bmc in bmcs)
        if xnames:
            type_excluded_xnames = set(xnames) - hsm_xnames
            xnames = set(xnames).intersection(hsm_xnames)
            if type_excluded_xnames:
                LOGGER.warning(
                    'The following xnames will be excluded as they are not type(s) %s: %s',
                    ', '.join(bmc_types), ', '.join(type_excluded_xnames)
                )
        else:
            xnames = hsm_xnames

        # Filter out disabled components
        if not include_disabled:
            disabled_xnames = set(bmc['ID'] for bmc in bmcs if not bmc['Enabled'])
            disabled_xnames_to_report = set(xnames).intersection(disabled_xnames)
            if disabled_xnames_to_report:
                LOGGER.warning(
                    'Excluding the following xnames which are disabled: %s',
                    ', '.join(disabled_xnames_to_report)
                )
            xnames = xnames - disabled_xnames

        # Filter out components for which discovery failed
        if not include_failed_discovery:
            failed_discovery_xnames = set(
                bmc['ID'] for bmc in bmcs if bmc['DiscoveryInfo']['LastDiscoveryStatus'] != 'DiscoverOK'
            )
            failed_discovery_xnames_to_report = set(xnames).intersection(failed_discovery_xnames)
            if failed_discovery_xnames_to_report:
                LOGGER.warning(
                    'Excluding the following xnames which have a LastDiscoveryStatus other than "DiscoverOK": %s',
                    ', '.join(failed_discovery_xnames_to_report)
                )
            xnames = xnames - failed_discovery_xnames

        return xnames

    def get_component_xnames(self, params=None, omit_empty=True):
        """Get the xnames of components matching the given criteria.

        If any args are omitted, the results are not limited by that criteria.

        Args:
            params (dict): the parameters to pass in the GET request to the
                '/State/Components' URL in HSM. E.g.:
                    {
                        'type': 'Node',
                        'role': 'Compute',
                        'class': 'Mountain'
                    }
            omit_empty (bool): if True, omit the components with "State": "Empty"

        Returns:
            list of str: the xnames matching the given filters

        Raises:
            APIError: if there is a failure querying the HSM API or getting
                the required information from the response.
        """
        if params:
            params_string = f' with {", ".join(f"{key}={value}" for key, value in params.items())}'
        else:
            params_string = ''

        err_prefix = f'Failed to get components{params_string}.'

        try:
            components = self.get('State', 'Components', params=params).json()['Components']
        except APIError as err:
            raise APIError(f'{err_prefix}: {err}')
        except ValueError as err:
            raise APIError(f'{err_prefix} due to bad JSON in response: {err}')
        except KeyError as err:
            raise APIError(f'{err_prefix} due to missing {err} key in response.')

        try:
            if omit_empty:
                return [component['ID'] for component in components
                        if component['State'] != 'Empty']
            else:
                return [component['ID'] for component in components]
        except KeyError as err:
            raise APIError(f'{err_prefix} due to missing {err} key in list of components.')

    def get_node_components(self):
        """Get the components of Type=Node from HSM.

        Returns:
            list of dictionaries of Node components.

        Raises:
            APIError: if there is a failure querying the HSM API or getting
                the required information from the response.
        """

        err_prefix = 'Failed to get Node components'
        try:
            components = self.get('State', 'Components', params={'type': 'Node'}).json()['Components']
        except APIError as err:
            raise APIError(f'{err_prefix}: {err}')
        except ValueError as err:
            raise APIError(f'{err_prefix} due to bad JSON in response: {err}')
        except KeyError as err:
            raise APIError(f'{err_prefix} due to missing {err} key in response.')

        return components

    def get_all_components(self):
        """Get all components from HSM.

        Returns:
            components ([dict]): A list of dictionaries from HSM.

        Raises:
            APIError: if there is a failure querying the HSM API or getting
                the required information from the response.
        """

        err_prefix = 'Failed to get HSM components'
        try:
            components = self.get('State', 'Components').json()['Components']
        except APIError as err:
            raise APIError(f'{err_prefix}: {err}')
        except ValueError as err:
            raise APIError(f'{err_prefix} due to bad JSON in response: {err}')
        except KeyError as err:
            raise APIError(f'{err_prefix} due to missing {err} key in response.')

        return components


class FabricControllerClient(APIGatewayClient):
    base_resource_path = 'fabric-manager/'
    default_port_set_names = ['fabric-ports', 'edge-ports']

    def get_fabric_edge_ports(self):
        """Get all the fabric and edge ports in the system.

        Returns:
            A dict mapping from the default fabric and edge port set names to a
            list of ports in that port set.
        """
        ports_by_port_set = {}
        for port_set in self.default_port_set_names:
            try:
                ports_by_port_set[port_set] = self.get('port-sets', port_set).json()['ports']
            except APIError as err:
                LOGGER.warning(f'Failed to get ports for port set {port_set}: {err}')
            except ValueError as err:
                LOGGER.warning(f'Failed to parse response from fabric controller API '
                               f'when getting ports for port set {port_set}: {err}')
            except KeyError as err:
                LOGGER.warning(f'Response from fabric controller API was missing the '
                               f'{err} key.')

        return ports_by_port_set

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
            whether that port is enabled or not.

            If we fail to get enabled status for a port set, it is omitted from the
            returned dictionary, and a warning is logged.
        """
        port_states_by_port_set = {}

        for port_set in self.default_port_set_names:
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


class SCSDClient(APIGatewayClient):
    base_resource_path = 'scsd/v1/'


class CAPMCError(APIError):
    """An error occurred in CAPMC."""
    def __init__(self, message, xname_errs=None):
        """Create a new CAPMCError with the given message and info about the failing xnames.

        Args:
            message (str): the error message
            xname_errs (list): a list of dictionaries representing the failures for
                the individual components that failed. Each dict should have the
                following keys:
                    e: the error code
                    err_msg: the error message
                    xname: the actual xname which failed
        """
        self.message = message
        self.xname_errs = xname_errs if xname_errs is not None else []
        self.xnames = [xname_err['xname'] for xname_err in self.xname_errs
                       if 'xname' in xname_err]

    def __str__(self):
        if not self.xname_errs:
            return self.message
        else:
            # A mapping from a tuple of (err_code, err_msg) to a list of xnames
            # with that combination of err_code and err_msg.
            xnames_by_err = defaultdict(list)
            for xname_err in self.xname_errs:
                xnames_by_err[(xname_err.get('e'), xname_err.get('err_msg'))].append(xname_err.get('xname'))

            xname_err_summary = '\n'.join([f'xname(s) ({", ".join(xnames)}) failed with '
                                           f'e={err_info[0]} and err_msg="{err_info[1]}"'
                                           for err_info, xnames in xnames_by_err.items()])

            return f'{self.message}\n{xname_err_summary}'


class CAPMCClient(APIGatewayClient):
    base_resource_path = 'capmc/capmc/v1/'

    def __init__(self, *args, suppress_warnings=False, **kwargs):
        """Initialize the CAPMCClient.

        Args:
            *args: args passed through to APIGatewayClient.__init__
            suppress_warnings (bool): if True, suppress warnings when a query to
                get_xname_status results in an error and node(s) in undefined
                state. As an example, this is useful when waiting for a BMC or
                node controller to be powered on since CAPMC will fail to query
                the power status until it is powered on.
            **kwargs: keyword args passed through to APIGatewayClient.__init__
        """
        self.suppress_warnings = suppress_warnings
        super().__init__(*args, **kwargs)

    def set_xnames_power_state(self, xnames, power_state, force=False, recursive=False, prereq=False):
        """Set the power state of the given xnames.

        Args:
            xnames (list): the xnames (str) to perform the power operation
                against.
            power_state (str): the desired power state. Either "on" or "off".
            force (bool): if True, disable checks and force the power operation.
            recursive (bool): if True, power on component and its descendants.
            prereq (bool): if True, power on component and its ancestors.

        Returns:
            None

        Raises:
            ValueError: if the given `power_state` is not one of 'on' or 'off'
            CAPMCError: if the attempt to power on/off the given xnames with CAPMC
                fails. This exception contains more specific information about
                the failure, which will be included in its __str__.
        """
        if power_state == 'on':
            path = 'xname_on'
        elif power_state == 'off':
            path = 'xname_off'
        else:
            raise ValueError(f'Invalid power state {power_state} given. Must be "on" or "off".')

        params = {'xnames': xnames, 'force': force, 'recursive': recursive, 'prereq': prereq}

        try:
            response = self.post(path, json=params).json()
        except APIError as err:
            raise CAPMCError(f'Failed to power {power_state} xname(s): {", ".join(xnames)}') from err
        except ValueError as err:
            raise CAPMCError(f'Failed to parse JSON in response from CAPMC API when powering '
                             f'{power_state} xname(s): {", ".join(xnames)}') from err

        if response.get('e'):
            raise CAPMCError(f'Power {power_state} operation failed for xname(s).',
                             xname_errs=response.get('xnames'))

    def get_xnames_power_state(self, xnames):
        """Get the power state of the given xnames from CAPMC.

        Args:
            xnames (list): the xnames (str) to get power state for.

        Returns:
            dict: a dictionary whose keys are the power states and whose values
                are lists of xnames in those power states.

        Raises:
            CAPMCError: if the request to get power state fails.
        """
        try:
            response = self.post('get_xname_status', json={'xnames': xnames}).json()
        except APIError as err:
            raise CAPMCError(f'Failed to get power state of xname(s): {", ".join(xnames)}') from err
        except ValueError as err:
            raise CAPMCError(f'Failed to parse JSON in response from CAPMC API '
                             f'when getting power state of xname(s): {", ".join(xnames)}') from err

        if response.get('e'):
            level = logging.DEBUG if self.suppress_warnings else logging.WARNING
            LOGGER.log(level,
                       'Failed to get power state of one or more xnames, e=%s, '
                       'err_msg="%s". xnames with undefined power state: %s',
                       response['e'], response.get("err_msg"), ", ".join(response.get('undefined', [])))

        # Take out the err code and err_msg if everything went well
        return {k: v for k, v in response.items() if k not in {'e', 'err_msg'}}

    def get_xname_power_state(self, xname):
        """Get the power state of a single xname from CAPMC.

        Args:
            xname (str): the xname to get power state of

        Returns:
            str: the power state of the node

        Raises:
            CAPMCError: if the request to CAPMC fails or the expected information
                is not returned by the CAPMC API.
        """
        xnames_by_power_state = self.get_xnames_power_state([xname])
        matching_states = [state for state, xnames in xnames_by_power_state.items()
                           if xname in xnames]
        if not matching_states:
            raise CAPMCError(f'Unable to determine power state of {xname}. Not '
                             f'present in response from CAPMC: {xnames_by_power_state}')
        elif len(matching_states) > 1:
            raise CAPMCError(f'Unable to determine power state of {xname}. CAPMC '
                             f'reported multiple power states: {", ".join(matching_states)}')
        else:
            return matching_states[0]


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
