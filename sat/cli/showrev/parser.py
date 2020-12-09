"""
The parser for the showrev subcommand.
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


def add_showrev_subparser(subparsers):
    """Add the showrev subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()

    showrev_parser = subparsers.add_parser(
        'showrev', help='Show system revision information.',
        description='Show system revision information.',
        parents=[format_options, filter_options])

    showrev_parser.add_argument(
        '--all',
        help='Display everything. Equivalent to specifying --system, --products, '
             '--docker, --packages, and --release-files.',
        action='store_true')
    showrev_parser.add_argument(
        '--system',
        help='Display general system version information. This is enabled when '
             'no other options are specified.',
        action='store_true')
    showrev_parser.add_argument(
        '--products',
        help='Display version information about the installed products. '
             'This is enabled when no other options are specified.',
        action='store_true')
    showrev_parser.add_argument(
        '--release-files',
        help='Display version information about locally installed release files.',
        action='store_true')
    showrev_parser.add_argument(
        '--docker',
        help='Display running docker image versions.',
        action='store_true')
    showrev_parser.add_argument(
        '--packages', help='Display installed rpm versions.', action='store_true')
    showrev_parser.add_argument(
        '--sitefile',
        help='Specify custom site information file printed by --system.',
        default='')
