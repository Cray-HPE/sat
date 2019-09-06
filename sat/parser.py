"""
Functions to create the top-level ArgumentParser for the program.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from argparse import ArgumentParser

def add_cable_check_subparser(subparsers):
    """Add the cable check subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    cable_check_parser = subparsers.add_parser('cablecheck', help='Check cabling.')
    cable_check_parser.add_argument('p2p_file',
                                    help='Path of point-to-point data file (CSV format).')


def add_showrev_subparser(subparsers):
    """Add the showrev subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    showrev_parser = subparsers.add_parser('showrev', help='Show Shasta revision information')
    showrev_parser.add_argument(
        '--all',
        help='Print everything. Equivalent to specifying --system, --docker, and --packages.',
        action='store_true')
    showrev_parser.add_argument(
        '--system',
        help='Print general Shasta version information. This is the default.',
        action='store_true')
    showrev_parser.add_argument(
        '--docker',
        help='Print running docker image versions.',
        action='store_true')
    showrev_parser.add_argument(
        '--packages', help='Print installed rpm versions.', action='store_true')
    showrev_parser.add_argument(
        '-s',
        '--substr',
        help='Show version information for components whose names or IDs contain the substring',
        default='')
    showrev_parser.add_argument(
        '-p',
        '--plain',
        help='If applicable, do not pretty-print output.',
        action='store_true')


def create_parent_parser():
    """Creates the top-level parser for sat and adds subparsers for the commands.

    Returns:
        An argparse.ArgumentParser object with all arguments and subparsers
        added to it.
    """

    parser = ArgumentParser(description='SAT - The Shasta Admin Toolkit')
    subparsers = parser.add_subparsers(metavar='command', dest='command')

    # Add the subparsers for the individual subcommands here
    add_cable_check_subparser(subparsers)
    add_showrev_subparser(subparsers)

    return parser
