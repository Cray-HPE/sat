"""
The main entry point for the hwinv subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging
import sys

from sat.apiclient import APIError, HSMClient
from sat.hwinv.system import System
from sat.session import SATSession

LOGGER = logging.getLogger(__name__)


def set_default_args(args):
    """Defaults args to '--list-all' and '--summarize-all' if none specified.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None. Modifies `args` given as input.
    """
    # Extract all the arguments that start with the word 'list'
    list_args = {arg: val for arg, val in vars(args).items()
                 if arg.startswith('list')}
    no_list_args = not any(val for val in list_args.values())

    # Extract all the arguments that start with the word 'summarize'
    summarize_args = {arg: val for arg, val in vars(args).items()
                      if arg.startswith('summarize')}
    no_summarize_args = not any(val for val in summarize_args.values())

    # The default behavior of hwinv is to summarize and list all components
    if no_list_args and no_summarize_args:
        LOGGER.debug("No '--summarize' or '--list' options specified. Defaulting to "
                     "'--summarize-all' and '--list-all'.")
        args.list_all = True
        args.summarize_all = True


def do_hwinv(args):
    """Executes the hwinv command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    LOGGER.debug('do_hwinv received the following args: %s', args)
    set_default_args(args)

    client = HSMClient(SATSession())

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

    full_system = System(response_json, args)
    full_system.parse_all()
    print(full_system.get_all_output())
