"""
The parser for the sensors subcommand.

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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


BATCHSIZE = 16
TIMEOUT = 60
TYPES = [
    'ChassisBMC',
    'NodeBMC',
    'RouterBMC'
]
TOPICS = [
    'cray-telemetry-temperature',
    'cray-telemetry-voltage',
    'cray-telemetry-power',
    'cray-telemetry-energy',
    'cray-telemetry-fan',
    'cray-telemetry-pressure'
]


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

    sensors_parser = subparsers.add_parser(
        'sensors', help='Obtain sensor readings.',
        description='Obtain sensor readings from BMCs (any type).',
        parents=[xname_options, format_options, filter_options]
    )

    sensors_parser.add_argument('-t', '--types',
                                metavar='TYPE',
                                dest='types',
                                nargs='+',
                                choices=TYPES,
                                default=TYPES,
                                help=f'Limit the types of BMCs queried to the types listed. '
                                     f'The default is to query all types: {TYPES}.')

    sensors_parser.add_argument('--topics',
                                metavar='TOPIC',
                                dest='topics',
                                nargs='+',
                                choices=TOPICS,
                                default=TOPICS,
                                help=f'Limit the telemetry topics queried to the topics listed. '
                                     f'The default is to query all topics: {TOPICS}.')

    sensors_parser.add_argument('-b', '--batch-size',
                                dest='batchsize',
                                default=BATCHSIZE,
                                help=f'Number of metrics in each message. '
                                     f'Defaults to {BATCHSIZE}.')

    sensors_parser.add_argument('--timeout',
                                default=TIMEOUT,
                                help=f'Total time, in seconds, for receiving data from telemetry topics. '
                                     f'Defaults to {TIMEOUT}.')

    sensors_parser.add_argument('-r', '--recursive',
                                action='store_true',
                                help='Include all BMCs for Chassis xnames specified by xXcC.')
