"""
Entry point for the status subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import re
import textwrap

import requests
from prettytable import PrettyTable

APIHOST = 'api-gw-service-nmn.local/'
APIHSM = 'apis/smd/hsm/v1/'

# for local development ssh port-forwarding can be used, i.e.
# ssh root@spottedcow-sms1 -L *:443:api-gw-service-nmn.local:443
# APIHOST = 'localhost/'


APIKEYS = ('ID', 'NID', 'State', 'Flag', 'Enabled', 'Arch', 'Role', 'NetType')
HEADERS = ('XName', 'NID', 'State', 'Flag', 'Enabled', 'Arch', 'Role', 'Net Type')


class UsageError(Exception):
    pass


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
        xname: the xname to tokenize

    Returns:
        tokenized xname

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
        s (string): the value passed on the command line
        headers (sequence of strings): the column headers to match against

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


def make_raw_table(sort_index, reverse):
    """Obtains node status, normalizes the field order, and sorts according to
    the provided index.

    Args:
        sort_index (int): a 0-based index into the rows that determines sort
        order. If 0, interpret as an xname, and tokenize to sort integer parts
        correctly.

        reverse (bool): If true, reverse the sort order

    Returns:
        A list-of-lists table of strings, each row representing the status of a
        node.

    Raises:
        Exceptions raised by requests.get()
    """

    rsp = api_query('State', 'Components', type='Node')

    comps_as_dict = rsp.json()['Components']
    comps_as_list = [[d[field_name] for field_name in APIKEYS] for d in comps_as_dict]

    if sort_index == 0:
        comps_as_list.sort(key=lambda x: tokenize_xname(x[0]), reverse=reverse)
    else:
        comps_as_list.sort(key=lambda x: x[sort_index], reverse=reverse)

    return comps_as_list


def do_status(args):
    """Displays node status.

    Results are sorted by the "sort_column" member of args, which defaults
    to xname. Xnames are tokenized for the purposes of sorting, so that their
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
        print('\n'.join(textwrap.wrap(e.args[0])))
        raise SystemExit(1)

    raw_table = make_raw_table(sort_index, args.reverse)

    table_out = PrettyTable()
    table_out.field_names = HEADERS

    for row in raw_table:
        table_out.add_row(row)

    print(table_out)
