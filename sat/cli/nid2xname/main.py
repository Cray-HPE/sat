"""
Entry point for the nid2xname subcommand.

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


LOGGER = logging.getLogger(__name__)


def get_xname_using_nid(nid, components):
    """Get the xname for a given nid from node component data from the HSM API.

    Args:
        nid(str): The nid.
        components(list): A list of dictionaries representing the node components
            in the system.

    Returns:
        A list of xnames corresponding to the nid.
    """

    xname = MISSING_VALUE
    for component in components:
        cnid = component.get('NID', MISSING_VALUE)
        if cnid == MISSING_VALUE:
            continue
        if str(cnid) == nid:
            xname = component.get('ID', MISSING_VALUE)
            break

    LOGGER.info(f'xname: {xname}, nid: {nid}')
    return xname


def fixup_nid(nid_arg):
    """Remove leading characters from a nid input by the user.

    Args:
        nid_arg(str): The nid argument as input by the user.

    Returns:
        A nid(str) with leading characters 'nid' and '0' stripped off.
    """

    if nid_arg.startswith('nid'):
        nid_arg = nid_arg[3:]

    return nid_arg.lstrip('0') or '0'


def parse_nid_arg(nid_arg):
    """Parse a nid argument that can be either a single nid or a range of nids.

    Args:
        nid_arg(str): The nid argument as input by the user.
            The nid argument can be either a single nid or a range of nids.

    Returns:
        A list of nid(str) with leading characters 'nid' and '0' stripped off.
    """

    nids = []
    if '-' in nid_arg:
        # nid could be a range of nids
        nid1 = fixup_nid(nid_arg.split('-', 1)[0])
        nid2 = fixup_nid(nid_arg.split('-', 1)[1])
        try:
            nids = list(map(str, range(int(nid1), int(nid2)+1)))
        except ValueError:
            # Use the original nid_arg
            LOGGER.debug(f'Range of {nid_arg} are not integers.')

    if not nids:
        nids.append(fixup_nid(nid_arg))

    return nids


def do_nid2xname(args):
    """Translates node nids to xnames.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit: if request to HSM API fails.
    """
    hsm_client = HSMClient(SATSession())

    try:
        components = hsm_client.get_node_components()
    except APIError as err:
        LOGGER.error('Request to HSM API failed: %s', err)
        raise SystemExit(1)

    xnames = []
    for arg in args.nids:
        for nid_arg in [n for n in arg.split(',') if n]:
            for nid in parse_nid_arg(nid_arg):
                xnames.append(get_xname_using_nid(nid, components))

    print(','.join(xnames))
