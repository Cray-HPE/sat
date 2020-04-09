"""
Entry point for the firmware subcommand.

Copyright 2020 Cray Inc. All Rights Reserved.
"""
import logging
import sys

from sat.apiclient import APIError, FirmwareClient
from sat.cli.firmware.snapshots import describe_snapshots, get_all_snapshot_names
from sat.config import get_config_value
from sat.report import Report
from sat.session import SATSession
from sat.xname import XName


HEADERS = ('xname', 'ID', 'version')

LOGGER = logging.getLogger(__name__)


def make_fw_table(fw_devs):
    """Obtains firmware version.

    Args:
        fw_devs (list): A list of dictionaries with xnames and their
            firmware elements and versions.

            fw_devs = [
                {
                    xname: xname,
                    'targets': [{'version': vers, 'id': id}, ...]
                },
                ...
            ]

    Returns:
        A list-of-lists table of strings, each row representing
        the firmware version for an xname and ID.

    """
    fw_table = []
    for fw_dev in fw_devs:
        if 'xname' not in fw_dev:
            LOGGER.error('Missing xname key.')
            continue
        xname = fw_dev['xname']
        if 'targets' in fw_dev and fw_dev['targets'] is not None:
            targets = fw_dev['targets']
            for target in targets:
                if 'error' in target:
                    LOGGER.error('Error getting firmware for %s ID %s: %s', xname,
                                 target.get('id', 'MISSING'), target['error'])
                    # Fall through to show version only if ID and version values exist.
                    if 'id' not in target or 'version' not in target:
                        continue
                # Use XName class so xnames sort properly.
                fw_table.append([XName(xname), target.get('id', 'MISSING'),
                                 target.get('version', 'MISSING')])
        elif 'error' in fw_dev:
            LOGGER.error('Error getting firmware for %s: %s', xname, fw_dev['error'])
        else:
            # It is unclear whether this can actually occur.
            LOGGER.warning('No firmware found for: %s', xname)
    return fw_table


def do_firmware(args):
    """Displays firmware versions.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """

    api_client = FirmwareClient(SATSession())

    # title is key to tables.
    fw_tables = {}

    if args.snapshots is not None:

        try:
            known_snaps = get_all_snapshot_names()
        except APIError as err:
            LOGGER.error('Getting available snapshot names: {}'.format(err))
            sys.exit(1)
        if not args.snapshots:
            for name in known_snaps:
                print(name)
            return
        else:
            if not known_snaps:
                LOGGER.error('No existing snapshots.')
                sys.exit(1)

            try:
                descriptions = describe_snapshots(args.snapshots)
            except APIError as err:
                LOGGER.error('Getting snapshot descriptions: {}'.format(err))
                sys.exit(1)

            for name, snapshot in descriptions.items():
                fw_tables[name] = make_fw_table(snapshot)

    elif args.xnames:

        # This report won't have a title.
        fw_tables[None] = []
        for xname in args.xnames:
            try:
                response = api_client.get('version', xname)
            except APIError as err:
                LOGGER.error('Request to Firmware API failed for %s: %s', xname, err)
                continue
            try:
                response_json = response.json()
            except ValueError as err:
                LOGGER.error('Failed to obtain JSON from response for %s: %s', xname, err)
                continue
            try:
                fw_devs = response_json['devices']
            except KeyError as err:
                LOGGER.error("Failed to obtain firmware devices for %s: %s", xname, err)
                continue
            fw_tables[None] += make_fw_table(fw_devs)
    else:
        try:
            response = api_client.get('version', 'all')
        except APIError as err:
            LOGGER.error('Request to Firmware API failed: %s', err)
            raise SystemExit(1)
        try:
            response_json = response.json()
        except ValueError as err:
            LOGGER.error('Failed to obtain JSON from firmware version response: %s', err)
            raise SystemExit(1)
        try:
            fw_devs = response_json['devices']
        except KeyError as err:
            LOGGER.error("Failed to obtain firmware devices: %s", err)
            raise SystemExit(1)

        # This report won't have a title.
        fw_tables[None] = make_fw_table(fw_devs)

    for title, table in sorted(fw_tables.items()):
        report = Report(
            HEADERS, title,
            args.sort_by, args.reverse,
            get_config_value('format.no_headings'),
            get_config_value('format.no_borders'),
            filter_strs=args.filter_strs)

        report.add_rows(table)

        if args.format == 'yaml':
            print(report.get_yaml())
        else:
            print(report)
