"""
The main entry point for the hwinv subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging
from prettytable import PrettyTable
import sys

from sat.apiclient import APIError, HSMClient

LOGGER = logging.getLogger(__name__)


def do_hwinv(args):
    """Execute the hwinv command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    LOGGER.debug('do_hwinv received the following args: %s', args)

    client = HSMClient()

    try:
        response = client.get('Inventory', 'Hardware')
    except APIError as err:
        LOGGER.error('Failed to get hardware inventory from HSM: %s', err)
        sys.exit(1)

    try:
        response_json = response.json()
    except ValueError as err:
        LOGGER.error('Failed to parse JSON from hardware inventory response: %s', err)
        sys.exit(1)

    # TODO: Implement actual options for display.
    # The code below is just a placeholder for the real functionality that needs
    # to be implemented for hwinv output. It does demonstrate the ability to
    # extract and display information from HSM's hardware inventory database.
    nodes = [component for component in response_json if component['Type'] == 'Node']

    LOGGER.warning('Parsing of hwinv options not implemented. Showing table of nodes.')

    pt = PrettyTable()
    pt.field_names = ['xname', 'serial number']
    for node in nodes:
        pt.add_row([node['ID'], node['PopulatedFRU']['NodeFRUInfo']['SerialNumber']])

    print(pt)
