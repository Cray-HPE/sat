"""
The main entry point for the hwinv subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging
import sys

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
    LOGGER.error('hwinv is not yet implemented')
    sys.exit(1)
