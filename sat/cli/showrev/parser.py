"""
The parser for the showrev subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""

import sat.parsergroups


def add_showrev_subparser(subparsers):
    """Add the showrev subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()

    showrev_parser = subparsers.add_parser(
        'showrev',
        help='Show system revision information.',
        parents=[format_options, filter_options])

    showrev_parser.add_argument(
        '--all',
        help='Print everything. Equivalent to specifying --system, --docker, and --packages.',
        action='store_true')
    showrev_parser.add_argument(
        '--system',
        help='Print general system version information. This is the default.',
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
        help='Show version information for components whose names or IDs contain the substring.',
        default='')
    showrev_parser.add_argument(
        '--sitefile',
        help='Specify custom site information file printed by --system.',
        default='')
