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
Client for querying the fabric manager API
"""
import logging

from sat.apiclient.gateway import APIError, APIGatewayClient
from sat.util import get_val_by_path


LOGGER = logging.getLogger(__name__)


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
