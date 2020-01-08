"""
Entry point for the status subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging
import re

from sat.apiclient import APIError, HSMClient
from sat.config import get_config_value
from sat.report import Report
from sat.session import SATSession
from sat.xname import XName


APIKEYS = ('ID', 'NID', 'State', 'Flag', 'Enabled', 'Arch', 'Role', 'NetType')
HEADERS = ('xname', 'NID', 'State', 'Flag', 'Enabled', 'Arch', 'Role', 'Net Type')

LOGGER = logging.getLogger(__name__)


class UsageError(Exception):
    pass


def make_raw_table(components):
    """Obtains node status from a list of components.

    Args:
        components (list): A list of dictionaries representing the components
            in the system along with information about their state.

    Returns:
        A list-of-lists table of strings, each row representing
        the status of a node.
    """
    return [[d[field_name] for field_name in APIKEYS] for d in components]


def do_status(args):
    """Displays node status.

    Results are sorted by the "sort_column" member of args, which defaults
    to xname. xnames are tokenized for the purposes of sorting, so that their
    numeric elements are sorted by their value, not lexicographically. Sort
    order is reversed if the "reverse" member of args is True.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        UsageError: if an argument is invalid
    """
    api_client = HSMClient(SATSession())
    try:
        response = api_client.get('State', 'Components', params={'type': 'Node'})
    except APIError as err:
        LOGGER.error('Request to HSM API failed: %s', err)
        raise SystemExit(1)

    try:
        response_json = response.json()
    except ValueError as err:
        LOGGER.error('Failed to parse JSON from component state response: %s', err)
        raise SystemExit(1)

    try:
        components = response_json['Components']
    except KeyError as err:
        LOGGER.error("Key '%s' not present in API response JSON.", err)
        raise SystemExit(1)

    raw_table = make_raw_table(components)
    report = Report(
        HEADERS, None,
        args.sort_by, args.reverse,
        get_config_value('format.no_headings'),
        get_config_value('format.no_borders'),
        filter_strs=args.filter_strs)

    report.add_rows(raw_table)

    if args.format == 'yaml':
        print(report.get_yaml())
    else:
        print(report)
