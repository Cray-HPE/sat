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
        raise APIError('Failed to get xnames from HSM: %s', err)

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


def get_endpoint_ids(xnames, username, password):
    """Retrieve all endpoint ids for the xnames.

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
        except requests.exceptions.ConnectionError as ce:
            LOGGER.error('No endpoint at {}.'.format(ce))
            sys.exit(1)

        if 'error' in response:
            code = response['error']['code']
            msg = response['error']['message']
            LOGGER.error(
                'Querying Redfish URL {} returned an error with the '
                'following code and message.'.format(url))
            LOGGER.error('Code: {}'.format(code))
            LOGGER.error('Message: {}'.format(msg))
            sys.exit(1)

        try:
            port_mapping[xname] = [os.path.basename(x['@odata.id']) for x in response['Members']]
        except KeyError:
            LOGGER.error(
                'The JSON payload for Redfish URL {} did not contain the '
                'expected fields "Members.@odata.id"'.format(url))
            sys.exit(1)

    return port_mapping


def get_configured_ports():
    """Return a mapping from xnames to physical ports that are configured.

    Kubernetes is used to query these ports. These are the ports that appear
    in the 'fabricPorts' and 'edgePorts' fields in the output from the
    following command.

        'kubectl -n services get configmaps bringup-info -o json'

    Returns:
        A dict where the keys are the xnames and the values are lists
        of physical ports that are configured for that endpoint.

        If there was an error gathering this information, then any queries about
        ports within this dictionary shall return True.
    """
    default = defaultdict(lambda: range(0, 1000000))
    cmd = 'kubectl -n services get configmaps bringup-info -o json'

    try:
        data = subprocess.check_output(cmd.split())
    except Exception as e:
        LOGGER.warning(
            'An exception happened while attempting to execute "{}". '
            'The report will not trim unconfigured ports.'.format(cmd))
        LOGGER.warning(e)
        return default

    try:
        # json.loads may have a bug where this entry is saved as a string.
        # This code corrects for that.
        data = json.loads(data)
        data = json.loads(data['data']['topology'])
    except (json.decoder.JSONDecodeError, KeyError):
        LOGGER.warning(
            'Cannot determine which ports are unconfigured. The '
            'JSON payload did not contain the expected mapping of '
            '"data.topology.switches.[IP,fabricPorts,edgePorts]"')
        return default

    port_map = defaultdict(lambda: set())
    try:
        for switch in data['switches']:
            xname = XName(switch['IP'])
            fabric_ports = switch['fabricPorts']
            edge_ports = switch['edgePorts']
            port_map[xname] = set(fabric_ports + edge_ports)
    except KeyError:
        LOGGER.warning(
            'Cannot determine which ports are unconfigured. The '
            'JSON payload did not contain the expected mapping of '
            '"data.topology.switches.[IP,fabricPorts,edgePorts]"')
        return default

    return port_map


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

    # first determine which ports are configured. It's not a super big deal
    # if this fails - it's just a hint to help trim the report.
    configured_ports = get_configured_ports()

    for xname, endpoints in xname_port_map.items():
        for endpoint in endpoints:
            addr = [
                'Chassis',
                'Enclosure',
                'NetworkAdapters',
                'Rosetta',
                'NetworkPorts',
                endpoint,
            ]
            try:
                url, response = redfish.query(xname, addr, username, password)
            except requests.exceptions.ConnectionError as ce:
                LOGGER.warning('No endpoint at {}. Skipping.'.format(ce))
                continue

            if 'error' in response:
                code = response['error']['code']
                msg = response['error']['message']
                LOGGER.error(
                    'Querying Redfish URL {} returned an error with the '
                    'following code and message.'.format(url))
                LOGGER.error('Code: {}'.format(code))
                LOGGER.error('Message: {}'.format(msg))
                sys.exit(1)

            entry = defaultdict(lambda: 'Not found')
            entry['xname'] = XName('{}{}'.format(xname, endpoint))

            try:
                entry['physical_port'] = int(response['PhysicalPortNumber'])
            except KeyError:
                pass
            except ValueError:
                LOGGER.warning('PhysicalPortNumber field for endpoint {} was not '
                               'an integer.'.format(entry['xname']))
                LOGGER.warning('This link might not appear in the report.')
                pass

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
                entry['flow_control_configuration'] = None

            try:
                entry['link_speed_mbps'] = response['CurrentLinkSpeedMbps']
            except KeyError:
                pass

            if (args.all
                    or (args.configured and entry['physical_port'] in configured_ports[xname])
                    or (args.unhealthy and entry['health'] != 'OK')
                    or (entry['physical_port'] in configured_ports[xname] and entry['health'] != 'OK')):
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
    xname_port_map = get_endpoint_ids(xnames, username, password)
    if not xname_port_map:
        LOGGER.error('No physical ports discovered')
        sys.exit(1)

    # create and print the report
    report = get_report(xname_port_map, username, password, args)

    if args.format == 'pretty':
        if not report.data:
            print('All links for Redfish endpoints {} are healthy '
                  '(or unconfigured).'.format(xnames))
        else:
            print(report)
    elif args.format == 'yaml':
        print(report.get_yaml())
