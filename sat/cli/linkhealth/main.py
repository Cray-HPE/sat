"""
The main entry point for the linkhealth subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import json
import logging
import os
import subprocess
import sys
import urllib3
from collections import defaultdict

import requests

from sat import redfish
from sat.apiclient import APIError, HSMClient
from sat.config import get_config_value
from sat.filtering import is_subsequence
from sat.report import Report
from sat.session import SATSession
from sat.xname import XName


LOGGER = logging.getLogger(__name__)


def get_router_xnames():
    """Get a list of xnames that are of type RouterBMC.

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
            'Inventory', 'RedfishEndpoints', params={'type': 'RouterBMC'})
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


def get_matches(filters, elems):
    """Separate a list into matching and unmatched members.

    Args:
        filters: List of strings which represent subsequences. If an elem in
            elems contains any subsequence in this list, then it will be
            considered a match.
        elems: List of elems to filter.

    Returns:
        used: Filters that generated a match.
        unused: Filters that did not generate a match.
        matches: Elements that matched one or more filters.
        no_matches: Elements that did not match anything.
    """
    used = set()
    unused = set(filters)
    matches = set()
    no_matches = set(elems)

    for elem in elems:
        for filter_ in filters:
            if is_subsequence(filter_, str(elem)):
                used.add(filter_)
                unused.discard(filter_)
                matches.add(elem)
                no_matches.discard(elem)

    return used, unused, matches, no_matches


def get_jack_port_ids(xnames, username, password):
    """Retrieve all jack-port IDs for the xnames.

    A jack ID represents a physical slot in the Rosetta swtitch, and each
    has 2 logical ports.

        eg. A jack ID might take the form of j0 or bp0, and the whole port
            address would be j0p0 and j0p1.

    Args:
        xnames: List of xnames to query.
        username: Redfish username.
        password: Redfish password.

    Returns:
        A dictionary where the keys are xnames and the values are lists
        of endpoints.
    """
    port_mapping = {}
    addr = [
        'Chassis',
        'Enclosure',
        'NetworkAdapters',
        'Rosetta',
        'NetworkPorts',
    ]

    for xname in xnames:

        try:
            url, response = redfish.query(xname, addr, username, password)
        except requests.exceptions.RequestException as err:
            LOGGER.error('Query failed. {}'.format(err))
            sys.exit(1)

        try:
            port_mapping[xname] = [os.path.basename(x['@odata.id']) for x in response['Members']]
        except KeyError:
            LOGGER.error(
                'The JSON payload for Redfish URL {} did not contain the '
                'expected fields "Members.@odata.id"'.format(url))
            sys.exit(1)

    return port_mapping

def get_cable_presence(xnames, username, password):
    """Determine the presence of cables as reported by Redfish.

    The {xname}/Chassis/Enclosure/NetworkAdapters/Rosetta/Oem/NetworkCables
    endpoint is queried, and reports the jack IDs along with whether or
    not a cable is present in the jack.

        'j' ports can report 'Present' or 'Not Present'
        'bp' ports can report 'No Device'.

    Args:
        xnames: List of xnames to ask.
        username: Redfish username.
        password: Redfish password.

    Returns:
        A dict where the keys are the xnames and the values are dicts
        of jack IDs mapped to string values indicating their presence.
    """
    presence_mapping = dict()

    endpoint_addr = [
        'Chassis',
        'Enclosure',
        'NetworkAdapters',
        'Rosetta',
        'Oem',
        'NetworkCables',
    ]

    for xname in xnames:
        try:
            url, response = redfish.query(
                xname, endpoint_addr, username, password)
        except requests.exceptions.ConnectionError as ce:
            LOGGER.warning(
                'While determining which ports are present: No endpoint '
                'at {}.'.format(ce))
            continue

        if 'error' in response:
            code = response['error']['code']
            msg = response['error']['message']
            LOGGER.warning(
                'While determining present ports; Redfish URL {} returned an error with the '
                'following code and message.'.format(url))
            LOGGER.warning('Code: {}'.format(code))
            LOGGER.warning('Message: {}'.format(msg))
            continue

        presence_mapping[xname] = dict()
        for member in response['Members']:
            id = os.path.basename(member['@odata.id'])
            cable_addr = endpoint_addr + [id]

            try:
                url, response = redfish.query(
                    xname, cable_addr, username, password)
            except requests.exceptions.ConnectionError as ce:
                LOGGER.warning(
                    'No endpoint at {} despite it being listed as a port in '
                    '{}.'.format(ce, '/'.join([xname] + endpoint_addr)))
                continue

            try:
                presence_mapping[xname][id] = response['CableStatus']
            except KeyError:
                LOGGER.error('No "CableStatus" found for {}{}.'.format(xname, id))
                presence_mapping[xname][id] = 'MISSING'

    return presence_mapping


