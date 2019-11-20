"""
Functions to create the top-level ArgumentParser for the program.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from argparse import ArgumentParser

import sat.cli


def create_parent_parser():
    """Creates the top-level parser for sat and adds subparsers for the commands.

    Returns:
        An argparse.ArgumentParser object with all arguments and subparsers
        added to it.
    """

    parser = ArgumentParser(description='SAT - The System Admin Toolkit')

    parser.add_argument(
        '-u', '--username',
        help='Username to use when loading or fetching authentication '
             'tokens. Overrides value set in config file.')

    parser.add_argument(
        '--token-file',
        help='Token file to use for authentication. Overrides value derived '
             'from other settings, or set in config file.')

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
    sat.cli.build_out_subparsers(subparsers)

    return parser
