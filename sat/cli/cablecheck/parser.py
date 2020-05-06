"""
The parser for the cablecheck subcommand.
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
