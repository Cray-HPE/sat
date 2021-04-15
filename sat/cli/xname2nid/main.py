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
import logging

from sat.apiclient import APIError, HSMClient
from sat.constants import MISSING_VALUE
from sat.session import SATSession
from sat.xname import XName

LOGGER = logging.getLogger(__name__)
NUM_NID_DIGITS = 6

ERR_MISSING_NAMES = 1
ERR_HSM_API_FAILED = 2


def get_nids_using_xname(xname, components):
    """Get the nids for a given xname from node component data from the HSM API.

    Args:
        xname(str): The Node or NodeBMC xname.
        components(list): A list of dictionaries representing the node components
            in the system.

    Returns:
        A list of nids corresponding to the xname.
        A bool of True/False indicating whether or not any nids are MISSING.
    """

    missing_nids = False
    nids = []
    for component in components:
        cid = component.get('ID')
        if not cid:
            continue
        if cid == xname or str(XName(cid).get_direct_parent()) == xname:
            nid = component.get('NID')
            if nid:
                nids.append('nid' + str(nid).zfill(NUM_NID_DIGITS))
                LOGGER.info(f'xname: {cid}, nid: {nid}')
            else:
                missing_nids = True
                LOGGER.error(f'HSM API has no NID for valid ID: {cid}')
            if XName.NODE_XNAME_REGEX.match(xname):
                # There is only one match for the node xname
                break

    if not nids:
        missing_nids = True
        LOGGER.error(f'xname: {xname}, nid: {MISSING_VALUE}')

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

    any_missing_nids = False
    nids = []
    for arg in args.xnames:
        for xname in [x for x in arg.split(',') if x]:
            xname_nids, missing_nids = get_nids_using_xname(xname, components)
            if missing_nids:
                any_missing_nids = True
            if xname_nids:
                nids.extend(xname_nids)

    if nids:
        print(','.join(nids))
    if any_missing_nids:
        raise SystemExit(ERR_MISSING_NAMES)
