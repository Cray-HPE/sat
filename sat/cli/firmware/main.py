#
# MIT License
#
# (C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
Entry point for the firmware subcommand.
"""
import logging

from sat.apiclient import APIError
from sat.fwclient import FASClient
from sat.config import get_config_value
from sat.report import Report
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)


def get_known_snapshots(client):
    """Get a list of known snapshot names.

    Args:
        client (FASClient): The FASClient to use.

    Returns:
        A list of snapshot names.

    Raises:
        SystemExit: If no snapshots exist.
    """
    try:
        known_snaps = client.get_all_snapshot_names()
    except APIError as err:
        LOGGER.error('Failed to get snapshot names: %s', err)
        raise SystemExit(1)

    return known_snaps


def get_snapshot_firmware(client, snapshot_names, xnames):
    """Get snapshots using get_multiple_snapshot_devices and assemble table rows.

    Args:
        client (FASClient): The FASClient to use.
        snapshot_names (list): A list of snapshot names for which to report
            firmware versions.
        xnames (list): A list of xnames for which to get firmware, or None to
            get firmware for all xnames.

    Returns:
        A dictionary where the keys are snapshot names and the values
        are lists of table rows representing firmware versions for
        every device corresponding to the given xnames, or all xnames.

    Raises:
        SystemExit: if an error occurred getting snapshots.
    """
    try:
        snapshots = client.get_multiple_snapshot_devices(snapshot_names, xnames)
    except APIError as err:
        LOGGER.error('Failed to get snapshots: %s', err)
        raise SystemExit(1)
    return {
        name: client.make_fw_table(snapshot)
        for name, snapshot in snapshots.items()
    }


def get_current_firmware(client, xnames):
    """Get firmware using get_device_firmwares and assemble table rows.

    Args:
        client (FASClient): The FASClient to use.
        xnames (list): A list of xnames for which to get firmware, or None to get
            firmware for all xnames.

    Returns:
        A list of table rows representing firmware versions for every device
        corresponding to the given xnames, or all xnames if xnames is
        None.

    Raises:
        SystemExit: if getting firmware resulted in an APIError.
    """
    try:
        if xnames:
            device_firmwares = client.get_multiple_device_firmwares(xnames)
        else:
            device_firmwares = client.get_device_firmwares()
    except APIError as err:
        LOGGER.error('Failed to get firmware: %s', err)
        raise SystemExit(1)

    # Use a key of 'None' because this table will not have a title
    return {None: client.make_fw_table(device_firmwares)}


def print_reports_from_tables(fw_tables, sort_by, reverse, filter_strs, output_format):
    """Print a report given one or more firmware tables.

    Args:
        fw_tables (dict): A dictionary of firmware tables, where the keys are
            titles of the tables and the values are lists of lists, where each
            'inner' list is a row in the table.
        sort_by (str): The field name to sort by.
        reverse (bool): Whether output should be reversed.
        filter_strs (list): Specify options to filter output.
        output_format (str): Specify how to format output.
    """
    for title, table in sorted(fw_tables.items()):
        report = Report(
            FASClient.headers, title,
            sort_by, reverse,
            get_config_value('format.no_headings'),
            get_config_value('format.no_borders'),
            filter_strs=filter_strs
        )
        report.add_rows(table)

        if output_format == 'yaml':
            print(report.get_yaml())
        else:
            print(report)


def do_firmware(args):
    """Displays firmware versions.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """
    client = FASClient(SATSession())

    if args.snapshots is not None:
        # --snapshots without any arguments means list snapshot names, while
        # --snapshots with arguments means generate a report about given snapshots.
        # --x/--xname can be given with --snapshots to restrict the returned
        # information to firmware pertaining to the given xnames.
        # get_known_snapshots will exit with an error if no snapshots exist.
        known_snaps = get_known_snapshots(client)
        if args.snapshots:
            firmware_tables = get_snapshot_firmware(client, args.snapshots, args.xnames)
        else:
            if args.xnames:
                LOGGER.warning(
                    '--snapshots was given with no arguments. The value of '
                    '-x/--xname will be ignored.'
                )
            for snap_name in known_snaps:
                print(snap_name)
            return
    else:
        # If --snapshots is not given, generate a report based off temporary
        # snapshots. If xnames are specified, generate snapshots for each xname,
        # otherwise generate a snapshot for all xnames. This table will not
        # have a title as the titles would normally be snapshot names.
        firmware_tables = get_current_firmware(client, args.xnames)

    print_reports_from_tables(
        firmware_tables, args.sort_by, args.reverse, args.filter_strs, args.format
    )
