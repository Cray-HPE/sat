"""
The parser for the hwmatch subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""
import sat.parsergroups


def add_hwmatch_subparser(subparsers):
    """Add the hwmatch subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()

    hwmatch_parser = subparsers.add_parser(
        'hwmatch', help='Report hardware match issues.',
        description='Report hardware match issues for processors and memory.',
        parents=[format_options, filter_options])

    hwmatch_parser.add_argument(
        '--level', '-l', action='append',
        help='Matching level:  slot, card, and/or node (default and a subset of slot).',
        dest='levels',
        choices=['slot', 'card', 'node']
    )
    hwmatch_parser.add_argument(
        '--show-matches', '-s', action='store_true',
        help='Show matches in addition to mismatches.'
    )
