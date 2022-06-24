#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
The parser for the firmware subcommand.
"""

import sat.parsergroups


def add_firmware_subparser(subparsers):
    """Add the firmware subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()
    xname_options = sat.parsergroups.create_xname_options()

    firmware_parser = subparsers.add_parser(
        'firmware', help='Report firmware version.',
        description='Report firmware version of xname IDs. If no xnames '
                    'are specified, then all xnames will be targeted.',
        parents=[xname_options, format_options, filter_options])

    firmware_parser.add_argument(
        '--snapshots', dest='snapshots', metavar='SNAPSHOT', nargs='*',
        help='Describe firmware snapshots. Provide no arguments to this '
             'option to list available snapshots.')
