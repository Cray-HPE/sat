"""
Functions to assist with querying a Redfish endpoint.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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

import getpass
import logging
import sys

import requests

from sat.config import get_config_value
from sat.constants import BMC_TYPES
from sat.apiclient import APIError, HSMClient
from sat.session import SATSession
from sat.xname import XName, get_matches


LOGGER = logging.getLogger(__name__)


class RedfishQueryError(requests.exceptions.RequestException):
    """Subclasses requests.exceptions.RequesException

    Meant for delivering status codes and an english reason for why a call
    to query delivered a payload indicating an error from the server.
    """
    def __init__(self, summary, code, reason):
        self.summary = summary
        self.code = code
        self.reason = reason
        super().__init__(summary)


def get_username_and_pass(suggestion=''):
    """Gets the username and password for a user.

    This will lookup the username and password from the config
    file. If either is not supplied, then the user will be queried
    interactively for both.

    Args:
        suggestion: If empty, then this function will look in the
            configuration file.

    Returns: a pair (2-tuple) containing the username and password
        for use with the Redfish API.
    """
    username = suggestion or get_config_value('redfish.username')
    password = '' if suggestion else get_config_value('redfish.password')
    if not username:
        username = input("Redfish username: ")
        password = ''
    if not password:
        password = getpass.getpass('Password for {}: '.format(username))

    return username, password


def query(xname, addr, username, password):
    """Make a query using the redfish username and password to the URL.

    Either of the exceptions raised by this function can be caught by handling
    requests.exceptions.RequestException.

    Args:
        xname: Xname of Redfish node.
        addr: List whose members represent the entries in the Redfish path
            after https://xname/redfish/v1/.
        username: Redfish username.
        password: Redfish password.

    Returns:
        url: The formatted url which was used by to make the query
        response: Dictionary created from the JSON in the response. If the
            response failed, then the response is plainly returned.

    Raises:
        requests.exceptions.ConnectionError: requests.get can raise this if
            there was no endpoint present.

        RedfishQueryError: Any other error happened after the presence of the
            endpoint was established. Includes 'code' and 'reason' fields to
            indicate the http error code and reason for the failure.
    """
    url = 'https://{}/redfish/v1/{}'.format(xname, '/'.join(addr))
    try:
        response = requests.get(url, auth=(username, password))
    except requests.exceptions.ConnectionError:
        msg = 'No Redfish resource at url {}'.format(url)
        raise requests.exceptions.ConnectionError(msg)

    # response isn't None, the class just evals to False if an error occurred.
    if not response:
        code = response.status_code
        reason = response.reason
        msg = ('GET request to Redfish URL {} returned an error with the '
               'following code and message: {}: {}'.format(url, code, reason))
        raise RedfishQueryError(msg, code, reason)

    return url, response.json()


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
