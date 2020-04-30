"""
The main entry point for the switch subcommand.

Copyright 2020 Cray Inc. All Rights Reserved.
"""

import json
import logging
import sys

from sat.apiclient import APIError, FabricControllerClient
from sat.session import SATSession

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
        delete_port_set(portset_name)
        for port in ports:
            LOGGER.debug("Deleting port set {}".format(PS_PRE + port))
            delete_port_set(PS_PRE + port)
	
    ports = get_switch_ports(args.xname)
    if ports is None:
        sys.exit(1)
    if not ports:
        LOGGER.error('No ports found for switch {}'.format(args.xname))
        sys.exit(2)

    portset = {}
    portset_name = PS_PRE + args.xname
    portset['name'] = portset_name
    portset['ports'] = ports
    if args.save_portset:
        portset_file = args.xname + "-ports.json"
        output_json(portset, portset_file)

    portsets = get_port_sets()
    if portset_name in portsets['names']:
        LOGGER.error('Port set {} already exists, exiting.'.format(portset_name))
        sys.exit(3)
    for port in ports:
        ps_name = PS_PRE + port
        if ps_name in portsets['names']:
            LOGGER.error('Port set {} already exists, exiting.'.format(ps_name))
            sys.exit(3)

    # Create port set for switch.
    if not create_port_set(portset):
        sys.exit(4)

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
            # Deletion of port sets will log errors for those not created.
            clear_port_sets()
            sys.exit(4)

    port_config = {}
    for port in ports:
        for config in portset_config['ports']:
            if config['xname'] == port:
                port_config[port] = config['config']
                break
        if port not in port_config:
            LOGGER.error("Failed to find config for port {}." + port)
            clear_port_sets()
            sys.exit(5)

    if args.disruptive:
        for port in ports:
            # Disable port if preparing to replace switch, or enable if finished.
            if not update_port_set(PS_PRE + port, port_config[port], args.finish):
                clear_port_sets()
                sys.exit(6)
    else:
        LOGGER.info('Not disabling/enabling switch {} '
                    'without --disruptive option.'.format(args.xname))

    clear_port_sets()

    if args.disruptive:
        if args.finish:
            print('Switch has been disabled and is ready for replacment.')
        else:
            print('Switch has been enabled.')
    else:
        print('Trial run completed without actual disabling/enabling of switch.')


def output_json(switch_ports, filepath):
    """Output dictionary to file in JSON format."""
    try:
        with open(filepath, mode="w") as jsonfile:
            json.dump(switch_ports, jsonfile, indent=4)
    except (OSError, IOError):
        LOGGER.error("Unable to open file for writing: " + filepath)
        return


def get_switch_ports(xname):
    """Get a list of ports for a switch.

    Args:
        xname: component name of switch

    Returns:
        List of port names (xname augmented by port)
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
    if 'edge' not in portinfo['ports'] and 'fabric' not in portinfo['ports']:
        LOGGER.error('Key "edge" and "fabric" both missing in fabric port links.')
        return None

    # Create list of ports.
    ports = []
    if 'edge' in portinfo['ports']:
        for port in portinfo['ports']['edge']:
            if xname in port:
                ports.append(port)
    if 'fabric' in portinfo['ports']:
        for port in portinfo['ports']['fabric']:
            if xname in port:
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
    config_json = ('{"autoneg": ' + str(port_config['autoneg']).lower() +
                   ', "enable": ' + str(enable).lower() +
                   ', "flowControl": {"rx": ' + str(port_config['flowControl']['rx']).lower() +
                   ', "tx": ' + str(port_config['flowControl']['tx']).lower() +
                   '}, "speed": "' + str(port_config['speed']) + '"}')

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
