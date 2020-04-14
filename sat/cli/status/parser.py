"""
The parser for the status subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""

import sat.parsergroups


def add_status_subparser(subparsers):
    """Add the status subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()

    types=[
        'all',
        'Chassis',
        'ChassisBMC',
        'ComputeModule',
        'HSNBoard',
        'Node',
        'NodeBMC',
        'NodeEnclosure',
        'RouterBMC',
        'RouterModule',
    ]

    status_parser = subparsers.add_parser(
        'status', help='Report node status.',
        description='Report node status.',
        parents=[format_options, filter_options])

    status_parser.add_argument(
        '--types', metavar='TYPE', dest='types', nargs='+',
        help="Specify which components should be queried.",
        choices=types, default=['Node'])
