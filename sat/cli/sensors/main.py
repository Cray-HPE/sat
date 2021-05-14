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
import traceback

import inflect

from sat.apiclient import APIError, HSMClient
from sat.config import get_config_value
from sat.constants import MISSING_VALUE
from sat.report import Report
from sat.session import SATSession

from sat.cli.sensors.telemetry_client import TelemetryClient
from sat.cli.sensors.sensor_fields import FIELD_MAPPING


CHASSIS_XNAME_REGEX = re.compile(r'x\d+c\d$')
CHASSIS_XNAME_PREFIX_REGEX = re.compile(r'x\d+c\d')


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
    traceback.print_stack(frame)
    raise ServiceExit


signal.signal(signal.SIGINT, service_shutdown)
signal.signal(signal.SIGTERM, service_shutdown)


def get_hsm_components(types):
    """Get components from HSM for the specified types.

    Args:
        types ([str]): A list of BMC types.

    Returns:
        components ([dict]): A list of dictionaries with BMC data returned from HSM.
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

    return components


def get_chassis_bmcs(components, chassis_xname):
    """Get the BMC xnames inside a Chassis.

    Args:
        components ([dict]): A list of dictionaries with BMC data returned from HSM.
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


def expand_xnames(components, xnames):
    """Expand a list of xnames to include all BMC xnames inside each Chassis.

    Args:
        components ([dict]): A list of dictionaries with BMC data returned from HSM.
        xnames ([str]): A list of xnames.

    Returns:
        expanded_xnames ([str]): A list of BMC xnames.
    """

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

    return expanded_xnames


def print_xnames_not_included(xnames, types, hsm_xnames_info):
    """Print xnames not included in a list of dictionaries with xname and type.

    Args:
        xnames ([str]): A list of xnames.
        types ([str]): A list of BMC types.
        hsm_xnames_info ([dict]): A list of dictionaries with xname and type for each BMC.

    Returns:
        None
    """

    if xnames:
        xnames_not_included = []
        for xname in xnames:
            if xname not in [xname_info.get('xname') for xname_info in hsm_xnames_info]:
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

    hsm_xnames_info = []
    components = get_hsm_components(types)

    expanded_xnames = xnames
    if xnames and recursive:
        expanded_xnames = expand_xnames(components, xnames)

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
            for metric in topic_result['Metrics']:
                for sensor in metric['Sensors']:
                    raw_table.append([extractor(topic_result, metric, sensor)
                                      for extractor in FIELD_MAPPING.values()])
    except KeyError as err:
        LOGGER.error(f'Key not present in telemetry results: {err}')
        raise SystemExit(1)

    return raw_table


def any_thread_alive(telemetry_clients):
    """Check if any threads are alive or not.

    Args:
        telemetry_clients (threading.Thread list):  A list of threads.

    Returns:
        True or False
    """

    return any(thread.is_alive() for thread in telemetry_clients)


def wait_for_threads(telemetry_clients, stop_event, update_until_timeout, total_timeout):
    """Wait for threads started for each telemetry topic.

    Args:
        telemetry_clients (threading.Thread list):  A list of threads (one per telemetry topic).
        stop_event (threading.Event): Event object used to stop all threads.
        update_until_timeout (bool): True if update sensor data for all xnames until timeout.
        total_timeout (int): The total timeout in seconds for all threads.

    Returns:
        None
    """

    LOGGER.info(f'Waiting for threads using timeout of {total_timeout} seconds')
    if update_until_timeout:
        LOGGER.info('Sensor data will continue to be updated for each xname until timeout occurs')
    else:
        LOGGER.info('Each thread will exit when sensor data is received for all xnames')

    now = time.time()
    end = now + total_timeout
    while now <= end and any_thread_alive(telemetry_clients):
        time.sleep(1)
        now = time.time()

    if not any_thread_alive(telemetry_clients):
        LOGGER.info('All threads have completed')
    else:
        LOGGER.info(f'Timed out after {total_timeout} seconds')
        LOGGER.debug('Stopping all threads - setting stop_event')
        stop_event.set()

    for client_thread in telemetry_clients:
        client_thread.join()


def get_telemetry_metrics(topics, xnames_info, batchsize, update_until_timeout, total_timeout):
    """Get sensor data from the Kafka topics for the specified xnames.

    Args:
        topics ([str]): A list of topics with telemetry data for sensors.
        xnames_info ([dict]): A list of dictionaries with xname and Type.
        batchsize (int): The number of metrics to include in each message from API.
        update_until_timeout (bool): True if update sensor data for all xnames until timeout.
        total_timeout (int): The maximum timeout in seconds for collecting data from all topics.

    Returns:
        all_topics_results ([dict]): A list of dictionaries with sensor data (one per topic).
    """

    all_topics_results = [None] * len(topics)
    telemetry_clients = []

    # Event to share between threads to coordinate shutdown
    stop_event = threading.Event()

    try:
        for i, topic in enumerate(topics):
            LOGGER.info(f'Getting telemetry data from {topic}...')
            telemetry_client = TelemetryClient(stop_event, xnames_info,
                                               batchsize, update_until_timeout,
                                               topic, all_topics_results, i)
            LOGGER.debug(f'Starting thread: {telemetry_client.getName()}')

            if telemetry_client.endpoint_alive():
                telemetry_clients.append(telemetry_client)
                telemetry_client.start()
            else:
                LOGGER.error('Exiting due to error pinging telemetry API')
                raise SystemExit(1)

        print('Please be patient...')
        wait_for_threads(telemetry_clients, stop_event, update_until_timeout, total_timeout)

    except ServiceExit:
        LOGGER.debug('Stopping all threads - setting stop_event')
        stop_event.set()
        for client_thread in telemetry_clients:
            client_thread.join()
        raise ServiceExit

    return all_topics_results


def do_sensors(args):
    """Get sensor data for the requested BMCs from the SMA Telemetry API.

    The requested BMC xnames are verified using the HSM API.
    If a ChassisBMC xname is specified, the user can optionally include the
    BMCs in the Chassis.  All Kafka telemetry topics are included by default,
    but the user can optionally limit the search to 1 or more specific topics.

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
        LOGGER.error(f'No telemetry data being collected for '
                     f'{inf.plural("xname", len(args.xnames))}: '
                     f'{args.xnames} and {inf.plural("type", len(args.types))}: {args.types}')
        raise SystemExit(1)

    print('Telemetry data being collected for '
          f'{", ".join(xname_info["xname"] for xname_info in xnames_info)}')

    try:
        all_topics_results = get_telemetry_metrics(args.topics, xnames_info,
                                                   args.batchsize, args.update_until_timeout,
                                                   int(args.timeout))

        topics_with_api_error = [topic_result['Topic']
                                 for topic_result in all_topics_results if topic_result['APIError']]
        topics_not_done = [topic_result['Topic']
                           for topic_result in all_topics_results if not topic_result['Done']
                           and not topic_result['APIError']]
        if topics_with_api_error:
            print(f'Telemetry API error getting xnames data from topics '
                  f'{", ".join(t for t in topics_with_api_error)}.')
        if topics_not_done:
            print(f'Timed out after {args.timeout} seconds searching for xnames data from topics '
                  f'{", ".join(t for t in topics_not_done)}.')

        report = Report(
            tuple(FIELD_MAPPING.keys()), None,
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

    except ServiceExit:
        print('Exiting due to SIGINT or SIGTERM.')
