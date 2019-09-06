"""
Functions to create the top-level ArgumentParser for the program.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from argparse import ArgumentParser


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
        help='Print general Shasta version information. This is the default',
        action='store_true')
    showrev_parser.add_argument('--docker', help='Print running docker image versions.',
                                action='store_true')
    showrev_parser.add_argument('--packages', help='Print installed rpm versions.',
                                action='store_true')
    showrev_parser.add_argument('-e', '--substr', help='Print lines that contain the substring',
                                default='')


def create_parent_parser():
    """Creates the top-level parser for sat and adds subparsers for the commands.

    Returns:
        An argparse.ArgumentParser object with all arguments and subparsers
        added to it.
    """

    parser = ArgumentParser(description='SAT - The Shasta Admin Toolkit')
    subparsers = parser.add_subparsers(metavar='command', dest='command')

    # Add the subparsers for the individual subcommands here
    add_showrev_subparser(subparsers)

    return parser
