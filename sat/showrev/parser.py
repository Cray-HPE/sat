"""
The parser for the showrev subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""


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
