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
        '-n',
        '--no-headings',
        help='If applicable, do not print table headings.',
        action='store_true')


def add_status_subparser(subparsers):
    """Add the status subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    status_parser = subparsers.add_parser('status', help='Report node status')
    status_parser.add_argument('-r', '--reverse', help='Reverse order of nodes',
                               action='store_true')
    status_parser.add_argument('-s', '--sort-column', default='xname',
                               help='Sort by the selected column. The default is to sort by xname. '
                                    'May be specified by the (case insensitive) column, or by index '
                                    '(starting at 1). The column can be abbreviated if unambiguous.')


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

    return parser
