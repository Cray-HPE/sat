"""
Functions to create argument groups which are used by multiple subcommands.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from argparse import ArgumentParser


def create_format_options():
    parser = ArgumentParser(add_help=False)

    group = parser.add_argument_group(
        'format options', 'Options to modify output formatting.')

    group.add_argument(
        '--format',
        help="Display information in the given format. Defaults to 'pretty'.",
        choices=['pretty', 'yaml'],
        default='pretty')

    group.add_argument(
        '--no-borders',
        help='Omit borders from tables.',
        default=None, action='store_true')

    group.add_argument(
        '--no-headings',
        help='Omit headings from tables.',
        default=None, action='store_true')

    group.add_argument(
        '--reverse',
        help='Sort the output in reverse order. Only applies for "pretty".',
        default=False, action='store_true')

    group.add_argument(
        '--sort-by', metavar='FIELD', default=0,
        help=('Select which column to sort by. Can accept a column name '
              'or a 0-based index. Only applies for "pretty"'))

    return parser
