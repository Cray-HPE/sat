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


LOGGER = logging.getLogger(__name__)


class TelemetryClient(threading.Thread):
    """A thread that collects telemetry data using the SMA Telemetry API."""

    # Default timeout for the telemetry streaming API
    GET_TIMEOUT_SECS = 60

    # Time to sleep in between telemetry API reconnect attempts
    RECONNECT_DELAY_SECS = 10

    # Number of times to try to reconnect
    RECONNECT_RETRIES = 3

    def __init__(self, stop_event, xnames_info, batchsize, topic, results, results_index):
        """Create a thread to connect to streaming telemetry API.

        Args:
            stop_event (threading.Event): Event object used to stop all threads.
            xnames_info ([dict]): A list of dictionaries with xname and Type.
            batchsize (int): The number of metrics to include in each message from API.
            topic (str): The name of the Kafka telemetry topic.
            results ([dict]): A list of dictionaries with temeletry results for all topics.
            results_index (int): The index into the results list for this thread.
        """

        super().__init__()
        self.stop_event = stop_event
        self.batchsize = batchsize

        # initialize the results for this thread
        metrics = []
        for xname_info in xnames_info:
            metrics.append(
                {'Context': xname_info['xname'],
                 'Type': xname_info['Type'],
                 'Count': 0,
                 'Sensors': []}
            )
        results[results_index] = {
            'Topic': topic,
            'Done': False,
            'Metrics': metrics
        }
        self.results = results
        self.results_index = results_index
        self.api_client = TelemetryAPIClient(SATSession())

    def get_topic(self):
        """Get the Kafka topic being consumed using this thread.

        Returns:
           A topic name string or None.
        """

        return self.results[self.results_index].get('Topic')

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

    def set_sensors_for_context(self, context, sensors):
        """Set the sensors data in the thread results for a particular context.

        Args:
            context (str): The Context (xname) of the sensor data.
            sensors ([dict]): A list of dictionaries with sensor data for the xname.

        Returns:
           True if successful and otherwise False.
        """

        metrics = self.results[self.results_index].get('Metrics')
        for metric in metrics:
            try:
                if metric['Context'] == context:
                    metric['Count'] += 1
                    metric['Sensors'] = sensors
                    return True
            except KeyError as err:
                LOGGER.error(f'Failed to parse telemetry results: {err}')
                raise

        return False

    def am_i_done(self):
        """Checks if the thread is done getting data for all xnames and topics requested.

        Returns:
           True if all done and otherwise False.
        """

        metrics = self.results[self.results_index].get('Metrics')
        for metric in metrics:
            try:
                if metric['Count'] == 0:
                    return False
            except KeyError as err:
                LOGGER.error(f'Failed to parse telemetry results: {err}')
                raise

        return True

    def unpack_data(self, messages):
        """Unpack data returned from the sseclient stream.

        Args:
            messages (sseclient.event.data): The json messages returned from the streaming client.

        Returns:
            num_metrics (int): The number of metrics received.
            all_done (bool): True if data has been received for all xnames.
        """

        num_metrics = 0
        all_done = False
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
                    all_done = True
                    break
        except KeyError as err:
            LOGGER.error(f'Failed to parse metrics received from Telemetry API: {err}')
            raise

        return num_metrics, all_done

    def run(self):
        """Create a Telemetry API message consumer and consume messages for a list of xnames.
        """

        LOGGER.debug(f'Thread starting at {datetime.datetime.now()}')

        total_metrics = 0
        retries = 0
        topic = self.results[self.results_index].get('Topic')
        while True and topic and not self.stopped() and not self.results[self.results_index]['Done']:
            try:
                response = self.api_client.stream(topic, self.GET_TIMEOUT_SECS,
                                                  params={'count': 0, 'batchsize': self.batchsize})
                client = sseclient.SSEClient(response)
                print(f'Waiting for metrics for all requested xnames from {topic}.')
                for event in client.events():
                    num_metrics, all_done = self.unpack_data(event.data)
                    total_metrics += num_metrics
                    LOGGER.info(f'Received {total_metrics} metrics from stream: {event.event}')
                    print(f'Receiving metrics from stream: {event.event}...')

                    if all_done or self.stopped():
                        if all_done:
                            print(f'Telemetry data received from {topic} for all requested xnames.')
                            self.results[self.results_index]['Done'] = True
                        elif self.stopped():
                            LOGGER.debug(f'The stop_event is set. Stopping thread for {topic}')
                        break

            except APIError as err:
                LOGGER.error(f'Request to Telemetry API failed: {err}')
                break

            except ReadTimeout:
                print(f'Timed out getting any data from {topic}.')
                self.results[self.results_index]['Done'] = True
                break

            except Exception as err:
                LOGGER.error(f'Telemetry API exception: {err}')
                if retries >= self.RECONNECT_RETRIES:
                    LOGGER.debug(f'Exceeded number of retries: {self.RECONNECT_RETRIES} for {topic}')
                    break

                if not self.stopped():
                    retries += 1
                    alive = self.endpoint_alive()
                    while not alive and not self.stopped() and retries < self.RECONNECT_RETRIES:
                        time.sleep(self.RECONNECT_DELAY_SECS)
                        alive = self.endpoint_alive()
                        if not alive:
                            retries += 1
                    if self.stopped():
                        break

                    if alive:
                        LOGGER.debug(f'Attempting Telemetry API reconnect for {topic}')
                    else:
                        LOGGER.debug(f'Exceeded number of retries: {self.RECONNECT_RETRIES} for {topic}')
                        break

        msg_info = ''
        if self.stopped():
            msg_info = ' due to stop_event'
        LOGGER.debug(f'Thread stopping{msg_info} for {topic}')
