#
# MIT License
#
# (C) Copyright 2019-2022, 2024 Hewlett Packard Enterprise Development LP
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

from sat.cli.status.constants import COMPONENT_TYPES, DEFAULT_TYPE
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

    type_choices = ['all', *COMPONENT_TYPES]
    status_parser.add_argument(
        '--types', metavar='TYPE', dest='types', nargs='+',
        choices=type_choices, default=[DEFAULT_TYPE],
        help=f"Specify which components should be queried. "
        f"The default is \"{DEFAULT_TYPE}\". All types are: {', '.join(type_choices)}")

    status_parser.add_argument(
        '--all-fields', dest='status_module_names',
        action='store_const', const=['SLSStatusModule', 'HSMStatusModule', 'CFSStatusModule', 'BOSStatusModule'],
        help='Display all status fields. This is the default behavior when no other '
        '--*-fields options are specified.'
    )

    status_parser.add_argument(
        '--hsm-fields', dest='status_module_names',
        action='append_const', const='HSMStatusModule',
        help='Display all fields for HSM component states.'
    )

    status_parser.add_argument(
        '--sls-fields', dest='status_module_names',
        action='append_const', const='SLSStatusModule',
        help='Display all fields for SLS hostnames.'
    )

    status_parser.add_argument(
        '--cfs-fields', dest='status_module_names',
        action='append_const', const='CFSStatusModule',
        help='Display all fields for CFS configuration state.'
    )

    status_parser.add_argument(
        '--bos-fields', dest='status_module_names',
        action='append_const', const='BOSStatusModule',
        help='Display all fields for BOS boot state.'
    )

    status_parser.add_argument(
        '--bos-template',
        help='Only show nodes specified in the node list, roles, and groups in '
             'the boot sets contained in the given BOS session template.'
    )

    status_parser.add_argument(
        '--bos-version',
        choices=['v1', 'v2'],
        help='The version of the BOS API to use for BOS operations',
    )

    status_parser.add_argument(
        '--cfs-version',
        choices=['v2', 'v3'],
        help='The version of the CFS API to use for CFS operations',
    )
