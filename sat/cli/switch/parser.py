"""
The parser for the switch subcommand.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
        '--action', '-a', choices=['disable', 'enable'],
        help='Perform action to disable/enable the switch.')

    switch_parser.add_argument(
        '--save-portset', '-s', action='store_true',
        help='Save switch portset JSON as <xname>-ports.json file in current directory.')

    switch_parser.add_argument(
        '--disruptive', action='store_true',
        help='Do not ask whether to continue.')

    switch_parser.add_argument(
        '--over-write', action='store_true',
        help='Delete and recreate any existing SAT port sets for switch.')

    switch_parser.add_argument(
        '--dry-run', action='store_true',
        help='Perform a dry run without enable/disable of the switch.')

