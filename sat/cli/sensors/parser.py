"""
The parser for the sensors subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import sat.parsergroups

from sat.cli.sensors.capture import CAPTURE_NAME


def add_sensors_subparser(subparsers):
    """Add the sensors subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()
    redfish_options = sat.parsergroups.create_redfish_options()

    sensors_parser = subparsers.add_parser(
        'sensors', help='Obtain sensor readings.',
        description='Obtain sensor readings.',
        parents=[format_options, filter_options, redfish_options]
    )

    sensors_parser.add_argument(
        '-x', '--xnames', '--xname',
        help='Xname/hostname or IP address of BMC/controller to query, or a '
             'comma-separated list of names and/or addresses.', required=True)

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
