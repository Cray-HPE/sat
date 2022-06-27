#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Entry point for the xname2nid subcommand.
"""
from collections import OrderedDict
import logging

from sat.apiclient import APIError, HSMClient
from sat.constants import MISSING_VALUE
from sat.session import SATSession
from sat.xname import XName

LOGGER = logging.getLogger(__name__)
NUM_NID_DIGITS = 6

ERR_MISSING_NAMES = 1
ERR_HSM_API_FAILED = 2


def group(ints):
    """Group a list of integers as ranges that are yielded as tuples.

    Args:
        ints ([int]): A list of integers that may be unsorted.
            Caller should sort and delete duplicates if required.

    Yields:
        A tuple for each range representing a group.
    """

    first = ints[0]
    last = first
    for num in ints[1:]:
        if num - 1 == last:
            # Part of the group, bump the end
            last = num
        else:
            # Not part of the group
            # Yield current group and start a new group
            yield first, last
            first = num
            last = first

    # Yield the last group
    yield first, last


def init_xname_results(xname_args):
    """Initialize an ordered dictionary that will contain xnames and nid results.

    Args:
        xname_args ([str]): A list of xname arguments as input by the user.

    Returns:
        xname_results (OrderedDict): A dictionary with xnames as keys.
    """

    xname_results = OrderedDict()
    for arg in xname_args:
        for xname in [x for x in (x.strip() for x in arg.split(',')) if x]:
            xname_results[xname] = {
                'xname': XName(xname),
                'type': XName(xname).get_type(),
                'found': False,
                'missing_nids': False,
                'nodes': []
            }

    return xname_results


def process_node_component(node_xname, node_component, xname_results):
    """Check if a node xname matches one or more xname arguments and add to the xname_results.

    Args:
        node_xname (str): A component xname for a node being processed.
        node_component (Dict): A dictionary with node component data from HSM for node_xname.
        xname_results (OrderedDict): A dictionary with results for xname arguments.

    Returns:
        True if the node component matches one or more arguments in xname_results.
        Otherwise returns False.
    """

    node_component_match = False
    nid = node_component.get('NID')

    # Check for xname matches with the arguments even if nid is None
    for arg, result in xname_results.items():
        # Need to check each arg and store cid/nid data for that argument if match
        # The xname_results found flag is also set to True for the argument
        arg_match = False
        if (arg == node_xname or (
                result['type'] != 'NODE' and
                result['type'] != 'UNKNOWN' and
                result['xname'].contains_component(XName(node_xname)))):
            result['found'] = True
            arg_match = True

        if arg_match and nid:
            node_component_match = True
            result['nodes'].append({'cid': node_xname, 'nid': nid})
        elif arg_match and not nid:
            # Keep track of missing NIDs for each argument
            node_component_match = True
            result['missing_nids'] = True

    # Log an error one time if there was a node component match but no NID in the HSM data
    # Don't log an error if there was not a match
    if node_component_match and not nid:
        LOGGER.error(f'HSM API has no NID for valid node xname: {node_xname}')

    return node_component_match


def make_nid_list_from_results(xname_results, remove_duplicates):
    """Create a list of nids from xname_results.

    Args:
        xname_results (OrderedDict): A dictionary with xnames as keys.
        remove_duplicates (bool): True if duplicate nids should be removed.

    Returns:
        all_nids ([int]): A list of nids that are sorted with duplicates removed if requested.
        missing_nids (bool): True if any xnames had no nids or missing nids.
    """

    all_nids = []
    missing_nids = False
    for xname, vals in xname_results.items():
        if vals['nodes']:
            nids = []
            vals['nodes'].sort(key=lambda item: item.get('nid'))
            for node in vals['nodes']:
                nids.append(node['nid'])
                LOGGER.debug(f'xname: {node["cid"]}, nid: {node["nid"]}')
            all_nids += nids
        else:
            missing_nids = True
            LOGGER.error(f'xname: {xname}, nid: {MISSING_VALUE}')

        # A node container can have some nids set but still be missing some if bad HSM data
        if vals['missing_nids']:
            missing_nids = True

    # Remove duplicates if necessary
    if remove_duplicates:
        all_nids = sorted(set(all_nids))

    return all_nids, missing_nids


def format_nid_list(nids, nid_format):
    """Create a string representing nids from a list of integer nids in the specified format.

    Args:
        nids ([int]): A list of nids.
        nid_format (str): The format of the nid list to be returned.

    Returns:
        (str): A string representing a list of nids in the format specified.
    """

    # Create the list of nids in the specified format
    formatted_nids = []
    if nid_format == 'nid':
        for nid in nids:
            formatted_nids.append('nid' + str(nid).zfill(NUM_NID_DIGITS))
        return ','.join(formatted_nids)

    # Format is range, for example, nid[001001-001002,001005,001033-001034]
    # Check if no range and just one nid in list, then return single nid string
    if len(nids) == 1:
        return f'nid{str(nids[0]).zfill(NUM_NID_DIGITS)}'

    nid_ranges = list(group(nids))
    for range_start, range_end in nid_ranges:
        if range_start == range_end:
            formatted_nids.append(
                str(range_start).zfill(NUM_NID_DIGITS)
            )
        else:
            formatted_nids.append(
                f'{str(range_start).zfill(NUM_NID_DIGITS)}-{str(range_end).zfill(NUM_NID_DIGITS)}'
            )

    return f'nid[{",".join(formatted_nids)}]'


def do_xname2nid(args):
    """Translates node xnames to nids.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit(1): if one or more xnames can not be translated.
        SystemExit(2): if request to HSM API fails.
    """

    hsm_client = HSMClient(SATSession())

    try:
        components = hsm_client.get_node_components()
    except APIError as err:
        LOGGER.error('Request to HSM API failed: %s', err)
        raise SystemExit(ERR_HSM_API_FAILED)

    # Create a dictionary with the results for each of the xname arguments
    xname_results = init_xname_results(args.xnames)

    # Loop through the node components sorted by node xname as a string
    for component in sorted(components, key=lambda c: c.get('ID', MISSING_VALUE)):
        node_xname = component.get('ID')
        if not node_xname:
            LOGGER.error(f'HSM API has no xname for node component: {component}')
            continue

        # Flag to indicate whether or not a node component matches one or more args
        node_component_match = process_node_component(node_xname, component, xname_results)

        if not node_component_match and \
           all(result['found'] or result['type'] == 'UNKNOWN' for result in xname_results.values()):
            # Exit the for loop early if all nodes for all valid xname arguments have been found.
            # For NODE arguments, there will be only one matching node component.
            # For BMC, SLOT, CHASSIS, and CABINET arguments (container xname), there can be
            # multiple node components that match.
            #
            # The node components being processed in the for loop are sorted by the xname(str).
            # When a container xname arg is first matched, the xname argument is marked as found.
            # The end of the node components in the container is detected when there is no match
            # since they are sorted.
            break

    # For nid output, keep duplicate nids
    # The default format is range - remove duplicates and sort for range output
    remove_duplicates = True
    if args.format == 'nid':
        remove_duplicates = False
    nids, any_missing_nids = make_nid_list_from_results(xname_results, remove_duplicates)

    if nids:
        print(format_nid_list(nids, args.format))

    if any_missing_nids:
        raise SystemExit(ERR_MISSING_NAMES)
