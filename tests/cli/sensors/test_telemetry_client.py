"""
Unit tests for sat.cli.sensors.telemetry_client

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

import json
import unittest
from threading import Event
from unittest import mock

from sat.cli.sensors.telemetry_client import (
    TelemetryClient
)


class TestTelemetryClient(unittest.TestCase):
    """Unit test for the TelemetryClient class."""

    def setUp(self):
        """Mock functions called."""

        self.mock_api_client = mock.Mock()
        mock.patch('sat.cli.sensors.telemetry_client.TelemetryAPIClient',
                   return_value=self.mock_api_client).start()
        mock.patch('sat.cli.sensors.telemetry_client.SATSession').start()

        self.mock_api_client.ping.return_value = True

        self.stop_event = Event()
        self.xnames_info = [{'xname': 'x3000c0r22b0', 'Type': 'RouterBMC'},
                            {'xname': 'x3000c0s17b3', 'Type': 'NodeBMC'}]
        self.batchsize = 8
        self.topic = 'cray-telemetry-temperature'
        self.xname_with_data = 'x3000c0s17b3'
        self.temperature_sensors_results = [
            {
                'Timestamp': '2021-04-16T21:20:53Z',
                'Location': 'x3000c0s17b3',
                'ParentalContext': 'Chassis',
                'PhysicalContext': 'Baseboard',
                'Index': 0,
                'DeviceSpecificContext': 'BB Inlet Temp',
                'Value': '22'
            },
            {
                'Timestamp': '2021-04-16T21:20:53Z',
                'Location': 'x3000c0s17b3',
                'ParentalContext': 'Chassis',
                'PhysicalContext': 'Baseboard',
                'Index': 0,
                'DeviceSpecificContext': 'BB BMC Temp',
                'Value': '26'
            }
        ]
        self.event_data = {
            'metrics': {
                'messages': [
                    {
                        'Context': 'x3000c0s17b3',
                        'Events': [
                            {
                                'EventTimestamp': '2021-04-16T21:20:53Z',
                                'MessageId': 'CrayTelemetry.Temperature',
                                'Oem':
                                    {
                                        'Sensors': self.temperature_sensors_results,
                                        'TelemetrySource': 'cC'
                                    }
                            }
                        ]
                    }
                ]
            }
        }

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_init(self):
        """Test creation of a TelemetryClient."""
        all_topics_results = [None, None]
        temperature_init_results = {
            'Topic': self.topic,
            'Done': False,
            'APIError': False,
            'Metrics': [
                {
                    'Context': xname_info['xname'],
                    'Type': xname_info['Type'],
                    'Count': 0,
                    'Sensors': []
                } for xname_info in self.xnames_info
            ]
        }
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertEqual(self.stop_event, telemetry_client.stop_event)
        self.assertEqual(self.batchsize, telemetry_client.batchsize)
        self.assertEqual(all_topics_results[0], temperature_init_results)
        self.assertEqual(all_topics_results[1], None)

    def test_stop(self):
        """Test stop of a TelemetryClient."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertFalse(telemetry_client.stopped())
        telemetry_client.stop()
        self.assertTrue(telemetry_client.stopped())

    def test_get_topic(self):
        """Test get_topic of a TelemetryClient."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertEqual(self.topic, telemetry_client.get_topic())

    def test_endpoint_alive(self):
        """Test endpoint_alive of a TelemetryClient."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertTrue(telemetry_client.endpoint_alive())

    def test_set_sensors_for_context(self):
        """Test set_sensors_for_context of a TelemetryClient."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertTrue(telemetry_client.set_sensors_for_context(
                        self.xname_with_data, self.temperature_sensors_results))
        xname_results = all_topics_results[0]['Metrics'][1]
        self.assertEqual(xname_results['Context'], self.xname_with_data)
        self.assertEqual(xname_results['Type'], 'NodeBMC')
        self.assertEqual(xname_results['Count'], 1)
        self.assertEqual(xname_results['Sensors'], self.temperature_sensors_results)

    def test_am_i_done(self):
        """Test am_i_done of a TelemetryClient."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertFalse(telemetry_client.am_i_done())

    def test_unpack_data(self):
        """Test unpack_data of a TelemetryClient."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)

        num_metrics = telemetry_client.unpack_data(json.dumps(self.event_data))
        self.assertEqual(num_metrics, 1)
        self.assertFalse(telemetry_client.am_i_done())
        xname_results = all_topics_results[0]['Metrics'][1]
        self.assertEqual(xname_results['Context'], self.xname_with_data)
        self.assertEqual(xname_results['Type'], 'NodeBMC')
        self.assertEqual(xname_results['Count'], 1)
        self.assertEqual(xname_results['Sensors'], self.temperature_sensors_results)

    def test_check_if_run_done_when_stopped(self):
        """Test check_if_run_done of a TelemetryClient that is stopped."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertFalse(telemetry_client.check_if_run_done(self.topic))
        telemetry_client.stop()
        self.assertTrue(telemetry_client.check_if_run_done(self.topic))

    def test_ping_and_sleep(self):
        """Test ping_and_sleep of a TelemetryClient."""
        all_topics_results = [None]
        telemetry_client = TelemetryClient(self.stop_event, self.xnames_info, self.batchsize,
                                           self.topic, all_topics_results, 0)
        self.assertTrue(telemetry_client.ping_and_sleep(self.topic))


if __name__ == '__main__':
    unittest.main()
