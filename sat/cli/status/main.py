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


def parse_filters(filters_in):
    """Parse filter specifications.

    A specification is a single term or many terms separated by commas.

    No validation is done. Passing a non-integer as a NID will fail to match,
    but no errors will occur.

    Args:
        filters_in: A dictionary with keys matching those of the API response,
            and values specifying the terms to match against.

    Returns:
        A corresponding dictionary with frozensets parsed from comma-separated
        values, and xnames tokenized. All strings and string xname tokens are
        lowercased.
    """

    filters_out = {}
    for k, v_in in filters_in.items():
        if v_in is not None:
            # filter out spurious empties, which may occur, for instance, with 'foo,'.split(',')
            # or even just ','.split(',')!
            v_out = filter(None, v_in.split(','))
            if k == 'ID':
                v_out = frozenset([XName(e) for e in v_out])
            else:
                # comparisons will be case-insensitive
                v_out = frozenset([e.lower() for e in v_out])

            if v_out:
                filters_out[k] = v_out

    return filters_out


def filter_match(comp, filters):
    """Determine whether the component passes the filters.

    Components are passed if they match any filter, like an OR.

    Each key in the filter dictionary is also present in the component. The
    value of this key in the filters is a set of strings whose elements may be
    exact case-insensitive matches of the value of the key in the component, or
    case-insensitive abbreviations.

    If there are no filters, all components pass.

    Args:
        comp (dict): Any dictionary whose keys are a superset of the keys in
            the filters. Typically, a component as returned by the HSM API's
            entry point /State/Components.
        filters (dict): Keys are a subset of those in the component. Values are
            sets of strings.

    Returns:
        True if the component matches, else False

    Raises:
        KeyError: if a key in the filters is not present in the component
    """

    if not filters:
        return True

    for key, matchers in filters.items():
        # the component's values need not be strings
        input_ = str(comp[key]).lower()

        if key == 'ID':
            input_ = XName(input_)
            input_ = input_.tokens

        for matcher in matchers:
            if key == 'ID':
                if matcher.tokens == input_[:len(matcher.tokens)]:
                    return True
            else:
                if matcher == input_[:len(matcher)]:
                    return True

    return False


def make_raw_table(components, filters):
    """Obtains node status, normalizes the field order, and sorts according to
    the provided index.

    Args:
        components (list): A list of dictionaries representing the components
            in the system along with information about their state.
        filters (dict): Keys are a subset of those returned from the API call,
            values are sequences of strings.

    Returns:
        A list-of-lists table of strings, each row representing
        the status of a node.

    Raises:
        KeyError: (via filter_match()) if a filter key does not exist
            in the API results
    """
    return [[d[field_name] for field_name in APIKEYS]
            for d in components if filter_match(d, filters)]


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

    raw_table = make_raw_table(
        components, parse_filters(dict(ID=args.xnames, NID=args.nids)))

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
