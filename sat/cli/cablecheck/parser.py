"""
The parser for the cablecheck subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""


def add_cable_check_subparser(subparsers):
    """Add the cable check subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    cable_check_parser = subparsers.add_parser(
        'cablecheck', help='Check cabling.',
        description='Check that cabling is correct and output any problems found.')
    cable_check_parser.add_argument('p2p_file',
                                    help='Path of point-to-point data file (CSV format).')

    cable_check_parser.add_argument('-l',
                                    '--link-levels',
                                    nargs='+', type=int,
                                    help='Link levels to check; for L1 and L2, '
                                         'use -l 1 2. Defaults to all.')
    cable_check_parser.add_argument('-n',
                                    '--nic-prefix',
                                    help='HSN NIC prefix. Defaults to "hsn".')
    cable_check_parser.add_argument('-q',
                                    '--quiet',
                                    help='Quiet output; only total faults found.',
                                    action='store_true')
