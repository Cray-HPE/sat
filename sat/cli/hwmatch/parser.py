"""
The parser for the hwmatch subcommand.
(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
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
