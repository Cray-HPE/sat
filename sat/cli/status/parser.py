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

    status_parser = subparsers.add_parser(
        'status', help='Report node status.',
        description='Report node status.',
        parents=[format_options, filter_options])

    status_parser.add_argument(
        '-x', '--xnames',
        help='Filter list of nodes to show only those with xnames specified '
             'with this argument. A single xname may be given, or a '
             'comma-separated list (no spaces) of multiple xnames.')

    status_parser.add_argument(
        '-n', '--nids',
        help='Filter list of nodes to show only those with NIDs specified '
             'with this argument. A single NID may be given, or a '
             'comma-separated list (no spaces) of multiple NIDs.')