def get_report(xname_port_map, username, password, args):
    """Query the endpoints for their health and create a Report.

    Args:
        xname_port_map: Dict where the keys are xnames and the values are the
            list of endpoints.
        username: Redfish username.
        password: Redfish password.
        args: Argparser instance.

    Returns:
        sat.Report instance.
    """
    headings = [
        'xname',
        'cable_present',
        'physical_port',
        'link_status',
        'health',
        'state',
        'flow_control_configuration',
        'link_speed_mbps'
    ]

    report = Report(
        headings,
        sort_by=args.sort_by,
        reverse=args.reverse,
        no_headings=get_config_value('format.no_headings'),
        no_borders=get_config_value('format.no_borders'),
        filter_strs=args.filter_strs)

    # determine which cables are present
    presence_mapping = get_cable_presence(xname_port_map.keys(), username, password)

    for xname, jackports in xname_port_map.items():

        for jackport in jackports:
            addr = [
                'Chassis',
                'Enclosure',
                'NetworkAdapters',
                'Rosetta',
                'NetworkPorts',
                jackport,
            ]
            try:
                url, response = redfish.query(xname, addr, username, password)
            except requests.exceptions.RequestException as err:
                LOGGER.warning('Query failed. Skipping. {}'.format(err))
                continue

            entry = defaultdict(lambda: 'MISSING')
            entry['xname'] = XName('{}{}'.format(xname, jackport))

            try:
                entry['physical_port'] = int(response['PhysicalPortNumber'])
            except KeyError:
                pass
            except ValueError:
                LOGGER.warning(
                    'PhysicalPortNumber field for jackport {} was not an '
                    'integer. Value was {}.'.format(
                        entry['xname'], response['PhysicalPortNumber']))
                entry['physical_port'] = response['PhysicalPortNumber']

            # Raw jack ID - Use to print physical presence of cable.
            jack = jackport[:-2] 
            if jack in presence_mapping[xname]:
                entry['cable_present'] = presence_mapping[xname][jack]

            try:
                entry['link_status'] = response['LinkStatus']
            except KeyError:
                pass

            try:
                entry['health'] = response['Status']['Health']
            except KeyError:
                pass

            try:
                entry['state'] = response['Status']['State']
            except KeyError:
                pass

            try:
                entry['flow_control_configuration'] = response['FlowControlConfiguration']
            except KeyError:
                pass

            try:
                entry['link_speed_mbps'] = response['CurrentLinkSpeedMbps']
            except KeyError:
                pass

            report.add_row(entry)

    return report


def do_linkhealth(args):
    """Run the linkhealth command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """
    LOGGER.debug('do_linkhealth received the following args: %s', args)

    username, password = redfish.get_username_and_pass(args.redfish_username)

    # TODO: See SAT-140 for how we should handle this.
    urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

    try:
        xnames = get_router_xnames()
    except (APIError, KeyError, ValueError) as err:
        if args.xnames:
            LOGGER.warning(err)
            LOGGER.warning(
                'Will proceed using the literal values in --xnames.')
            xnames = args.xnames
        else:
            LOGGER.error(err)
            sys.exit(1)

    # filter for matches
    if args.xnames:
        used, unused, xnames, _ = get_matches(args.xnames, xnames)

        if unused:
            LOGGER.warning('The following xname filters generated no '
                           'matches {}'.format(unused))

    if not xnames:
        if args.xnames:
            LOGGER.error('No BMC routers discovered with matching IDs.')
        else:
            LOGGER.error('No BMC routers discovered.')

        sys.exit(1)

    # get all ports for all xnames
    xname_port_map = get_jack_port_ids(xnames, username, password)
    if not xname_port_map:
        LOGGER.error('No physical ports discovered')
        sys.exit(1)

    # create and print the report
    report = get_report(xname_port_map, username, password, args)

    if args.format == 'pretty':
        print(report)
    elif args.format == 'yaml':
        print(report.get_yaml())
