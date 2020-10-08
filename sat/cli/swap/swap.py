"""
Contains the code for swapping components.

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

import abc
import json
import logging

import inflect

from sat.cached_property import cached_property
from sat.cli.swap.ports import PortManager
from sat.util import pester

LOGGER = logging.getLogger(__name__)

INF = inflect.engine()

# Prefix for port set names created.
PS_PRE = 'SAT-'

ERR_INVALID_OPTIONS = 1
ERR_GET_PORTS_FAIL = 2
ERR_NO_PORTS_FOUND = 3
ERR_PORTSET_EXISTS = 4
ERR_PORTSET_CREATE_FAIL = 5
ERR_PORTSET_DELETE_FAIL = 6
ERR_PORTSET_GET_CONFIG = 7
ERR_PORTSET_TOGGLE_FAIL = 8


class Swapper(metaclass=abc.ABCMeta):
    """Base class for swapping components"""

    def __init__(self):
        self.port_manager = PortManager()
        self.component_type = ''

        # Keep track of port sets this swap has created
        self.created_port_sets = []

    @abc.abstractmethod
    def get_ports(self, component_id, force):
        """Get a list of ports to enable/disable for this swap.

        Args:
            component_id (str, list): The xname or list of xnames
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.  (Not used for switch swapping)

        Returns:
            A list of port xnames.
        """
        raise NotImplementedError(f'{self.__class__.__name__}.get_ports')

    @cached_property
    def existing_port_sets(self):
        """A list of port set names that existed prior to this swap"""
        return self._get_existing_port_set_names()

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

    def _apply_configuration(self, port_set_config, action):
        """Apply configuration to ports

        Args:
            port_set_config (dict): A dictionary mapping from port xnames to
                port set configuration
            action (str): 'enable' or 'disable'

        Returns:
            True if all configuration was successfully applied, else False.
        """
        return all(
            self.port_manager.update_port_set(f'{PS_PRE}{port_xname}', port_config, action == 'enable')
            for port_xname, port_config in port_set_config.items()
        )

    def _check_arguments(self, action, dry_run, disruptive):
        """Check that given options are valid for a swap.

        Args:
            action (str): 'enable' or 'disable'
            dry_run (bool): if True, skip applying configuration to ports,
                but still create port sets.
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

    def _check_port_set_does_not_exist(self, port_set_name, overwrite):
        """Check if port set exists and delete it if self.overwrite is True

        Args:
            port_set_name (str): The string name of the port set
            overwrite (bool): if True, overwrite existing port sets.

        Raises:
            SystemExit(4): if overwrite is False and port set exists
            SystemExit(5): if deleting an existing port set failed.
        """
        if port_set_name in self.existing_port_sets:
            if overwrite:
                LOGGER.warning(f'Port set {port_set_name} already exists, deleting it.')
                if not self.port_manager.delete_port_set(port_set_name):
                    self._clean_up_and_exit(ERR_PORTSET_DELETE_FAIL)
            else:
                LOGGER.error(f'Port set {port_set_name} already exists, exiting.')
                self._clean_up_and_exit(ERR_PORTSET_EXISTS)

    def _check_port_set_config(self, ports, port_set_config):
        """Check that the port set configuration dictionary contains all the given ports

        Args:
             ports (list): A list of port xnames
             port_set_config (dict): A dictionary mapping port xnames to configuration

        Raises:
            SystemExit(7): if any of the specified ports don't exist in port_set_config
        """
        missing_ports = set(ports) - set(port_set_config.keys())
        if missing_ports:
            LOGGER.error(
                f'Unable to find configuration for {INF.plural("port", len(missing_ports))} '
                f'{",".join(missing_ports)}.'
            )
            self._clean_up_and_exit(ERR_PORTSET_GET_CONFIG)

    def _clean_up_and_exit(self, error_code):
        """Exit and clean up any existing port sets

        Args:
            error_code (int): The return code with which to exit

        Raises:
            SystemExit(error_code): exits with the given error code
        """
        self._clean_up_port_sets()
        raise SystemExit(error_code)

    def _create_port_set(self, port_set_name, ports, save_port_set=False):
        """Create a port set.

        Args:
            port_set_name (str): The name of the port set to create
            ports (list): The list of ports for this port set
            save_port_set (bool): if True, save the port set to a file
                in the current working directory.

        Raises:
            SystemExit(5): if creating a new port set fails
        """
        port_set_data = {
            'name': port_set_name,
            'ports': ports
        }

        if save_port_set:
            port_set_filename = f'{port_set_name.replace(PS_PRE,"",1)}-ports.json'
            output_json(port_set_data, port_set_filename)

        LOGGER.debug(f'Creating port set {port_set_name}')
        if not self.port_manager.create_port_set(port_set_data):
            self._clean_up_and_exit(ERR_PORTSET_CREATE_FAIL)

        self.created_port_sets.append(port_set_name)

    def _get_existing_port_set_names(self):
        """Get the names of all currently-defined port sets.

        Returns:
            A list of port set names

        Raises:
            SystemExit(2): if a valid response was not returned
        """
        port_sets = self.port_manager.get_port_sets()
        if not (port_sets and port_sets.get('names')):
            self._clean_up_and_exit(ERR_GET_PORTS_FAIL)

        return port_sets['names']

    def _clean_up_port_sets(self):
        """Clean up existing port sets"""
        if self.created_port_sets:
            self.port_manager.delete_port_set_list(self.created_port_sets)

    def _get_port_set_config(self, port_set_name):
        """Get port set configuration and return it as a map of xnames to config data.

        Args:
            port_set_name (str): the name of a port set

        Returns:
            A dictionary of port xnames to configuration data

        Raises:
            SystemExit(7): if failed to get config
        """
        port_set_config = self.port_manager.get_port_set_config(port_set_name)
        if not port_set_config:
            self._clean_up_and_exit(ERR_PORTSET_GET_CONFIG)
        return {
            config.get('xname'): config.get('config') for config in port_set_config['ports'] if config.get('config')
        }

    def get_and_check_ports(self, component_id, force):
        """Get ports for this swap and check result.

        Args:
            component_id (str, list): The xname or list of xnames
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.  (Not used for switch swapping)

        Returns:
            A list of port xnames

        Raises:
            SystemExit(2): if getting ports failed
            SystemExit(3): if no ports were found
        """
        ports = self.get_ports(component_id, force)
        if ports is None:
            raise SystemExit(ERR_GET_PORTS_FAIL)
        if not ports:
            LOGGER.error(f'No ports found for {self.component_type} {component_id}')
            raise SystemExit(ERR_NO_PORTS_FOUND)

        return ports

    def swap_component(self, action, component_id, disruptive, dry_run, overwrite, save_port_set, force=False):
        """Enable or disable ports specified by self.component_id

        Args:
            action (str): the action to perform, ('enable' or 'disable')
            component_id (str, list): The xname or list of xnames
            disruptive (bool): if True, do not confirm disable/enable
            dry_run (bool): if True, skip applying configuration to ports,
                but still create port sets.
            overwrite (bool): if True, overwrite existing port sets.
            save_port_set (bool): if True, save a port set (for all ports)
                to a file in the local working directory.
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.  (Not used for switch swapping)

        Raises:
            SystemExit: if a failure occurred.  Exit codes are as follows:
                1 if invalid options were given.
                2 for an error getting ports.
                3 if no ports were found for the component.
                4 if port set already exists.
                5 if creation of port set fails.
                6 if deletion of port set fails.
                7 if problem occurs getting port configuration.
                8 if disable/enable of port set fails.
        """

        # For a switch, this is the switch xname, and for a cable it is a comma-separated string of xnames
        component_name = self.component_name(component_id)

        self._check_arguments(action, dry_run, disruptive)

        # Get the ports to enable/disable for this swap
        ports = self.get_and_check_ports(component_id, force)

        all_ports_port_set_name = f'{PS_PRE}{component_name}'

        # Check if any port sets exist and/or if we are overwriting, for the
        # port set for all ports, and each individual port set we are creating
        self._check_port_set_does_not_exist(all_ports_port_set_name, overwrite)
        for port in ports:
            self._check_port_set_does_not_exist(f'{PS_PRE}{port}', overwrite)

        # Create a port set for all the ports
        self._create_port_set(all_ports_port_set_name, ports, save_port_set)

        # Get and check configuration for all of the ports
        port_set_config = self._get_port_set_config(all_ports_port_set_name)
        self._check_port_set_config(ports, port_set_config)

        # Create individual port sets for each port
        for port in ports:
            self._create_port_set(f'{PS_PRE}{port}', [port])

        if dry_run:
            LOGGER.info(f'Dry run, so not enabling/disabling {self.component_type} {component_name}')
        else:
            LOGGER.info(
                f'{("Disabling", "Enabling")[action == "enable"]} '
                f'ports on {self.component_type} {self.component_name}'
            )
            if not self._apply_configuration(port_set_config, action):
                LOGGER.error(f'Failed to {action} {self.component_type} {component_name}.')
                self._clean_up_and_exit(ERR_PORTSET_TOGGLE_FAIL)

        # Clean up port sets we created
        self._clean_up_port_sets()

        if dry_run:
            print(f'Dry run completed with no action to enable/disable {self.component_type}.')
        else:
            print(
                f'{self.component_type.capitalize()} has '
                f'been {("disabled", "enabled")[action == "enable"]}'
                f'{(" and is ready for replacement.", ".")[action == "enable"]}'
            )


class CableSwapper(Swapper):
    """Swaps cables.

    Implements a get_ports method specific to cables that should take a list of jack xnames.
    """

    def __init__(self):
        super().__init__()
        self.component_type = 'cable'

    def get_ports(self, component_id, force):
        """Get a list of ports for this cable.

        Args:
            component_id (list): a list of jack xnames
            force (bool): if True, skip checking that supplied ports are
                connected by a single cable.

        Returns:
            A list of ports or None if getting ports failed.
        """
        return self.port_manager.get_jack_ports(component_id, force)

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

    Implements a get_ports method specific to switches that should take a single switch xname.
    """

    def __init__(self):
        super().__init__()
        self.component_type = 'switch'

    def get_ports(self, component_id, force):
        """Get a list of ports for this switch.

        Args:
            component_id (str): the switch xname
            force: unused

        Returns:
            A list of ports or None if getting ports failed.
        """
        return self.port_manager.get_switch_ports(component_id)


def output_json(switch_ports, filepath):
    """Output dictionary to file in JSON format."""
    try:
        with open(filepath, mode="w") as jsonfile:
            json.dump(switch_ports, jsonfile, indent=4)
    except (OSError, IOError):
        LOGGER.error("Unable to open file for writing: %s", filepath)
        return
