"""
Entry point for the sensors subcommand.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
import re
import signal
import threading
import time

import inflect

from sat.apiclient import APIError, HSMClient
from sat.config import get_config_value
from sat.constants import MISSING_VALUE
from sat.report import Report
from sat.session import SATSession

from sat.cli.sensors.telemetry_client import TelemetryClient


CHASSIS_XNAME_REGEX = re.compile(r'x\d+c\d$')
CHASSIS_XNAME_PREFIX_REGEX = re.compile(r'x\d+c\d')

HEADERS = (
    'xname',
    'Type',
    'Topic',
    'Timestamp',
    'Index',
    'Location',
    'Parental Context',
    'Physical Context',
    'Device Specific Context',
    'Value')
SENSOR_KEYS = (
    'Timestamp',
    'Index',
    'Location',
    'ParentalContext',
    'PhysicalContext',
    'DeviceSpecificContext',
    'Value')

inf = inflect.engine()
LOGGER = logging.getLogger(__name__)


class ServiceExit(Exception):
    """
    Custom exception which is used to trigger the clean exit
    of all running threads and the main program.
    """
    pass


def service_shutdown(signum, frame):
    logging.warning('Caught signal %d', signum)
    raise ServiceExit


signal.signal(signal.SIGINT, service_shutdown)
signal.signal(signal.SIGTERM, service_shutdown)


def get_chassis_bmcs(components, chassis_xname):
    """Get the BMC xnames inside a Chassis.

    Args:
        components([dict]): A list of dictionaries with BMC data returned from HSM.
        chassis_xname (str): A Chassis xname that has the form xXcC, for example, x3000c0.

    Returns:
        chassis_xnames ([str]): A list of BMC xnames inside the Chassis.
    """

    chassis_xnames = []
    for component in components:
        cid = component.get('ID')
        if not cid:
            continue
        if cid[:len(chassis_xname)] == chassis_xname:
            chassis_xnames.append(cid)

    return chassis_xnames


def print_xnames_not_included(xnames, types, hsm_xnames_info):
    """Print xnames not included in a list of dictionaries with xname and type.

    Args:
        xnames ([str]): A list of xnames.
        xnames ([types]): A list of BMC types.
        hsm_xnames_info ([dict]): A list of dictionaries with xname and type for each BMC.

    Returns:
        None
    """

    if xnames:
        xnames_not_included = []
        for xname in xnames:
            if xname not in [dict.get('xname') for dict in hsm_xnames_info]:
                xnames_not_included.append(xname)

        if xnames_not_included:
            print(f'BMC {inf.plural("xname", len(xnames_not_included))} '
                  f'{xnames_not_included} not available from HSM API for {types}.')


def expand_and_screen_xnames(xnames, types, recursive):
    """Screen xnames by type and eliminate xnames not in HSM.

    Args:
        xnames ([str]): A list of xnames or None for all xnames.
        types ([str]): A list of BMC types.
        recursive (bool): True if all BMCs in a Chassis should be included for ChassisBMC xnames.

    Returns:
        hsm_xnames_info ([dict]): A list of dictionaries with xname and type for each BMC.
    """

    hsm_client = HSMClient(SATSession())

    try:
        response = hsm_client.get('State', 'Components', params={'type': types})
    except APIError as err:
        LOGGER.error(f'Request to HSM API failed: {err}')
        raise SystemExit(1)

    try:
        response_json = response.json()
    except ValueError as err:
        LOGGER.error(f'Failed to parse JSON from component state response: {err}')
        raise SystemExit(1)

    try:
        components = response_json['Components']
    except KeyError as err:
        LOGGER.error(f'Key not present in API response: {err}')
        raise SystemExit(1)

    hsm_xnames_info = []

    expanded_xnames = xnames
    if xnames and recursive:
        expanded_xnames = []
        for xname in xnames:
            # get BMCs for any Chassis in the list of xnames input
            child_xnames = []
            if CHASSIS_XNAME_REGEX.match(xname):
                child_xnames = get_chassis_bmcs(components, xname)

            if child_xnames:
                expanded_xnames.extend(child_xnames)
            else:
                expanded_xnames.append(xname)

    # screen all xnames using HSM data by name and type
    for component in components:
        cid = component.get('ID')
        if not cid:
            continue
        bmc_type = component.get('Type', MISSING_VALUE)
        if not expanded_xnames or cid in expanded_xnames:
            hsm_xnames_info.append({'xname': cid, 'Type': bmc_type})

    print_xnames_not_included(expanded_xnames, types, hsm_xnames_info)

    return hsm_xnames_info


def make_raw_table(all_topics_results):
    """Create a table of sensor data for BMCs using results from the Telemetry API.

    Args:
        all_topics_results ([dict]): A list of dictionaries with sensor data (one per topic).

    Returns:
        A list of lists containing sensor data for each BMC xname.
    """

    raw_table = []
    try:
        for topic_result in all_topics_results:
            topic = topic_result['Topic']
            for metric in topic_result['Metrics']:
                context = metric['Context']
                bmc_type = metric['Type']
                for sensor in metric['Sensors']:
                    row = [context, bmc_type, topic]
                    for sensor_key in SENSOR_KEYS:
                        row.append(sensor.get(sensor_key, MISSING_VALUE))
                    raw_table.append(row)
    except KeyError as err:
        LOGGER.error(f'Key not present in telemetry results: {err}')
        raise SystemExit(1)

    return raw_table


def wait_for_threads(telemetry_clients, total_timeout):
    """Wait for threads started for each telemetry topic.

    Args:
        telemetry_clients (threading.Thread list):  A list of threads (one per telemetry topic).
        total_timeout (int): The total timeout in seconds for all threads.

    Returns:
        None
    """

    timeout = total_timeout
    for client_thread in telemetry_clients:
        start = time.time()
        LOGGER.debug(f'Waiting for thread: {client_thread.getName()}')
        if timeout <= 0 and client_thread.is_alive():
            LOGGER.debug('Setting stop_event.')
            client_thread.stop()
            client_thread.join()
        elif timeout > 0:
            LOGGER.debug(f'Calling join with timeout = {timeout}')
            client_thread.join(timeout=timeout)
            if client_thread.is_alive():
                LOGGER.debug(f'Setting stop_event for running thread due to timeout for '
                             f'{client_thread.get_topic()}')
                client_thread.stop()
                client_thread.join()
                timeout = 0
            else:
                now = time.time()
                timeout = timeout - int(now-start)


def get_telemetry_metrics(topics, xnames_info, batchsize, total_timeout):
    """Get sensor data from the Kafka topics for the specified xnames.

    Args:
        topics ([str]): A list of topics with telemetry data for sensors.
        xnames_info ([dict]): A list of dictionaries with xname and Type.
        batchsize (int): The number of metrics to include in each message from API.
        total_timeout (int): The maximum timeout in seconds for collecting data from all topics.

    Returns:
        all_topics_results ([dict]): A list of dictionaries with sensor data (one per topic).
    """

    all_topics_results = [None] * len(topics)
    telemetry_clients = []

    try:
        # Event to share between threads to coordinate shutdown
        stop_event = threading.Event()

        for i, topic in enumerate(topics):
            LOGGER.info(f'Getting telemetry data from {topic}...')
            telemetry_client = TelemetryClient(stop_event, xnames_info,
                                               batchsize, topic, all_topics_results, i)
            LOGGER.debug(f'Starting thread: {telemetry_client.getName()}')

            if telemetry_client.endpoint_alive():
                telemetry_clients.append(telemetry_client)
                telemetry_client.start()
            else:
                LOGGER.error('Exiting due to error pinging telemetry API')
                raise SystemExit(1)

        print('Please be patient...')
        wait_for_threads(telemetry_clients, total_timeout)

    except ServiceExit:
        LOGGER.debug('Stopping all threads - setting stop_event')
        stop_event.set()
        wait_for_threads(telemetry_clients, 0)
        raise ServiceExit

    return all_topics_results


def do_sensors(args):
    """Get sensor data for the requested BMCs from the SMA Telemetry API.

    The requested BMC xnames are verified using the HSM API.
    If a ChassisBMC xname is specified, the user can optionally include the
    BMCs in the Chassis.  All Kafka telemetry topics are included by default,
    but the user can optionally limit the search to 1 or more speific topics.

    The type of BMC can also be specified so that the BMCs are filtered by type.

    The readings that result are displayed in a tabular format using the standard
    Report class.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """

    xnames_info = expand_and_screen_xnames(args.xnames, args.types, args.recursive)
    if not xnames_info:
        print('No telemetry data being collected.')
        raise SystemExit(1)

    print('Telemetry data being collected for', end=' ')
    print(', '.join(x for x in [dict['xname'] for dict in xnames_info]))

    try:
        all_topics_results = get_telemetry_metrics(args.topics, xnames_info,
                                                   args.batchsize, int(args.timeout))

        topics_not_done = [dict['Topic'] for dict in all_topics_results if not dict['Done']]
        if topics_not_done:
            print(f'Timed out after {args.timeout} secs searching for xnames data from', end=' ')
            print(', '.join(x for x in topics_not_done), end='.\n')

        report = Report(
            HEADERS, None,
            args.sort_by, args.reverse,
            get_config_value('format.no_headings'),
            get_config_value('format.no_borders'),
            filter_strs=args.filter_strs)

        raw_table = make_raw_table(all_topics_results)
        report.add_rows(raw_table)

        if args.format == 'yaml':
            print(report.get_yaml())
        else:
            print(report)

    except KeyError as err:
        LOGGER.error(f'Key error: {err}')
        raise SystemExit(1)
    except ServiceExit:
        LOGGER.debug('Exiting due to ServiceExit')
