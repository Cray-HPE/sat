"""
The parser for the sensors subcommand.

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

from sat.cli.sensors.capture import CAPTURE_NAME
from sat.constants import BMC_TYPES


def add_sensors_subparser(subparsers):
    """Add the sensors subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    xname_options = sat.parsergroups.create_xname_options()
    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()
    redfish_options = sat.parsergroups.create_redfish_options()

    sensors_parser = subparsers.add_parser(
        'sensors', help='Obtain sensor readings.',
        description='Obtain sensor readings from BMCs (any type).',
        parents=[xname_options, format_options, filter_options, redfish_options]
    )

    sensors_parser.add_argument('-t', '--types',
                                nargs='*',
                                choices=BMC_TYPES,
                                default=BMC_TYPES,
                                help='Limit the types of BMCs queried to the types listed. '
                                     'The default is to query all types.')

    if CAPTURE_NAME is not None:
        capture_group = sensors_parser.add_argument_group('capture')

        capture_group.add_argument(
            '--capture-comm', action='store_true',
            help='Capture successful network requests and responses.')

        capture_group.add_argument(
            '--capture-logs', action='store_true',
            help='Capture log messages.')

        capture_group.add_argument(
            '--capture-data', action='store_true',
            help='Capture data.')

        capture_group.add_argument(
            '--capture-dir',
            help='Destination directory. Defaults to the current directory.'
        )

        capture_group.add_argument(
            '--no-zip', action='store_true',
            help='Do not bundle the capture into a "tgz" file; retain temporary directory instead.'
        )
