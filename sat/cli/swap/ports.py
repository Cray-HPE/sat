"""
Contains functions for modifying port configuration via fabric API.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
from sat.cli.swap.cable_endpoints import JACK_XNAME_REGEX, CableEndpoints
from sat.session import SATSession

LOGGER = logging.getLogger(__name__)

INF = inflect.engine()


class PortManager:
    """Manages port operations that use the Fabric Controller API"""

    def __init__(self):
        self.fabric_client = FabricControllerClient(SATSession())
        self.cable_endpoints = CableEndpoints()

    def get_ports(self):
        """Get a list of port document links

        Returns:
            A list of port paths or None
        """

        # Get ports information using fabric manager API.
        try:
            response = self.fabric_client.get('fabric/ports')
        except APIError as err:
            LOGGER.error(f'Failed to get ports from fabric manager: {err}')
            return None

        # Get result as JSON.
        try:
            ports = response.json()
        except ValueError as err:
            LOGGER.error(f'Failed to parse JSON from fabric manager response: {err}')
            return None

        return ports.get('documentLinks')

    def get_port(self, port_link):
        """Get port data using document link

        Args:
            port_link (str): The full path of the port document link

        Returns:
            A dictionary of port data or None if there is an error
        """

        # Get port information from fabric manager via gateway API.
        try:
            response = self.fabric_client.get(port_link)
        except APIError as err:
            LOGGER.error('Failed to get port information from fabric manager: {}'.format(err))
            return None

        # Get result as JSON.
        try:
            port = response.json()
        except ValueError as err:
            LOGGER.error('Failed to parse JSON from fabric manager response: {}'.format(err))
            return None

        return port

    def get_switches(self):
        """Get a list of switch document links

        Returns:
            A list of switch paths or None
        """

        # Get switches information using fabric manager API.
        try:
            response = self.fabric_client.get('fabric/switches')
        except APIError as err:
            LOGGER.error('Failed to get switches from fabric manager: {}'.format(err))
            return None

        # Get result as JSON.
        try:
            switches = response.json()
        except ValueError as err:
            LOGGER.error('Failed to parse JSON from fabric manager response: {}'.format(err))
            return None

        return switches.get('documentLinks')

    def get_switch(self, switch_link):
        """Get switch data using document link

        Args:
            switch_link (str): The full path of the switch document link

        Returns:
            A dictionary of switch data or None if there is an error
        """

        # Get switch information from fabric manager via gateway API.
        try:
            response = self.fabric_client.get(switch_link)
        except APIError as err:
            LOGGER.error('Failed to get switch information from fabric manager: {}'.format(err))
            return None

        # Get result as JSON.
        try:
            switch = response.json()
        except ValueError as err:
            LOGGER.error('Failed to parse JSON switch data from fabric manager response: {}'.format(err))
            return None

        return switch

    def get_port_policies(self):
        """Get a list of port policy document links

        Returns:
            A list of port policy paths or None
        """

        # Get port policy information using fabric manager API.
        try:
            response = self.fabric_client.get('fabric/port-policies')
        except APIError as err:
            LOGGER.error('Failed to get port policies from fabric manager: {}'.format(err))
            return None

        # Get result as JSON.
        try:
            port_policies = response.json()
        except ValueError as err:
            LOGGER.error('Failed to parse JSON from fabric manager response: {}'.format(err))
            return None

        return port_policies.get('documentLinks')

    def get_port_data_list(self, port_links):
        """Get a list of dictionaries for ports using document links for each port

        Args:
            port_links (list): a list of port document links
                Example: [/fabric/ports/x3000c0r15j14p0]

        Returns:
            A list of dictionaries for ports or None if there is an error
                Example: {"xname": "x3000c0r21j14p0",
                          "port_link": "/fabric/ports/x3000c0r21j14p0",
                          "policy_link: "/fabric/port-policies/fabric-policy"}
        """

        port_data_list = []
        for port_link in port_links:
            port = self.get_port(port_link)

            if port is None:
                LOGGER.error(f'Failed to get port data for {port_link}.')
                return None

            port_data = {}
            try:
                port_data['xname'] = port['conn_port']
                port_data['port_link'] = port_link
                port_data['policy_link'] = port['portPolicyLinks'][0]
            except KeyError as err:
                LOGGER.error('Key %s for port data missing from fabric manager switch information.', err)
                return None

            port_data_list.append(port_data)

        return port_data_list

    def get_jack_port_data_list(self, jack_xnames, force=False):
        """Get a list of dictionaries for ports for one or more jacks

        Args:
            jack_xnames (list): a list of jack xnames
            force (bool): Ignore if unable to validate jack_xnames or
                if supplied jacks are not connected by a cable.
                If False, return None for these cases.

        Returns:
            A list of dictionaries for ports or None if there is an error
        """

        # If a non-jack was given, return None
        non_matching_xnames = [xname for xname in jack_xnames if not re.match(JACK_XNAME_REGEX, xname)]
        if non_matching_xnames:
            num_non_matching = len(non_matching_xnames)
            LOGGER.error(f'{INF.plural("xname", num_non_matching)} {",".join(non_matching_xnames)} '
                         f'{INF.plural_verb("does", num_non_matching)} not match the format of a jack xname.')
            return None

        # Load the p2p file in order to get the endpoints and validate the jack_xnames input
        valid_p2p_jacks = False
        valid_p2p_file = self.cable_endpoints.load_cables_from_p2p_file()
        if not valid_p2p_file:
            LOGGER.warning('Error loading cable data from p2p file')
        else:
            # Check if all jacks given are in the p2p file
            # Check if all jacks given are for the same single cable
            valid_p2p_jacks = self.cable_endpoints.validate_jacks_using_p2p_file(jack_xnames)

        if not valid_p2p_jacks and not force:
            LOGGER.error(f'Exiting due to errors validating jack xnames {jack_xnames}')
            return None

        all_jack_xnames = []
        if valid_p2p_file:
            # Add the linked jacks to the list of jacks input
            all_jack_xnames = []
            for jack in jack_xnames:
                # Make sure that the jack is in the p2p file
                cable = self.cable_endpoints.get_cable(jack)
                if cable:
                    linked_jacks = self.cable_endpoints.get_linked_jack_list(jack)
                    if linked_jacks is not None:
                        all_jack_xnames.extend(linked_jacks)
            if all_jack_xnames:
                all_jack_xnames = set(all_jack_xnames)

        if not all_jack_xnames:
            LOGGER.info(f'Continuing with errors validating jack xnames {jack_xnames}')
            all_jack_xnames = jack_xnames

        LOGGER.info(f'Using jack xname list: {all_jack_xnames}')
        ports = self.get_ports()
        if ports is None:
            LOGGER.error('Failed to get ports.')
            return None

        port_links = []
        for jack_xname in all_jack_xnames:
            for doc_link in ports:
                port = doc_link.split('/')[-1]
                if port.startswith(f'{jack_xname}p'):
                    port_links.append(doc_link)

        port_data_list = self.get_port_data_list(port_links)
        return port_data_list

    def get_switch_port_data_list(self, switch_xname):
        """Get a list of dictionaries for ports for a switch.

        Args:
            switch_xname: component name of switch

        Returns:
            A list of dictionaries for ports or None if there is an error
        """

        switches = self.get_switches()
        if switches is None:
            LOGGER.error('Failed to get switches.')
            return None

        # Get the document link for the switch_xname input
        # Should only be one so break after find it
        switch_link = None
        for doc_link in switches:
            switch = doc_link.split('/')[-1]
            if switch in (switch_xname, f'{switch_xname}b0'):
                switch_link = doc_link
                break

        if switch_link is None:
            LOGGER.error(f'Switch {switch_xname} missing from fabric manager switches.')
            return None

        switch = self.get_switch(switch_link)
        if switch is None:
            LOGGER.error(f'Failed to get switch data for {switch_link}.')
            return None

        edge_ports = []
        fabric_ports = []
        try:
            edge_ports = switch['edgePortLinks']
            fabric_ports = switch['fabricPortLinks']
        except KeyError as err:
            LOGGER.warning('Key %s for switch data missing from fabric manager switch information.', err)

        port_data_list = self.get_port_data_list(edge_ports)
        fabric_list = self.get_port_data_list(fabric_ports)
        if port_data_list is None:
            port_data_list = fabric_list
        elif fabric_list is not None:
            port_data_list.extend(fabric_list)

        return port_data_list

    def update_port_policy_link(self, port_link, policy_link):
        """Update a port to use a new policy

        Args:
            port_link (str): The full path of the port document link
            policy_link (str): The full path of the new port policy

        Returns:
            True if update is successful
            False if there is an error with the fabric manager API
        """

        # Example: {"portPolicyLinks":["/fabric/port-policies/edge-policy"]}
        port_config = {}
        port_config['portPolicyLinks'] = [policy_link]
        config_json = json.dumps(port_config)
        LOGGER.debug(f'Updating port: {port_link}')
        LOGGER.debug(f'config_json: {config_json}')

        # Update port to use policy through fabric manager API.
        try:
            self.fabric_client.patch(port_link, payload=config_json)
        except APIError as err:
            LOGGER.error('Failed to update portPolicyLinks {} '
                         'through fabric manager: {}'.format(port_link, err))
            return False

        return True

    def create_offline_port_policy(self, existing_policy_link, new_policy_prefix):
        """Create a port policy to be used to OFFLINE ports if it doesn't already exist

        Args:
            existing_policy_link (str): The full path of the current port policy used
            new_policy_prefix (str): Prefix to be added to the current policy used

        Returns:
            True if creation is successful
            False if there is an error with the fabric manager API
        """

        # Get the list of port policies and see if the offline port policy already exists
        port_policies = self.get_port_policies()
        if port_policies is None:
            LOGGER.error('Failed to get port policies.')
            return False

        path_parts = existing_policy_link.split('/')
        offline_policy = '/'.join(path_parts[:-1]) + '/' + new_policy_prefix + path_parts[-1]

        if offline_policy in port_policies:
            LOGGER.info(f'Using existing offline policy: {offline_policy}')
        else:
            new_policy_config = {
                'state': 'OFFLINE',
                'documentSelfLink': new_policy_prefix + path_parts[-1]
            }
            LOGGER.debug(f'Creating offline policy: {offline_policy}')
            LOGGER.debug(f'new_policy_config: {new_policy_config}')

            # Create port policy through fabric manager API.
            try:
                self.fabric_client.post('/'.join(path_parts[:-1]), json=new_policy_config)
            except APIError as err:
                LOGGER.error('Failed to create port policy {} '
                             'through fabric manager: {}'.format(offline_policy, err))
                return False

        return True
