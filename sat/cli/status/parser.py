#
# MIT License
#
# (C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP
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
The parser for the status subcommand.
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

    types = [
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

    default_type = 'Node'

    status_parser = subparsers.add_parser(
        'status', help='Report node status.',
        description='Report node status.',
        parents=[format_options, filter_options])

    status_parser.add_argument(
        '--types', metavar='TYPE', dest='types', nargs='+',
        choices=types, default=[default_type],
        help=f"Specify which components should be queried. "
        f"The default is \"{default_type}\". All types are: {', '.join(types)}")
