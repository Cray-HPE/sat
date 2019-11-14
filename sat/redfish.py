"""
Functions to assist with querying a Redfish endpoint.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import getpass

import requests

from sat.config import get_config_value
from sat.util import pester


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
        username = pester("Username: ", "^.*$",
                          human_readable_valid="Redfish",
                          parse_answer=(lambda x: x))
        password = ''
    if not password:
        password = getpass.getpass('Password for {}: '.format(username))

    return username, password


def query(xname, addr, username, password):
    """Make a query using the redfish username and password to the URL.

    Args:
        xname: Xname of Redfish node.
        addr: List whose members represent the entries in the Redfish path
            after https://xname/redfish/v1/.
        username: Redfish username.
        password: Redfish password.

    Returns:
        url: The formatted url which was used by to make the query
        data: Dictionary created from the JSON in the response.

    Raises:
        requests.exceptions.ConnectionError: requests.get can raise this if
            there was no endpoint present.
    """
    url = 'https://{}/redfish/v1/{}'.format(xname, '/'.join(addr))
    try:
        data = requests.get(url, auth=(username, password), verify=False)
    except requests.exceptions.ConnectionError as ce:
        raise requests.exceptions.ConnectionError(url)

    return url, data.json()
