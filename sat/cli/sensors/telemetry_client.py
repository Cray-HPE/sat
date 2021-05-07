"""
The TelemetryClient for the sensors subcommand.

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

import datetime
import json
import logging
import threading
import time
import sseclient

from sat.apiclient import APIError, ReadTimeout, TelemetryAPIClient
from sat.session import SATSession

from sat.cli.sensors.sensor_fields import UNIQUE_SENSOR_FIELD_MAPPING


LOGGER = logging.getLogger(__name__)


class TelemetryClient(threading.Thread):
    """A thread that collects telemetry data using the SMA Telemetry API."""

    # Default timeout for the telemetry streaming API
    GET_TIMEOUT_SECS = 60

    # Time to sleep in between telemetry API reconnect attempts
    RECONNECT_DELAY_SECS = 10

    # Number of times to try to reconnect
    RECONNECT_RETRIES = 3

    def __init__(self, stop_event, xnames_info, batchsize, update_until_timeout,
                 topic, all_results, results_index):
        """Create a thread to connect to streaming telemetry API.

        Args:
            stop_event (threading.Event): Event object used to stop all threads.
            xnames_info ([dict]): A list of dictionaries with xname and Type.
            batchsize (int): The number of metrics to include in each message from API.
            update_until_timeout (bool): True if update sensor data for all xnames until timeout.
            topic (str): The name of the Kafka telemetry topic.
            all_results ([dict]): A list of dictionaries with temeletry results for all topics.
            results_index (int): The index into the results list for this thread.
        """

        super().__init__()
        self.stop_event = stop_event
        self.batchsize = batchsize
        self.update_until_timeout = update_until_timeout
        self.retries = 0

        # initialize the results for this thread
        metrics = [
            {
                'Context': xname_info['xname'],
                'Type': xname_info['Type'],
                'Count': 0,
                'Sensors': []
            } for xname_info in xnames_info
        ]
        self.results = {
            'Topic': topic,
            'Done': False,
            'APIError': False,
            'Metrics': metrics
        }
        all_results[results_index] = self.results
        self.api_client = TelemetryAPIClient(SATSession())

    def get_topic(self):
        """Get the Kafka topic being consumed using this thread.

        Returns:
           A topic name string or None.
        """

        return self.results.get('Topic')

    def stop(self):
        """Stop the execution of this thread at the next opportunity.
        """

        self.stop_event.set()

    def stopped(self):
        """Return whether a stop of this thread was requested.

        Returns:
           True or False
        """

        return self.stop_event.is_set()

    def endpoint_alive(self):
        """Check whether or not the Telemetry API service is alive or not.

        Returns:
           True or False
        """
        return self.api_client.ping()

    def add_or_update_sensor(self, metric, sensor):
        """Add or update data for a sensor in the results for a metric.

        Args:
            metric (dict): A dictionary with sensor data collected so far for the xname.
            sensor (dict): A dictionary with new sensor data for the xname.
        """

        new_unique_sensor_data = [extractor(self.get_topic(), metric, sensor) for extractor
                                  in UNIQUE_SENSOR_FIELD_MAPPING.values()]

        # Search for the sensor in the existing results and update it if it exists
        metric_sensors = metric['Sensors']
        for metric_sensor in metric_sensors:
            old_unique_sensor_data = [extractor(self.get_topic(), metric, metric_sensor)
                                      for extractor in UNIQUE_SENSOR_FIELD_MAPPING.values()]
            if old_unique_sensor_data == new_unique_sensor_data:
                LOGGER.debug(f'Updating sensor for xname: {metric["Context"]} '
                             f'and topic: {self.get_topic()}')
                LOGGER.debug(f'{sensor}')
                metric_sensor['Timestamp'] = sensor['Timestamp']
                metric_sensor['Value'] = sensor['Value']
                return

        # Sensor doesn't exist in the results so add it
        LOGGER.debug(f'Adding sensor for xname: {metric["Context"]} '
                     f'and topic: {self.get_topic()}')
        LOGGER.debug(f'{sensor}')
        metric_sensors.append(sensor)

    def update_metric_sensors(self, metric, sensors):
        """Initialize or update the sensors data in the thread results for a metric.

        Args:
            metric (dict): A dictionary with sensor data collected so far for the xname.
            sensors ([dict]): A list of dictionaries with new sensor data for the xname.
        """

        if not metric['Sensors']:
            LOGGER.debug(f'Setting first set of sensors for xname: {metric["Context"]} '
                         f'and topic: {self.get_topic()}')
            for sensor in sensors:
                LOGGER.debug(f'{sensor}')
            metric['Sensors'] = sensors
            return

        # Sensor data has already been collected for the xname, so add or update it
        for sensor in sensors:
            self.add_or_update_sensor(metric, sensor)

    def set_sensors_for_context(self, context, sensors):
        """Set the sensors data in the thread results for a particular context.

        Args:
            context (str): The Context (xname) of the sensor data.
            sensors ([dict]): A list of dictionaries with sensor data for the xname.

        Returns:
           True if successful and otherwise False.
        """

        metrics = self.results.get('Metrics')
        for metric in metrics:
            try:
                if metric['Context'] == context:
                    metric['Count'] += 1
                    self.update_metric_sensors(metric, sensors)
                    return True
            except KeyError as err:
                LOGGER.error(f'Failed to parse telemetry results due to missing key(s) in '
                             f'Metrics: {err}')
                raise

        return False

    def am_i_done(self):
        """Checks if the thread is done getting data for all xnames and topics requested.

        Returns:
           True if all done and otherwise False.
        """

        if self.update_until_timeout:
            return False

        metrics = self.results.get('Metrics')
        for metric in metrics:
            try:
                if metric['Count'] == 0:
                    return False
            except KeyError as err:
                LOGGER.error(f"Failed to get metric count due to missing 'Count' key: {err}")
                raise

        return True

    def unpack_data(self, messages):
        """Unpack data returned from the sseclient stream.

        Args:
            messages (sseclient.event.data): The json messages returned from the streaming client.

        Returns:
            num_metrics (int): The number of metrics received.
        """

        num_metrics = 0
        try:
            json_data = json.loads(messages)
        except ValueError:
            LOGGER.error(f'Failed to parse event: {messages}')
            raise

        try:
            for metric in json_data['metrics']['messages']:
                num_metrics += 1
                context = metric['Context']
                events = metric['Events']
                for event in events:
                    sensors = event['Oem']['Sensors']
                    self.set_sensors_for_context(context, sensors)

                # break if got the data already
                if self.am_i_done():
                    break
        except KeyError as err:
            LOGGER.error(f'Failed to unpack messages received from sseclient due to missing key(s) '
                         f'in messages: {err}')
            raise

        return num_metrics

    def check_if_run_done(self, topic):
        """Checks if the thread run should stop.

        Args:
            topic (str): The name of the Kafka telemetry topic.

        Returns:
           True if thread run should stop and otherwise False.
        """

        if self.stopped():
            LOGGER.debug(f'The stop_event is set. Stopping thread for {topic}')
            return True

        done = self.results.get('Done')
        if done:
            return True

        if self.am_i_done():
            print(f'Telemetry data received from {topic} for all requested xnames.')
            self.results['Done'] = True
            return True

        return False

    def ping_and_sleep(self, topic):
        """Ping the Telemetry API service until alive with sleep in between.

        Args:
            topic (str): The name of the Kafka telemetry topic.

        Returns:
           True or False if alive or not for RECONNECT_RETRIES.
        """

        alive = False
        while not alive and not self.stopped() and self.retries < self.RECONNECT_RETRIES:
            self.retries += 1
            alive = self.endpoint_alive()
            if not alive:
                time.sleep(self.RECONNECT_DELAY_SECS)

        if not alive and self.retries == self.RECONNECT_RETRIES:
            self.results['APIError'] = True
            LOGGER.error(f'Exceeded number of retries: '
                         f'{self.RECONNECT_RETRIES} for {topic}')

        return alive

    def run(self):
        """Create a Telemetry API message consumer and consume messages for a list of xnames.
        """

        LOGGER.debug(f'Thread starting at {datetime.datetime.now()}')

        total_metrics = 0
        topic = self.results.get('Topic')
        while not self.check_if_run_done(topic):
            try:
                response = self.api_client.stream(topic, self.GET_TIMEOUT_SECS,
                                                  params={'count': 0, 'batchsize': self.batchsize})
                client = sseclient.SSEClient(response)
                print(f'Waiting for metrics for all requested xnames from {topic}.')
                for event in client.events():
                    num_metrics = self.unpack_data(event.data)
                    total_metrics += num_metrics
                    LOGGER.info(f'Received {total_metrics} metrics from stream: {event.event}')
                    print(f'Receiving metrics from stream: {event.event}...')
                    if self.am_i_done() or self.stopped():
                        break

            except APIError as err:
                self.results['APIError'] = True
                LOGGER.error(f'Request to Telemetry API failed: {err}')
                break

            except ReadTimeout:
                print(f'Timed out getting any data from {topic}.')
                self.results['Done'] = True
                break

            except Exception as err:
                LOGGER.error(f'Telemetry API exception: {err}')
                if not self.ping_and_sleep(topic):
                    break
                LOGGER.debug(f'Attempting Telemetry API reconnect for {topic}')

        msg_info = ''
        if self.stopped():
            msg_info = ' due to stop_event'
        LOGGER.debug(f'Thread stopping{msg_info} for {topic}')
