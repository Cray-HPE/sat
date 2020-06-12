"""
Entry point for the bootsys subcommand.

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
import logging
import sys

from sat.cli.bootsys.service_activity import do_service_activity_check


LOGGER = logging.getLogger(__name__)


def do_boot(args):
    """Perform a shutdown operation on the system.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    LOGGER.error("Boot not implemented.")
    sys.exit(1)


def do_shutdown(args):
    """Perform a shutdown operation on the system.

    Currently this only does the service activity check to verify that it is
    okay to begin shutting down.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    do_service_activity_check(args)
    print('It is safe to continue with the shutdown procedure. Please proceed.')


def do_bootsys(args):
    """Perform a boot or shutdown operation on the system.

    A full system shutdown includes the following steps at a high level:

        * Checking for service idleness
        * Shutting down all computes and UANs using BOS
        * Shutting down management software on NCNs
        * Shutting down and powering off all NCNs

    A full system boot includes the following steps at a high level:

        * Powering on and booting all NCNs
        * Starting all management software on NCNs
        * Verifying health of management software services
        * Booting the computes and UANs using BOS

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    if args.action == 'boot':
        do_boot(args)
    elif args.action == 'shutdown':
        do_shutdown(args)
    else:
        # This should not happen based on the way args are parsed
        LOGGER.error('Invalid action received by bootsys command: %s',
                     args.action)
        sys.exit(1)
