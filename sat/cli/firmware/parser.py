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

    firmware_parser = subparsers.add_parser(
        'firmware', help='Report firmware version.',
        description='Report firmware version of system components (all by default).',
        parents=[format_options, filter_options])

    firmware_parser.add_argument(
        '-x', '--xname', '--xnames', action='append',
        help='List of xnames from which to get firmware version. '
             'A single xname may be given, or a comma separated list of xnames. '
             'Option may be specified multiple times. '
             'All is the default if no xnames are specified.')
