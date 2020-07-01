"""
Entry point for the firmware subcommand.

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
import logging
import sys

from sat.apiclient import APIError
from sat.fwclient import create_firmware_client
from sat.config import get_config_value
from sat.report import Report
from sat.session import SATSession


HEADERS = ('xname', 'ID', 'version')

LOGGER = logging.getLogger(__name__)


def do_firmware(args):
    """Displays firmware versions.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """

    try:
        client = create_firmware_client(SATSession())
    except APIError as err:
        LOGGER.error(err)
        sys.exit(1)

    # title is key to tables.
    fw_tables = {}

    if args.snapshots is not None:

        try:
            known_snaps = client.get_all_snapshot_names()
        except APIError as err:
            LOGGER.error('Getting available snapshot names: {}'.format(err))
            sys.exit(1)
        if not args.snapshots:
            for name in known_snaps:
                print(name)
            return
        else:

            # snapshot names were specified by the user but none exist.
            if not known_snaps:
                LOGGER.error('No existing snapshots.')
                sys.exit(1)

            try:
                snapshots = client.get_snapshots(args.snapshots)
            except APIError as err:
                LOGGER.error('Getting snapshot descriptions: {}'.format(err))
                sys.exit(1)

            for name, snapshot in snapshots.items():
                fw_tables[name] = client.make_fw_table(snapshot)

    elif args.xnames:

        # This report won't have a title.
        fw_tables[None] = []
        for xname in args.xnames:
            try:
                fw_devs = client.get_device_firmwares(xname)
            except APIError as err:
                LOGGER.error('Error with request for xname %s: %s', xname, err)
                sys.exit(1)

            fw_tables[None] += client.make_fw_table(fw_devs)
    else:
        try:
            fw_devs = client.get_device_firmwares()
        except APIError as err:
            LOGGER.error(err)
            raise SystemExit(1)

        # This report won't have a title.
        fw_tables[None] = client.make_fw_table(fw_devs)

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
