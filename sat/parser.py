"""
Functions to create the top-level ArgumentParser for the program.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from argparse import ArgumentParser

from sat.cablecheck.parser import add_cable_check_subparser
from sat.hwinv.parser import add_hwinv_subparser
from sat.showrev.parser import add_showrev_subparser
from sat.status.parser import add_status_subparser


def create_parent_parser():
    """Creates the top-level parser for sat and adds subparsers for the commands.

    Returns:
        An argparse.ArgumentParser object with all arguments and subparsers
        added to it.
    """

    parser = ArgumentParser(description='SAT - The Shasta Admin Toolkit')

    parser.add_argument(
        '--logfile',
        help='Set location of logs for this run. Overrides value set in config file.')

    parser.add_argument(
        '--loglevel',
        help='Set minimum log severity to report for this run. This level applies to '
             'messages logged to stderr and to the log file. Overrides values set in '
             'config file.',
        choices=['debug', 'info', 'warning', 'error', 'critical'])

    subparsers = parser.add_subparsers(metavar='command', dest='command')

    # Add the subparsers for the individual subcommands here
    add_cable_check_subparser(subparsers)
    add_showrev_subparser(subparsers)
    add_status_subparser(subparsers)
    add_hwinv_subparser(subparsers)

    return parser
