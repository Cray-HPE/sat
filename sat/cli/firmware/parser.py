"""
The parser for the firmware subcommand.

Copyright 2020 Cray Inc. All Rights Reserved.
"""

import sat.parsergroups


def add_firmware_subparser(subparsers):
    """Add the firmware subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()
    xname_options = sat.parsergroups.create_xname_options()

    firmware_parser = subparsers.add_parser(
        'firmware', help='Report firmware version.',
        description='Report firmware version of xname IDs. If no xnames '
                    'are specified, then all xnames will be targeted.',
        parents=[xname_options, format_options, filter_options])

    firmware_parser.add_argument(
        '--snapshots', dest='snapshots', metavar='SNAPSHOT', nargs='*',
        help='Describe firmware snapshots. Provide no arguments to this '
             'option to list available snapshots.')
