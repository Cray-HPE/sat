"""
Entry point for the xname2nid subcommand.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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


def init_xname_results(xname_args):
    """Initialize an ordered dictionary that will contain xnames and nids.

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


def get_matching_args_and_set_found(cid, xname_results):
    """Get a list of xnames from xname_results that match or contain a node cid and set found.

    Args:
        cid (str): A component ID for a node.
        xname_results (OrderdedDict): A dictionary with xnames as keys.

    Returns:
        matching_args ([str]: A list of xnames.
    """

    matching_args = []
    for arg in [k for k, item in xname_results.items() if item['type'] != 'UNKNOWN']:
        if (cid == arg or (
                xname_results[arg]['type'] != 'NODE' and
                xname_results[arg]['xname'].contains_component(XName(cid)))):
            matching_args.append(arg)
            xname_results[arg]['found'] = True

    return matching_args


def all_valid_args_found(xname_results):
    """Check if all valid xname arguments have been found.

    Args:
        xname_results (OrderdedDict): A dictionary with xnames as keys.

    Returns:
        True if all valid xnames in xname_results have been found.
    """

    for vals in xname_results.values():
        if vals['type'] != 'UNKNOWN' and not vals['found']:
            return False

    return True


def update_nodes_in_results(cid, nid, matching_args, xname_results):
    """Update the node results for the matching arguments.

    Args:
        cid (str): A component ID for a node.
        nid (int): A node ID for a node.
        matching_args ([str]: A list of xnames.
        xname_results (OrderdedDict): A dictionary with xnames as keys.
    """

    if not nid:
        LOGGER.error(f'HSM API has no NID for valid ID: {cid}')
    for marg in matching_args:
        if nid:
            xname_results[marg]['nodes'].append({'cid': cid, 'nid': nid})
        else:
            xname_results[marg]['missing_nids'] = True


def make_nid_list_from_results(xname_results):
    """Create a list of nids from xname_results.

    Args:
        xname_results (OrderdedDict): A dictionary with xnames as keys.

    Returns:
        nids ([str]): A list of nids.
        missing_nids (bool): True if any xnames had no nids or missing nids.
    """

    nids = []
    missing_nids = False
    for xname, vals in xname_results.items():
        if vals['nodes']:
            for node in vals['nodes']:
                nids.append('nid' + str(node['nid']).zfill(NUM_NID_DIGITS))
                LOGGER.debug(f'xname: {node["cid"]}, nid: {node["nid"]}')
        else:
            missing_nids = True
            LOGGER.error(f'xname: {xname}, nid: {MISSING_VALUE}')

        # A node container can have some nids set but still be missing some if bad HSM data
        if vals['missing_nids']:
            missing_nids = True

    return nids, missing_nids


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

    xname_results = init_xname_results(args.xnames)
    for component in sorted(components, key=lambda c: c.get('ID', MISSING_VALUE)):
        cid = component.get('ID')
        if not cid:
            continue
        matching_args = get_matching_args_and_set_found(cid, xname_results)

        # The components are sorted by the xname(str).
        # When a BMC or higher level contaianer is first matched, the argument
        # is marked as found.
        # The end of the container is detected when there is no match.
        # Then, all_valid_args_found() is used to check the 'found' flags.

        if not matching_args and all_valid_args_found(xname_results):
            break
        if not matching_args:
            continue
        update_nodes_in_results(cid, component.get('NID'), matching_args, xname_results)

    nids, any_missing_nids = make_nid_list_from_results(xname_results)

    if nids:
        if len(xname_results) == 1:
            list.sort(nids)
        print(','.join(nids))
    if any_missing_nids:
        raise SystemExit(ERR_MISSING_NAMES)
