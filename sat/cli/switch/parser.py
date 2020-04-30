"""
The parser for the switch subcommand.
Copyright 2020 Cray Inc. All Rights Reserved.
"""


def add_switch_subparser(subparsers):
    """Add the switch subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    switch_parser = subparsers.add_parser(
        'switch', help='Switch administration actions.',
        description='Prepare switch for replacement, and bring switch into service.')
    switch_parser.add_argument('xname', help='The xname of the switch.')

    switch_parser.add_argument(
        '--save-portset', '-s', action='store_true',
        help='Save switch portset JSON as <xname>-ports.json file in current directory.')

    switch_parser.add_argument(
        '--finish', action='store_true',
        help='Finish switch replacement')

    switch_parser.add_argument(
        '--disruptive', action='store_true',
        help='Perform action to disable/enable the switch rather than a trial run.')

