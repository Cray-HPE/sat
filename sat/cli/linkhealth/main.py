"""
The main entry point for the linkhealth subcommand.

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

import logging
import os
import sys
from collections import defaultdict

import requests

from sat import redfish
from sat.config import get_config_value
from sat.report import Report
from sat.xname import XName


LOGGER = logging.getLogger(__name__)


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
            continue

        try:
            port_mapping[xname] = [os.path.basename(x['@odata.id']) for x in response['Members']]
        except KeyError:
            LOGGER.error(
                'The JSON payload for Redfish URL {} did not contain the '
                'expected fields "Members.@odata.id"'.format(url))
            continue

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
        'flow_control_config',
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
                entry['flow_control_config'] = response['FlowControlConfiguration']
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

    xnames = redfish.screen_xname_args(args.xnames, ['RouterBMC'])

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
