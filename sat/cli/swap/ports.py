"""
Contains functions for modifying port configuration via fabric API.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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

import json
import logging
import re

import inflect

from sat.apiclient import APIError, FabricControllerClient
from sat.session import SATSession
from sat.xname import XName

LOGGER = logging.getLogger(__name__)

INF = inflect.engine()

JACK_XNAME_REGEX = re.compile(r'^x\d+c\d+r\d+j\d+$')


class PortManager:
    """Manages port operations that use the Fabric Controller API"""

    def __init__(self):
        self.fabric_client = FabricControllerClient(SATSession())

    @staticmethod
    def _get_endpoints_for_jack(jack, port_info):
        """Get a list of ports for a single jack

        Args:
            jack (str): jack xname
            port_info (dict): the data of a port-links query under the 'ports' key

        Returns:
            A 2-tuple of lists of edge port and fabric port xnames
        """

        jack_xname = XName(jack)

        # Get all ports matching the supplied jack
        edge_endpoints = [
            port for port in port_info['edge'] if jack_xname.contains_component(XName(port))
        ]

        fabric_endpoints = [
            port for port in port_info['fabric'] if jack_xname.contains_component(XName(port))
        ]

        return edge_endpoints, fabric_endpoints

    @staticmethod
    def _get_linked_endpoints(ports, link_info):
        """Get linked ports from a list of ports

        Args:
            ports (list): port xnames
            link_info (dict): the data of a port-links query under the 'links' key

        Returns:
            A list of port xnames which may contain duplicates
        """

        linked_endpoints = []

        for port in ports:
            for endpoint_pair in link_info:
                endpoint1 = endpoint_pair['endpoint1']
                endpoint2 = endpoint_pair['endpoint2']
                if port in [endpoint1, endpoint2]:
                    linked_endpoints.extend([endpoint1, endpoint2])
                    break

        return linked_endpoints

    @staticmethod
    def _get_linked_jacks(ports, link_info):
        """Get linked jacks from a list of ports

        Args:
            ports (list): port xnames
            link_info (dict): the data of a port-links query under the 'links' key

        Returns:
            A set of jack xnames
        """

        return set(
            XName(p).get_direct_parent().xname_str for p in PortManager._get_linked_endpoints(ports, link_info)
        )

    @staticmethod
    def _get_jack_endpoints(jack_xnames, portinfo, force):
        """Get all linked endpoints for the given jack xnames, optionally skipping checks

        Args:
            jack_xnames (list): list of jack xnames
            portinfo(dict): the response data from a fabric port-links query

        Returns:
            A list of sets, where each set is the set of ports connected to the
                corresponding jack in jack_xnames.

        """
        jack_endpoints = []
        for jack in jack_xnames:
            linked_endpoints = []

            # Get all ports local to the jack
            edge_endpoints, fabric_endpoints = PortManager._get_endpoints_for_jack(jack, portinfo['ports'])

            # Get all jacks that are linked to the jack
            linked_jacks = PortManager._get_linked_jacks(fabric_endpoints, portinfo['links'])
            # For each port of each linked jack, get all linked endpoints
            for linked_jack in linked_jacks:
                linked_jack_endpoints = PortManager._get_endpoints_for_jack(linked_jack, portinfo['ports'])[1]
                linked_endpoints.extend(PortManager._get_linked_endpoints(linked_jack_endpoints, portinfo['links']))

            # For fabric endpoints, check that we were able to get links
            if fabric_endpoints and not linked_endpoints:
                no_port_links = f'Unable to get port links for {jack}'
                if force:
                    LOGGER.warning(no_port_links)
                else:
                    LOGGER.error(no_port_links)
                    return None

            # Remove duplicates because linked endpoints may overlap with fabric endpoints
            jack_endpoints.append(set(edge_endpoints + fabric_endpoints + linked_endpoints))

        return jack_endpoints

    def get_jack_ports(self, jack_xnames, force=False):
        """Get a list of ports for one or more jacks

        Args:
            jack_xnames (list): a list of jack xnames
            force (bool): Ignore if supplied jacks are not connected by a cable
                or if unable to get linked ports.  If False, return None for these
                cases.

        Returns:
            List of port xnames or None
        """

        try:
            response = self.fabric_client.get('port-links')
            portinfo = response.json()
        except APIError as err:
            LOGGER.error(f'Failed to get port links from fabric controller: {err}')
            return None
        except ValueError as err:
            LOGGER.error(f'Failed to parse JSON from fabric controller response: {err}')
            return None

        # Check that ports and links sub-dictionaries exist
        missing_keys = [k for k in ['ports', 'links'] if k not in portinfo]
        if missing_keys:
            LOGGER.error(
                f'{INF.plural("Key", len(missing_keys))} missing from fabric controller port links: {missing_keys}'
            )
            return None

        # Under ports, check that both 'fabric' and 'edge' ports are listed
        missing_ports_keys = [k for k in ['fabric', 'edge'] if k not in portinfo['ports']]
        if missing_ports_keys:
            LOGGER.error(f'{INF.plural("Key", len(missing_keys))} missing from '
                         f'fabric controller port links port data: {missing_keys}')
            return None

        # If a non-jack was given, return an empty list
        non_matching_xnames = [xname for xname in jack_xnames if not re.match(JACK_XNAME_REGEX, xname)]
        if non_matching_xnames:
            num_non_matching = len(non_matching_xnames)
            LOGGER.error(f'{INF.plural("xname", num_non_matching)} {",".join(non_matching_xnames)} '
                         f'{INF.plural_verb("does", num_non_matching)} not match the format of a jack xname.')
            return []

        # Build a list of lists of all ports for the given jack(s)
        jack_endpoints = PortManager._get_jack_endpoints(jack_xnames, portinfo, force)
        if jack_endpoints is None:
            return None

        # For each jack, check that the endpoints match
        if not all(endpoint_list == jack_endpoints[0] for endpoint_list in jack_endpoints):
            not_connected = f'Jacks {",".join(jack_xnames)} are not connected by a single cable'
            if force:
                LOGGER.warning(not_connected)
            else:
                LOGGER.error(not_connected)
                return None

        # Flatten list of lists and remove duplicates
        jack_ports = list(set(jack for sublist in jack_endpoints for jack in sublist))

        # It may be helpful to the user to see which ports are affected
        if jack_ports:
            print(f'Ports: {" ".join(sorted(jack_ports))}')

        return jack_ports

    def get_switch_ports(self, switch_xname):
        """Get a list of ports for a switch.

        Args:
            switch_xname: component name of switch

        Returns:
            List of port names (switch xname augmented by port)
            Or None if there is an error with the fabric controller API
        """

        # Get port information from fabric controller via gateway API.
        try:
            response = self.fabric_client.get('port-links')
        except APIError as err:
            LOGGER.error('Failed to get port links from fabric controller: {}'.format(err))
            return None

        # Get result as JSON.
        try:
            portinfo = response.json()
        except ValueError as err:
            LOGGER.error('Failed to parse JSON from fabric controller response: {}'.format(err))
            return None

        # Check result for sanity.
        if 'ports' not in portinfo:
            LOGGER.error('Key "ports" missing from fabric controller port links.')
            return None

        # Create list of ports.
        ports = []
        for key in portinfo['ports']:
            for port in portinfo['ports'][key]:
                if XName(switch_xname).contains_component(XName(port)):
                    ports.append(port)

        return ports

    def create_port_set(self, portset):
        """Create a port set for a list of ports.

        Args:
            portset: JSON with name and ports as required by fabric controller.

        Returns:
            True if creation is successful
            False if there is an error with the fabric controller API
        """
        portset_json = json.dumps(portset)

        # Create port set through fabric controller gateway API.
        try:
            self.fabric_client.post('port-sets', payload=portset_json)
        except APIError as err:
            LOGGER.error('Failed to create port set through fabric controller: {}'.format(err))
            return False

        return True

    def get_port_set_config(self, portset_name):
        """Get a port set configuration (per port).

        Args:
            portset_name: name of port set

        Returns:
            configuration of ports in set
            Or None if there is an error with the fabric controller API
        """
        # Get port set configuration from fabric controller via gateway API.
        try:
            response = self.fabric_client.get('port-sets', portset_name, 'config')
        except APIError as err:
            LOGGER.error('Failed to get port set config from fabric controller: {}'.format(err))
            return None

        # Get result as JSON.
        try:
            portset_config = response.json()
            LOGGER.debug("Portset config for {}:\n{}".format(portset_name, portset_config))
        except ValueError as err:
            LOGGER.error('Failed to parse JSON from fabric controller response: {}'.format(err))
            return None

        # Check result for sanity.
        if 'ports' not in portset_config:
            LOGGER.error('Key "ports" missing from fabric controller port set config.')
            return None
        if portset_config['ports'][0] and 'config' not in portset_config['ports'][0]:
            LOGGER.error('Key "config" missing from port in fabric port set config.')
            return None

        return portset_config

    def update_port_set(self, portset_name, port_config, enable):
        """Update a port set to enable/disable.

        Args:
            portset_name: name of port set
            port_config: port configuration
            enable: True to enable or False to disable

        Returns:
            True if update is successful
            False if there is an error with the fabric controller API
        """
        # Example: {"autoneg": true, "enable": false,
        #           "flowControl": {"rx": true, "tx": true}, "speed": "100"}
        # Boolean values are not capitalized and speed value is a string.
        port_config['enable'] = enable
        config_json = json.dumps(port_config)

        # Update port set through fabric controller gateway API.
        try:
            self.fabric_client.put('port-sets', portset_name, 'config', payload=config_json)
        except APIError as err:
            LOGGER.error('Failed to update port set {} '
                         'through fabric controller: {}'.format(portset_name, err))
            return False

        return True

    def delete_port_set(self, portset_name):
        """Delete a port set.

        Args:
            portset_name: name of port set

        Returns:
            True if deletion is successful
            False if there is an error with the fabric controller API
        """
        # Delete port set through fabric controller gateway API.
        try:
            self.fabric_client.delete('port-sets', portset_name)
        except APIError as err:
            LOGGER.error('Failed to delete port set through fabric controller: {}'.format(err))
            return False

        return True

    def delete_port_set_list(self, portset_names):
        """Delete a list of port sets.

        Args:
            portset_names: a list of port set names

        Returns:
            None
        """
        for ps_name in portset_names:
            LOGGER.debug("Deleting port set {}".format(ps_name))
            self.delete_port_set(ps_name)

    def get_port_sets(self):
        """Get port sets.

        Returns:
            Port sets.
        """
        # Get port sets from fabric controller via gateway API.
        try:
            response = self.fabric_client.get('port-sets')
        except APIError as err:
            LOGGER.error('Failed to get port sets from fabric controller: {}'.format(err))
            return None

        # Get result as JSON.
        try:
            portsets = response.json()
        except ValueError as err:
            LOGGER.error('Failed to parse JSON from fabric controller response: {}'.format(err))
            return None

        return portsets
