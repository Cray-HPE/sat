"""
Unit tests for sat.cli.swap.ports

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
import unittest
from unittest import mock

from sat.cli.swap.ports import PortManager
from tests.common import ExtendedTestCase


class TestGetSwitchPortDataList(unittest.TestCase):
    """Unit test for Switch get_switch_port_data_list()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

        # If a test wishes to  change the mock_fc_data, the test can do something like:
        #     self.mock_fc_response.json.return_value = {'foo': 'bar'}

        # The data that will be returned for a port
        # Example: https://api-gw-service-nmn.local/apis/fabric-manager/fabric/ports/x1000c6r7j100p0
        self.mock_fc_data = {
            'id': 'x1000c6r7a0l13',
            'conn_port': 'x1000c6r7j100p0',
            'portPolicyLinks': [
                '/fabric/port-policies/edge-policy'
            ]
        }

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = self.mock_fc_data
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.get.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

        self.mock_get_switches = mock.patch('sat.cli.swap.ports.PortManager.get_switches',
                                            autospec=True).start()
        self.mock_get_switches.return_value = [
            '/fabric/switches/x1000c6r7b0',
            '/fabric/switches/x1000c0r7b1'
        ]

        self.mock_get_switch = mock.patch('sat.cli.swap.ports.PortManager.get_switch',
                                          autospec=True).start()
        self.mock_get_switch.return_value = {
            'edgePortLinks': [
                '/fabric/ports/x1000c6r7j100p0'
            ],
            'fabricPortLinks': []
        }
        self.pm = PortManager()

    def test_basic(self):
        """Test Switch: get_switch_port_data_list() basic"""

        result = self.pm.get_switch_port_data_list('x1000c6r7')
        expected = [{'xname': 'x1000c6r7j100p0',
                     'port_link': '/fabric/ports/x1000c6r7j100p0',
                     'policy_link': '/fabric/port-policies/edge-policy'}]
        self.assertEqual(result, expected)

    def tearDown(self):
        mock.patch.stopall()


class TestCreateOfflinePortPolicy(ExtendedTestCase):
    """Unit test for Switch create_offline_port_policy()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = {}
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.post.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

        self.mock_get_port_policies = mock.patch('sat.cli.swap.ports.PortManager.get_port_policies',
                                                 autospec=True).start()
        self.mock_get_port_policies.return_value = [
            '/fabric/port-policies/fabric-policy',
            '/fabric/port-policies/edge-policy',
            '/fabric/port-policies/sat-offline-edge-policy'
        ]

        self.mock_json_dumps = mock.patch('json.dumps', autospec=True).start()
        self.pm = PortManager()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test create_offline_port_policy() that already exists"""
        with self.assertLogs(level=logging.INFO) as logs:
            self.pm.create_offline_port_policy('/fabric/port-policies/edge-policy', 'sat-offline-')
        self.assert_in_element('Using existing offline policy: /fabric/port-policies/sat-offline-edge-policy',
                               logs.output)

    def test_new_policy(self):
        """Test create_offline_port_policy() that doesn't already exist"""
        with self.assertLogs(level=logging.DEBUG) as logs:
            self.pm.create_offline_port_policy('/fabric/port-policies/fabric-policy', 'sat-offline-')
        self.assert_in_element('Creating offline policy: /fabric/port-policies/sat-offline-fabric-policy',
                               logs.output)


if __name__ == '__main__':
    unittest.main()
