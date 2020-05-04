"""
The main entry point for the switch subcommand.

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
import sys

from sat.apiclient import APIError, FabricControllerClient
from sat.session import SATSession
from sat.util import pester
from sat.xname import XName

LOGGER = logging.getLogger(__name__)

# Prefix for port set names created.
PS_PRE = 'SAT-'


def do_switch(args):
    """Runs the sat switch subcommand with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Exits with 1 for an error getting ports.
    Exits with 2 if no ports are found for the switch.
    Exits with 3 if port set already exists.
    Exits with 4 if creation of port set fails.
    Exits with 5 if problem occurs getting port configuration.
    Exits with 6 if disable/enable of port set fails.
    """

    def clear_port_sets():
        for ps_name in created_ps_names:
            LOGGER.debug("Deleting port set {}".format(ps_name))
            delete_port_set(ps_name)

    if not args.dry_run and not args.action:
        LOGGER.error("The action option is required if not a dry run, exiting.")
        sys.exit(0)

    if not (args.disruptive or args.dry_run):
        if not pester("Enable/disable of switch can impact system. Continue?"):
            sys.exit(0)

    ports = get_switch_ports(args.xname)
    if ports is None:
        sys.exit(1)
    if not ports:
        LOGGER.error('No ports found for switch {}'.format(args.xname))
        sys.exit(2)

    created_ps_names = []
    portset = {}
    portset_name = PS_PRE + args.xname
    portset['name'] = portset_name
    portset['ports'] = ports
    if args.save_portset:
        portset_file = args.xname + "-ports.json"
        output_json(portset, portset_file)

    portsets = get_port_sets()
    if portset_name in portsets['names']:
        if args.over_write:
            LOGGER.error('Port set {} already exists, deleting it.'.format(portset_name))
            delete_port_set(portset_name)
        else:
            LOGGER.error('Port set {} already exists, exiting.'.format(portset_name))
            sys.exit(3)
    for port in ports:
        ps_name = PS_PRE + port
        if ps_name in portsets['names']:
            if args.over_write:
                LOGGER.error('Port set {} already exists, deleting it.'.format(ps_name))
                delete_port_set(ps_name)
            else:
                LOGGER.error('Port set {} already exists, exiting.'.format(ps_name))
                sys.exit(3)

    # Create port set for switch.
    if not create_port_set(portset):
        sys.exit(4)
    created_ps_names.append(portset_name)

    # Get configuration for all of the switch ports.
    portset_config = get_port_set_config(portset_name)
    if not portset_config:
        sys.exit(4)

    # Create port set for each port.
    for port in ports:
        portset = {}
        portset['name'] = PS_PRE + port
        portset['ports'] = [port]
        LOGGER.debug("Creating port set {}".format(portset['name']))
        if not create_port_set(portset):
            clear_port_sets()
            sys.exit(4)
        created_ps_names.append(portset['name'])

    port_config = {}
    for port in ports:
        for config in portset_config['ports']:
            if config['xname'] == port:
                port_config[port] = config['config']
                break
        else:
            LOGGER.error("Failed to find config for port {}." + port)
            clear_port_sets()
            sys.exit(5)

    if args.dry_run:
        LOGGER.info('Dry run, so not enabling/disabling switch {}.'.format(args.xname))
    else:
        if args.action == 'disable': 
            LOGGER.info('Disabling ports on switch {}.'.format(args.xname))
        else:
            LOGGER.info('Enabling ports on switch {}.'.format(args.xname))
        for port in ports:
            if not update_port_set(PS_PRE + port, port_config[port], args.action == 'enable'):
                clear_port_sets()
                sys.exit(6)

    clear_port_sets()

    if args.dry_run:
        print('Dry run completed with no action to enable/disable switch.')
    else:
        if args.action == 'disable':
            print('Switch has been disabled and is ready for replacement.')
        else:
            print('Switch has been enabled.')

def output_json(switch_ports, filepath):
    """Output dictionary to file in JSON format."""
    try:
        with open(filepath, mode="w") as jsonfile:
            json.dump(switch_ports, jsonfile, indent=4)
    except (OSError, IOError):
        LOGGER.error("Unable to open file for writing: " + filepath)
        return


def get_switch_ports(switch_xname):
    """Get a list of ports for a switch.

    Args:
        switch_xname: component name of switch

    Returns:
        List of port names (switch xname augmented by port)
        Or None if there is an error with the fabric controller API
    """
    client = FabricControllerClient(SATSession())

    # Get port information from fabric controller via gateway API.
    try:
        response = client.get('port-links')
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


def create_port_set(portset):
    """Create a port set for a list of ports.

    Args:
        portset: JSON with name and ports as required by fabric controller.

    Returns:
        True if creation is successful
        False if there is an error with the fabric controller API
    """
    client = FabricControllerClient(SATSession())

    portset_json = json.dumps(portset)

    # Create port set through fabric controller gateway API.
    try:
        response = client.post('port-sets', payload=portset_json)
    except APIError as err:
        LOGGER.error('Failed to create port set through fabric controller: {}'.format(err))
        return False

    return True


def get_port_set_config(portset_name):
    """Get a port set configuration (per port).

    Args:
        portset_name: name of port set

    Returns:
        configuration of ports in set
        Or None if there is an error with the fabric controller API
    """
    client = FabricControllerClient(SATSession())

    # Get port set configuration from fabric controller via gateway API.
    try:
        response = client.get('port-sets', portset_name, 'config')
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


def update_port_set(portset_name, port_config, enable):
    """Update a port set to enable/disable.

    Args:
        portset_name: name of port set
        port_config: port configuration
        enable: True to enable or False to disable

    Returns:
        True if update is successful
        False if there is an error with the fabric controller API
    """
    client = FabricControllerClient(SATSession())

    # Example: {"autoneg": true, "enable": false,
    #           "flowControl": {"rx": true, "tx": true}, "speed": "100"}
    # Boolean values are not capitalized and speed value is a string.
    port_config['enable'] = enable
    config_json = json.dumps(port_config)

    # Update port set through fabric controller gateway API.
    try:
        response = client.put('port-sets', portset_name, 'config', payload=config_json)
    except APIError as err:
        LOGGER.error('Failed to update port set {} '
                     'through fabric controller: {}'.format(portset_name, err))
        return False

    return True


def delete_port_set(portset_name):
    """Delete a port set.

    Args:
        portset_name: name of port set

    Returns:
        True if deletion is successful
        False if there is an error with the fabric controller API
    """
    client = FabricControllerClient(SATSession())

    # Delete port set through fabric controller gateway API.
    try:
        response = client.delete('port-sets', portset_name)
    except APIError as err:
        LOGGER.error('Failed to delete port set through fabric controller: {}'.format(err))
        return False

    return True


def get_port_sets():
    """Get port sets.

    Returns:
        Port sets.
    """
    client = FabricControllerClient(SATSession())

    # Get port sets from fabric controller via gateway API.
    try:
        response = client.get('port-sets')
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
