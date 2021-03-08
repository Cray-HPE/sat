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

ERR_MISSING_NAMES = 1
ERR_HSM_API_FAILED = 2


def get_xname_using_nid(nid, components):
    """Get the xname for a given nid from node component data from the HSM API.

    Args:
        nid(str): The nid.
        components(list): A list of dictionaries representing the node components
            in the system.

    Returns:
        An xname corresponding to the nid.
    """

    xname = None
    for component in components:
        cnid = component.get('NID')
        if not cnid:
            continue
        if str(cnid) == nid:
            xname = component.get('ID')
            if xname:
                LOGGER.info(f'xname: {xname}, nid: {nid}')
            else:
                LOGGER.error(f'HSM API has no ID for valid NID: {cnid}')
            break

    if not xname:
        LOGGER.error(f'xname: {MISSING_VALUE}, nid: {nid}')

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


def find_occurrences(s, ch):
    """Find all occurrences of a character in a string.

    Args:
        s(str): The string.
        ch(str): The character to find in the string.

    Returns:
        A list of indices into the string where the character is found.
    """
    return [i for i, letter in enumerate(s) if letter == ch]


def convert_pdsh_nid_list(nids):
    """Convert a single pdsh list to a list without brackets.

    Args:
        nids(str): A pdsh range in the form prefix[#-#,#,...]

    Returns:
        A new string where the brackets have been removed and the prefix added to
        each integer in the bracketed list.
        Returns the original string if there are any brackets in the input string.
    """

    new_nids = ''
    if '[' in nids and ']' in nids:
        prefix = nids.split('[')[0]
        middle = nids.split('[')[1][:-1]

        for nid in middle.split(','):
            new_nid = nid
            dash_indices = find_occurrences(nid, '-')
            if len(dash_indices) == 1:
                new_nid = f'{nid[:dash_indices[0]]}-{prefix}{nid[dash_indices[0]+1:]}'
            if new_nids:
                new_nids += ','
            new_nids += f'{prefix}{new_nid}'

    if not new_nids:
        new_nids = nids
    return new_nids


def convert_pdsh_lists_to_standard_lists(nids):
    """Convert a comma delimited list of nids including pdsh lists.

    Args:
        nids(str): A comma delimited list of nids using different formats:
            range in the form prefix#-prefix#
            pdsh list in the form prefix[#-#,#,...]
            nid in the form nid#
            nid in the form #

    Returns:
        A new string where the brackets have been removed and the prefix added to each
        integer in the bracketed list for each of the pdsh lists in the input string.
        Returns the original string if there are any errors converting the string.
    """

    new_nids = []
    rbracket_indices = find_occurrences(nids, ']')
    lbracket_indices = find_occurrences(nids, '[')
    if rbracket_indices and len(rbracket_indices) == len(lbracket_indices):
        nids_index = 0
        for iteration, rbracket_index in enumerate(rbracket_indices):
            if iteration > 0:
                # More than one set of brackets that have to be delimited by a comma
                previous_rbracket_index = rbracket_indices[iteration-1]
                if nids[previous_rbracket_index+1] != ',':
                    LOGGER.error(f'Unexpected character in nid list: {nids}')
                    new_nids = []
                    break
                # Skip the comma
                nids_index = previous_rbracket_index + 2
            substr_with_brackets = nids[nids_index:rbracket_index+1]

            # Find the prefix to the pdsh list
            # Skip over preceding comma delimited strings before the left bracket
            # Append the substring that is skipped to the new nid list
            prefix_to_left_bracket = substr_with_brackets.split('[', 1)[0]
            if ',' in prefix_to_left_bracket:
                comma_indices = find_occurrences(prefix_to_left_bracket, ',')
                last_comma_index = comma_indices[len(comma_indices)-1]
                new_nids.append(prefix_to_left_bracket[:last_comma_index])
                substr_with_brackets = substr_with_brackets[last_comma_index+1:]
            new_nids.append(convert_pdsh_nid_list(substr_with_brackets))

        # Add any remaining characters after the last right bracket followed by a comma
        last_rbracket_index = rbracket_indices[len(rbracket_indices)-1]
        if last_rbracket_index < len(nids)-1:
            new_nids.append(nids[last_rbracket_index+2:])
    else:
        new_nids.append(nids)

    if new_nids:
        return ','.join(new_nids)

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
        raise SystemExit(ERR_HSM_API_FAILED)

    any_missing_xnames = False
    xnames = []
    for arg in args.nids:
        # Each arg is a list of nids and nid ranges separated by commas.
        # A nid is either an integer or a string of the form: nid123456,
        # that is “nid” and a number.
        # Ranges can be specified using:
        #     standard nid range: n-m where n < m
        #     standard range with "nid" prefixes: nid1-nid5
        #     pdsh range: prefix[n-m,l-k,j,...], where n < m and l < k
        # Example of an arg: 1-5,6,nid[001921,002000-002008]

        new_arg = convert_pdsh_lists_to_standard_lists(arg)

        # the arg no longer has prefix[nid...]s
        for nid_arg in [n for n in new_arg.split(',') if n]:
            for nid in parse_nid_arg(nid_arg):
                xname = get_xname_using_nid(nid, components)
                if not xname:
                    any_missing_xnames = True
                else:
                    xnames.append(xname)

    if xnames:
        print(','.join(xnames))
    if any_missing_xnames:
        raise SystemExit(ERR_MISSING_NAMES)
