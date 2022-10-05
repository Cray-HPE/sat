#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Unit tests for sat.apiclient.fabric
"""

import logging
import unittest
from unittest import mock

from sat.apiclient import APIError, APIGatewayClient, FabricControllerClient
from tests.common import ExtendedTestCase


class TestFabricControllerClient(ExtendedTestCase):
    """Tests for the APIGatewayClient class: Fabric Controller client."""

    def setUp(self):
        self.mock_port_sets = {
            'fabric-ports': {'ports': ['x3000c0r24j4p0', 'x3000c0r24j4p1']},
            'edge-ports': {'ports': ['x3000c0r24j8p0', 'x3000c0r24j8p1']}
        }
        self.mock_port_set_status = {
            'fabric-ports': {
                'ports': [
                    {'xname': 'x3000c0r24j4p0', 'status': {'enable': True}},
                    {'xname': 'x3000c0r24j4p1', 'status': {'enable': False}}
                ]
            },
            'edge-ports': {
                'ports': [
                    {'xname': 'x3000c0r24j8p0', 'status': {'enable': True}},
                    {'xname': 'x3000c0r24j8p1', 'status': {'enable': False}}
                ]
            }
        }

        self.json_value_err = False
        self.get_api_err = False

        def mock_fc_get(_, *args):
            mock_response = mock.Mock()
            if self.get_api_err:
                raise APIError("simulated failure")
            elif self.json_value_err:
                mock_response.json.side_effect = ValueError('simulated json parse error')
            elif len(args) == 2 and args[0] == 'port-sets':
                # This should give a description of the port set
                mock_response.json.return_value = self.mock_port_sets[args[1]]
            elif len(args) == 3 and args[0] == 'port-sets' and args[-1] == 'status':
                # This should give the status of the port set
                mock_response.json.return_value = self.mock_port_set_status[args[1]]
            else:
                raise AssertionError(f'Unexpected args received by get method: {args}')
            return mock_response

        self.mock_fc_get = mock.patch.object(APIGatewayClient, 'get', mock_fc_get).start()

        self.mock_session = mock.MagicMock()
        self.fabric_client = FabricControllerClient(self.mock_session)

        self.fabric_status_fail_msg = 'Failed to get port status for port set fabric-ports'
        self.edge_status_fail_msg = 'Failed to get port status for port set edge-ports'

    def tearDown(self):
        mock.patch.stopall()

    def test_get_fabric_edge_ports(self):
        """Test getting all fabric and edge ports."""
        expected = {
            'fabric-ports': ['x3000c0r24j4p0', 'x3000c0r24j4p1'],
            'edge-ports': ['x3000c0r24j8p0', 'x3000c0r24j8p1']
        }
        actual = self.fabric_client.get_fabric_edge_ports()
        self.assertEqual(expected, actual)

    def test_get_fabric_edge_ports_api_error(self):
        """Test getting all fabric and edge ports when there is an APIError."""
        self.get_api_err = True
        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element('Failed to get ports for port set', cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_bad_json(self):
        """Test getting all fabric and edge ports when the response JSON cannot be parsed."""
        self.json_value_err = True
        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element('Failed to parse response', cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_missing_key(self):
        """Test getting all fabric and edge ports when there is a missing 'ports' key."""
        del self.mock_port_sets['fabric-ports']['ports']
        expected = {
            'edge-ports': ['x3000c0r24j8p0', 'x3000c0r24j8p1']
        }

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports()
        self.assertEqual(1, len(cm.output))
        self.assert_in_element("Response from fabric controller API was missing "
                               "the 'ports' key", cm.output)
        self.assertEqual(expected, actual)

    def test_get_fabric_edge_ports_status(self):
        """Test getting enabled status of fabric and edge ports."""
        expected = {
            'fabric-ports': {'x3000c0r24j4p0': True, 'x3000c0r24j4p1': False},
            'edge-ports': {'x3000c0r24j8p0': True, 'x3000c0r24j8p1': False}
        }
        actual = self.fabric_client.get_fabric_edge_ports_enabled_status()
        self.assertEqual(expected, actual)

    def test_get_fabric_edge_ports_status_api_error(self):
        """Test getting enabled status of fabric and edge ports w/ APIError."""
        self.get_api_err = True

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports_enabled_status()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element(self.fabric_status_fail_msg, cm.output)
        self.assert_in_element(self.edge_status_fail_msg, cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_status_bad_json(self):
        """Test getting enabled status of fabric and edge ports w/ JSON parse error."""
        self.json_value_err = True

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports_enabled_status()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element(self.fabric_status_fail_msg, cm.output)
        self.assert_in_element(self.edge_status_fail_msg, cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_status_missing_key(self):
        """Test getting enabled status of fabric and edge ports w/ missing 'ports' key."""
        del self.mock_port_set_status['fabric-ports']['ports']
        expected = {
            'edge-ports': {'x3000c0r24j8p0': True, 'x3000c0r24j8p1': False}
        }

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports_enabled_status()

        self.assertEqual(1, len(cm.output))
        self.assert_in_element(self.fabric_status_fail_msg, cm.output)
        self.assertEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
