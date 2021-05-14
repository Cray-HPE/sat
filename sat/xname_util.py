"""
Contains utilities for xnames.

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
import sys

from sat.apiclient import APIError, HSMClient
from sat.constants import BMC_TYPES
from sat.session import SATSession
from sat.xname import XName, get_matches


LOGGER = logging.getLogger(__name__)


def get_bmc_xnames(bmc_type=None):
    """Get a list of xnames that are BMCs, optionally of a single type.

    Arguments:
        bmc_type: (string): Any HSM BMC type: NodeBMC, RouterBMC or ChassisBMC.

    Returns:
        List of XName references.

    Raises:
        APIError: The API gateway was not available or HSM could not
            retrieve the xnames.
        ValueError: The payload retrieved from the API gateway was not
            in json format.
        KeyError: The json payload was valid but did not contain a field
            for 'RedfishEndpoints'
    """
    client = HSMClient(SATSession())

    try:
        response = client.get(
            'Inventory', 'RedfishEndpoints', params={'type': bmc_type} if bmc_type else {})
    except APIError as err:
        raise APIError('Failed to get xnames from HSM: {}'.format(err))

    try:
        endpoints = response.json()
        endpoints = endpoints['RedfishEndpoints']
    except ValueError as err:
        raise ValueError('Failed to parse JSON from hardware inventory response: {}'.format(err))
    except KeyError:
        raise KeyError('The response from the HSM has no entry for "RedfishEndpoints"')

    # Create list of xnames.
    xnames = []
    for num, endpoint in enumerate(endpoints):
        try:
            xnames.append(XName(endpoint['ID']))
        except KeyError:
            LOGGER.warning('Endpoint number {} in the endpoint list lacks an '
                           '"ID" field.'.format(num))

    return xnames


def screen_xname_args(xname_args, bmc_types=()):
    """Screens --xname arguments through list(s) of BMCs.

    Screens --xname arguments through list(s) of BMCs provided by the HSM, if
    available. If the HSM is unavailable, then pass the arguments through.

    If no arguments are provided, the HSM must be available. If neither the
    arguments provided or the HSM can provide xnames, the program exits with
    a non-zero return code.

    Arguments:
        xname_args (iterable of strings): The list of xnames to screen, presumably
            from the user.
        bmc_types: (container of strings): A mask of HSM BMC types (NodeBMC, RouterBMC
            or ChassisBMC) to screen against.

    Returns:
        List of XName references.

    Raises:
        Exceptions raised by get_bmc_xnames():
            APIError: The API gateway was not available or HSM could not
                retrieve the xnames.
            ValueError: The payload retrieved from the API gateway was not
                in json format.
            KeyError: The json payload was valid but did not contain a field
                for 'RedfishEndpoints'

    """

    bmc_types = frozenset(bmc_types)

    try:
        # a full set of types should query HSM only once!
        if not bmc_types or bmc_types == frozenset(BMC_TYPES):
            hsm_xnames = get_bmc_xnames(None)
        else:
            hsm_xnames = sum([get_bmc_xnames(type_) for type_ in bmc_types], [])

    except (APIError, KeyError, ValueError) as err:
        if xname_args:
            LOGGER.warning(err)
            hsm_xnames = []
        else:
            LOGGER.error(err)
            raise

    if xname_args:
        xnames = [XName(xname) for xname in xname_args]
        # Filter for matches if xnames obtained from HSM.
        if hsm_xnames:
            used, unused, xnames, _ = get_matches(xnames, hsm_xnames)
            if unused:
                LOGGER.warning('The following xname filters generated no '
                               'matches {}'.format(unused))
        else:
            LOGGER.warning('Could not obtain xnames from HSM, '
                           'will proceed using the literal values in --xnames.')

            xnames = xname_args
    else:
        xnames = hsm_xnames

    if xnames:
        return xnames

    if xname_args:
        LOGGER.error('No BMCs discovered with matching IDs.')
    else:
        LOGGER.error('No BMCs discovered.')

    sys.exit(1)
