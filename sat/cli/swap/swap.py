"""
Contains the code for swapping components.

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

import abc
import json
import logging

import inflect

from sat.cli.swap.ports import PortManager
from sat.util import pester

LOGGER = logging.getLogger(__name__)

INF = inflect.engine()

# Prefix for offline port policy created.
POL_PRE = 'sat-offline-'

ERR_INVALID_OPTIONS = 1
ERR_GET_PORTS_FAIL = 2
ERR_NO_PORTS_FOUND = 3
ERR_PORT_POLICY_CREATE_FAIL = 4
ERR_PORT_POLICY_TOGGLE_FAIL = 5


class Swapper(metaclass=abc.ABCMeta):
    """Base class for swapping components"""

    def __init__(self):
        self.port_manager = PortManager()
        self.component_type = ''

    @abc.abstractmethod
    def get_port_data(self, component_id, force):
        """Get a list of dictionaries for ports to enable/disable for this swap.

        Args:
            component_id (str, list): The xname or list of xnames
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.  (Not used for switch swapping)

        Returns:
            A list of dictionaries with port data.
        """
        raise NotImplementedError(f'{self.__class__.__name__}.get_port_data')

    def component_name(self, component_id):
        """Get a string name of a component id.

        Subclasses can override this method if component_id is a type
            other than string.

        Args:
            component_id (str): An xname

        Returns:
            The xname
        """
        return component_id

    def _check_arguments(self, action, dry_run, disruptive):
        """Check that given options are valid for a swap.

        Args:
            action (str): 'enable' or 'disable'
            dry_run (bool): if True, skip applying configuration to ports
            disruptive (bool): if True, do not confirm disable/enable

        Raises:
            SystemExit(1): if invalid options
        """
        if not dry_run and not action:
            LOGGER.error('The action option is required if not a dry run, exiting.')
            raise SystemExit(ERR_INVALID_OPTIONS)

        if dry_run and action:
            LOGGER.error('The action option is not valid with the dry run option.')
            raise SystemExit(ERR_INVALID_OPTIONS)

        if not (disruptive or dry_run or
                pester(f'Enable/disable of {self.component_type} can impact system. Continue?')):
            raise SystemExit(ERR_INVALID_OPTIONS)

    def get_and_check_ports(self, component_id, force):
        """Get list of dictionaries for ports for this swap and check result.

        Args:
            component_id (str, list): The xname or list of xnames
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.  (Not used for switch swapping)

        Returns:
            A list of dictionaries for ports

        Raises:
            SystemExit(2): if getting ports failed
            SystemExit(3): if no ports were found
        """
        ports = self.get_port_data(component_id, force)
        if ports is None:
            raise SystemExit(ERR_GET_PORTS_FAIL)
        if not ports:
            LOGGER.error(f'No ports found for {self.component_type} {component_id}')
            raise SystemExit(ERR_NO_PORTS_FOUND)

        return ports

    def create_offline_port_policies(self, port_data_list):
        """Create port policies to be used to OFFLINE ports

        Args:
            port_data_list (list): list of dictionaries with current port data

        Raises:
            SystemExit(4): if creating a new port policy fails
        """

        # Create new policies to OFFLINE ports
        # Name the new policies with POL_PRE followed by the current policy name
        # unless the current policy name is already a POL_PRE policy
        #
        # Create a unique list of policies and create a new policy for each one
        policy_list = list(set(p['policy_link'] for p in port_data_list))
        LOGGER.debug(f'policy_list: {policy_list}')
        for policy in policy_list:
            policy_name = policy.split('/')[-1]
            if not policy_name.startswith(POL_PRE):
                new_policy_name = POL_PRE + policy_name
                LOGGER.debug(f'Creating policy {new_policy_name} for {policy}')
                if not self.port_manager.create_offline_port_policy(policy, POL_PRE):
                    LOGGER.error(f'Error creating policy {new_policy_name} for {policy}')
                    raise SystemExit(ERR_PORT_POLICY_CREATE_FAIL)

    def update_ports_state(self, port_data_list, action):
        """Update the state for ports based on action

        Args:
            port_data_list (list): list of dictionaries with current port data
            action (str): the action to perform, ('enable' or 'disable')

        Returns:
            True if all ports were successfully updated, else False.
        """

        # Use success to return overall success
        # Returns True if there were no errors
        # Returns False if any port could not be updated
        # Keeps updating the remaining ports if an error occurs for any single port
        success = True
        for port_data in port_data_list:
            # Determine which policy to use depending on action and current policy
            path_parts = port_data['policy_link'].split('/')
            policy_name = path_parts[-1]
            if action == "enable" and policy_name.startswith(POL_PRE):
                # Remove prefix and use original policy
                policy_name = policy_name[len(POL_PRE):]
            elif action == "disable" and not policy_name.startswith(POL_PRE):
                # Add prefix to policy
                policy_name = POL_PRE + policy_name

            port_link = port_data['port_link']
            new_policy = '/'.join(path_parts[:-1]) + '/' + policy_name
            LOGGER.debug(f'Updating {port_link} with policy: {new_policy}')
            if not self.port_manager.update_port_policy_link(port_link, new_policy):
                LOGGER.error(f'Error updating {port_link} with policy: {new_policy}')
                success = False

        return success

    def swap_component(self, action, component_id, disruptive, dry_run, save_ports, force=False):
        """Enable or disable ports specified by self.component_id

        Args:
            action (str): the action to perform, ('enable' or 'disable')
            component_id (str, list): The xname or list of xnames
            disruptive (bool): if True, do not confirm disable/enable
            dry_run (bool): if True, skip applying action to ports,
                but still create the port set affected.
            save_ports (bool): if True, save port_data (xname, port_link, policy_link)
                (for all ports affected) to a file in the local working directory.
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.  (Not used for switch swapping)

        Raises:
            SystemExit: if a failure occurred.  Exit codes are as follows:
                1 if invalid options were given.
                2 for an error getting ports.
                3 if no ports were found for the component.
                4 if creation of port policy used to disable port fails.
                5 if applying a port policy to any port fails.
        """

        # For a switch, this is the switch xname, and for a cable it is a comma-separated string of xnames
        component_name = self.component_name(component_id)

        self._check_arguments(action, dry_run, disruptive)

        # Get the port data (xname, port_link, policy_link) to enable/disable for this swap
        port_data_list = self.get_and_check_ports(component_id, force)

        # Log the affected port xnames
        LOGGER.info(f'Ports: {" ".join([p["xname"] for p in port_data_list])}')

        if save_ports:
            ports_filename = f'{component_name}-ports.json'
            output_json(port_data_list, ports_filename)

        if dry_run:
            LOGGER.info(f'Dry run, so not enabling/disabling {self.component_type} {component_name}')
        else:
            LOGGER.info(
                f'{("Disabling", "Enabling")[action == "enable"]} '
                f'ports on {self.component_type} {component_name}'
            )
            if action == 'disable':
                self.create_offline_port_policies(port_data_list)

            if not self.update_ports_state(port_data_list, action):
                # at least one of the enable/disable ports failed
                LOGGER.error(f'Failed to {action} {self.component_type} {component_name}.')
                raise SystemExit(ERR_PORT_POLICY_TOGGLE_FAIL)

            LOGGER.info(
                f'{self.component_type.capitalize()} has '
                f'been {("disabled", "enabled")[action == "enable"]}'
                f'{(" and is ready for replacement.", ".")[action == "enable"]}'
            )


class CableSwapper(Swapper):
    """Swaps cables.

    Implements a get_port_data method specific to cables that should take a list of jack xnames.
    """

    def __init__(self):
        super().__init__()
        self.component_type = 'cable'

    def get_port_data(self, component_id, force):
        """Get a list of dictionaries for ports for this cable.

        Args:
            component_id (list): a list of jack xnames
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.

        Returns:
            A list of dictionaries for ports or None if getting ports failed.
        """
        return self.port_manager.get_jack_port_data_list(component_id, force)

    def component_name(self, component_id):
        """Get a string name of a component id.

        For a cable, this is a comma-separated string of xnames.

        Args:
            component_id(list): the list of jack xnames.

        Returns:
            A comma-separated string of xnames.
        """
        return ",".join(component_id)


class SwitchSwapper(Swapper):
    """Swaps switches.

    Implements a get_port_data method specific to switches that should take a single switch xname.
    """

    def __init__(self):
        super().__init__()
        self.component_type = 'switch'

    def get_port_data(self, component_id, force):
        """Get a list of dictionaries for ports for this switch.

        Args:
            component_id (str): the switch xname
            force: unused

        Returns:
            A list of dictionaries for ports or None if getting ports failed.
        """

        return self.port_manager.get_switch_port_data_list(component_id)


def output_json(switch_ports, filepath):
    """Output dictionary to file in JSON format."""
    try:
        with open(filepath, mode="w") as jsonfile:
            json.dump(switch_ports, jsonfile, indent=4)
    except (OSError, IOError):
        LOGGER.error("Unable to open file for writing: %s", filepath)
        return
