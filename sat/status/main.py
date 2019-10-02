"""
Entry point for the status subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import re
import logging

import requests
from prettytable import PrettyTable

APIHOST = 'api-gw-service-nmn.local/'
APIHSM = 'apis/smd/hsm/v1/'

# for local development ssh port-forwarding can be used, i.e.
# ssh root@spottedcow-sms1 -L *:443:api-gw-service-nmn.local:443
# APIHOST = 'localhost/'


APIKEYS = ('ID', 'NID', 'State', 'Flag', 'Enabled', 'Arch', 'Role', 'NetType')
HEADERS = ('xname', 'NID', 'State', 'Flag', 'Enabled', 'Arch', 'Role', 'Net Type')


class UsageError(Exception):
    pass


LOGGER = logging.getLogger(__name__)


def api_query(*args, **kwargs):
    """Call the Shasta HSM API

        Args:
            Positional arguments define the path to the API call, keyword
            parameters are passed as the parameters to the call.

        Returns:
            A Response object

        Raises:
            Exceptions raised by requests.get()
    """

    qry = 'https://' + APIHOST + APIHSM + '/'.join(args)
    return requests.get(qry, params=kwargs)


def tokenize_xname(xname):
    """Tokenize the xname to facilitate sorting.

    Numeric elements are converted to integers so that they compare correctly
    regardless of digit count.

    Args:
        xname: The xname to tokenize

    Returns:
        Tokenized xname

        A sequence with the alternating string and integer elements of the
        provided xname. For example, "x3000c0s28b0n0" would tokenize to
        ('x', 3000, 'c', 0, 's', 28, 'b', 0, 'n', 0).
    """

    # the last element will always be an empty string, since the input string
    # ends with a match.
    toks = re.split(r'(\d+)', xname)[:-1]

    for i, tok in enumerate(toks):
        if i % 2 == 1:
            toks[i] = int(toks[i])
        else:
            toks[i] = toks[i].lower()

    return tuple(toks)


def parse_sortcol(s, column_hdrs):
    """Parse and validate the "sort-column" argument.

    If an integer, interpret it as a 1-based column index

    If not, iterate over the column headers, and compare case-insensitively
    with the leading part of the header. NOTE: if the string passed would
    match more than one column, the first (leftmost) one is selected. If
    a column header matches, but there are remaining characters in the
    argument, the argument is considered invalid.

    If passed an empty string, use the default (0)

    Args:
        s (string): The value passed on the command line
        headers (sequence of strings): The column headers to match against

    Returns:
        The (0-based) index of the column to sort by

    Raises:
        UsageError if no match found
    """

    if not s:
        # empty string, use default
        return 0
    else:
        for i, hdr in enumerate(column_hdrs):
            if hdr.lower().startswith(s.lower()):
                return i

        try:
            i = int(s)
        except ValueError:
            pass
        else:
            if 1 <= i <= len(column_hdrs):
                return i-1

    raise UsageError('Not a valid value "{}" for --sort-column. Valid choices are {}; and a '
                     'number from 1 to {:d}.'.format(s, ', '.join(column_hdrs), len(column_hdrs)))


def parse_filters(filtersIn):
    """Parse filter specifications.

    A specification is a single term or many terms separated by commas.

    No validation is done. Passing a non-integer as a NID will fail to match,
    but no errors will occur.

    Args:
        filtersIn: A dictionary with keys matching those of the API response,
        and values specifying the terms to match against.

    Returns:
        A corresponding dictionary with frozensets parsed from comma-separated
        values, and xnames tokenized. All strings and string xname tokens are
        lowercased.
    """

    filtersOut = {}
    for k, vIn in filtersIn.items():
        if vIn is not None:
            # filter out spurious empties, which may occur, for instance, with 'foo,'.split(',')
            # or even just ','.split(',')!
            vOut = filter(None, vIn.split(','))
            if k == 'ID':
                vOut = frozenset([tokenize_xname(e) for e in vOut])
            else:
                # comparisons will be case-insensitive
                vOut = frozenset([e.lower() for e in vOut])

            if vOut:
                filtersOut[k] = vOut

    return filtersOut


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
        the filters. Typically, a component as returned by the HSM API's entry
        point /State/Components.

        filters (dict): Keys are a subset of those in the component. Values are
        sets of strings.

    Returns:
        True if the component matches, else False

    Raises:
        KeyError if a key in the filters is not present in the component
    """

    if not filters:
        return True

    for key, matchers in filters.items():
        # the component's values need not be strings
        match = str(comp[key]).lower()

        if key == 'ID':
            match = tokenize_xname(match)

        for matcher in matchers:
            if matcher == match[:len(matcher)]:
                return True

    return False


def make_raw_table(sort_index, reverse, filters):
    """Obtains node status, normalizes the field order, and sorts according to
    the provided index.

    Args:
        sort_index (int): A 0-based index into the rows that determines sort
            order. If 0, interpret as an xname, and tokenize to sort integer
            parts correctly.
        reverse (bool): If true, reverse the sort order
        filters (dict): Keys are a subset of those returned from the API call,
            values are sequences of strings.

    Returns:
        A list-of-lists table of strings, each row representing the status of a
        node.

    Raises:
        Exceptions raised by requests.get()
        KeyError (via filter_match()) if a filter key does not exist in the API results
    """

    rsp = api_query('State', 'Components', type='Node')
    rsp_json = rsp.json()

    if 'Components' not in rsp_json:
        LOGGER.error('Invalid API response. "%s"', rsp.text)
        raise SystemExit(1)

    comps_as_dict = rsp_json['Components']
    comps_as_list = [[d[field_name] for field_name in APIKEYS] for d in comps_as_dict
                     if filter_match(d, filters)]

    if sort_index == 0:
        comps_as_list.sort(key=lambda x: tokenize_xname(x[0]), reverse=reverse)
    else:
        comps_as_list.sort(key=lambda x: x[sort_index], reverse=reverse)

    return comps_as_list


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
        UsageError if an argument is invalid
        Exceptions raised by requests.get()
    """

    # Aborts the program if argument is invalid
    try:
        sort_index = parse_sortcol(args.sort_column, HEADERS)
    except UsageError as e:
        LOGGER.error(e.args[0])
        raise SystemExit(1)

    raw_table = make_raw_table(sort_index, args.reverse,
                               parse_filters(dict(ID=args.xnames, NID=args.nids)))

    table_out = PrettyTable()
    table_out.field_names = HEADERS

    for row in raw_table:
        table_out.add_row(row)

    print(table_out)
