"""
The parser for the hwhist subcommand.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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


def add_hwhist_subparser(subparsers):
    """Add the hwhist subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    xname_options = sat.parsergroups.create_xname_options()
    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()

    hwhist_parser = subparsers.add_parser(
        'hwhist',
        help='Report hardware component history.',
        description='Report hardware component history.',
        parents=[xname_options, format_options, filter_options]
    )

    hwhist_parser.add_argument(
        '--by-fru',
        dest='by_fru',
        action='store_true',
        help='Display hardware component history by FRU.'
    )
    hwhist_parser.add_argument(
        '--fruid',
        '--fruids',
        metavar='FRUID',
        dest='fruids',
        type=lambda x: x.split(','),
        help='A comma-separated list of FRUIDs to include in the hardware component history report.'
    )
