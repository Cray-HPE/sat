"""
Unit tests for sat.cli.switch

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

import unittest
from unittest import mock
from argparse import Namespace
import json
from sat.apiclient import APIError
from sat.xname import XName
import sat.cli.switch.main


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.xname = 'x1000c6r7'
    namespace.save_portset = False
    namespace.finish = False
    namespace.disruptive = False


class TestDoSwitch(unittest.TestCase):
    """Unit test for Switch do_switch()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.SATSession').start()

        self.mock_get_switch_ports = mock.patch('sat.cli.switch.main.get_switch_ports',
                                                autospec=True).start()
        self.mock_get_switch_ports.return_value = ['x1000c6r7j101p0', 'x1000c6r7j101p1',
                                                   'x1000c6r7j2p0', 'x1000c6r7j2p1']

        self.mock_output_json = mock.patch('sat.cli.switch.main.output_json',
                                           autospec=True).start()

        self.mock_get_port_sets = mock.patch('sat.cli.switch.main.get_port_sets',
                                             autospec=True).start()

        self.mock_create_port_set = mock.patch('sat.cli.switch.main.create_port_set',
                                               autospec=True).start()

        self.mock_update_port_set = mock.patch('sat.cli.switch.main.update_port_set',
                                               autospec=True).start()

        self.mock_get_port_set_config = mock.patch('sat.cli.switch.main.get_port_set_config',
                                                   autospec=True).start()
        self.mock_get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'}
            ]
        }

        self.mock_delete_port_set = mock.patch('sat.cli.switch.main.delete_port_set',
                                               autospec=True).start()

        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.parsed = Namespace()
        set_options(self.parsed)

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: do_switch() basic"""
        sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_called_once()
        self.mock_create_port_set.assert_called()
        self.mock_get_port_set_config.assert_called_once()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_called()
        self.mock_print.assert_called_once()

    def test_save_port_set_file(self):
        """Test Switch: do_switch() save port set file"""
        self.parsed.save_portset = True
        sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_called_once()
        self.mock_get_port_sets.assert_called_once()
        self.mock_create_port_set.assert_called()
        self.mock_get_port_set_config.assert_called_once()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_called()
        self.mock_print.assert_called_once()

    def test_save_port_set_file(self):
        """Test Switch: do_switch() save port set file"""
        sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_called_once()
        self.mock_create_port_set.assert_called()
        self.mock_get_port_set_config.assert_called_once()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_called()
        self.mock_print.assert_called_once()

    def test_finish(self):
        """Test Switch: do_switch() finish"""
        self.parsed.disruptive = True
        self.parsed.finish = True
        sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_get_port_sets.assert_called_once()
        self.mock_create_port_set.assert_called()
        self.mock_get_port_set_config.assert_called_once()
        self.mock_update_port_set.assert_called()
        self.mock_delete_port_set.assert_called()
        self.mock_print.assert_called_once()

    def test_get_ports_error(self):
        """Test Switch: do_switch() error getting ports"""
        self.mock_get_switch_ports.return_value = None
        with self.assertRaises(SystemExit):
            sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_not_called()
        self.mock_create_port_set.assert_not_called()
        self.mock_get_port_set_config.assert_not_called()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_not_called()
        self.mock_print.assert_not_called()

    def test_update_port_set_error(self):
        """Test Switch: do_switch() error updating port set configuration"""
        self.parsed.disruptive = True
        self.mock_update_port_set.return_value = None
        with self.assertRaises(SystemExit):
            sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_called()
        self.mock_create_port_set.assert_called()
        self.mock_get_port_set_config.assert_called()
        self.mock_update_port_set.assert_called()
        self.mock_delete_port_set.assert_called()
        self.mock_print.assert_not_called()

    def test_no_switch_ports(self):
        """Test Switch: do_switch() no switch ports"""
        self.mock_get_switch_ports.return_value = []
        with self.assertLogs(level='ERROR'):
            with self.assertRaises(SystemExit):
                sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_not_called()
        self.mock_create_port_set.assert_not_called()
        self.mock_get_port_set_config.assert_not_called()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_set_switch_exists(self):
        """Test Switch: do_switch() port set for switch already exists"""
        self.mock_get_port_sets.return_value = {'names': ['SAT-x1000c6r7']}
        with self.assertLogs(level='ERROR'):
            with self.assertRaises(SystemExit):
                sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_called_once()
        self.mock_create_port_set.assert_not_called()
        self.mock_get_port_set_config.assert_not_called()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_set_port_exists(self):
        """Test Switch: do_switch() port set for port already exists"""
        self.mock_get_port_sets.return_value = {'names': ['SAT-x1000c6r7j101p0']}
        with self.assertLogs(level='ERROR'):
            with self.assertRaises(SystemExit):
                sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_called_once()
        self.mock_create_port_set.assert_not_called()
        self.mock_get_port_set_config.assert_not_called()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_not_called()
        self.mock_print.assert_not_called()

    def test_port_config_missing(self):
        """Test Switch: do_switch() port set for port already exists"""
        self.mock_get_port_set_config.return_value = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'}
            ]
        }
        with self.assertLogs(level='ERROR'):
            with self.assertRaises(SystemExit):
                sat.cli.switch.main.do_switch(self.parsed)
        self.mock_get_switch_ports.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_get_port_sets.assert_called_once()
        self.mock_create_port_set.assert_called()
        self.mock_get_port_set_config.assert_called()
        self.mock_update_port_set.assert_not_called()
        self.mock_delete_port_set.assert_called()
        self.mock_print.assert_not_called()

class TestOutputJson(unittest.TestCase):
    """Unit test for Switch output_json()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_json_dump = mock.patch('json.dump', autospec=True).start()
        self.mock_open = mock.patch('builtins.open', autospec=True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: output_json() basic"""
        sat.cli.switch.main.output_json({}, 'filepath')
        self.mock_open.assert_called_once()
        self.mock_json_dump.assert_called_once()

    def test_api_error(self):
        """Test Switch: output_json() OSError"""
        self.mock_open.side_effect = OSError
        with self.assertLogs(level='ERROR'):
            sat.cli.switch.main.output_json({}, 'filepath')

class TestGetSwitchPorts(unittest.TestCase):
    """Unit test for Switch get_switch_ports()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.SATSession').start()

        # If a test wishes to  change the mock_fc_data, the test can do something like:
        #     self.mock_fc_response.json.return_value = {'foo': 'bar'}

        # The data that will be returned by the firmware response's JSON method
        self.mock_fc_data = {
            'links': [
                {'endpoint1': 'x1000c6r3j24p1', 'endpoint2': 'x1000c6r7j24p1'},
                {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
                {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
                {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'}
            ],
            'ports': {
                'edge': [
                 'x3000c0r24j4p0', 'x3000c0r24j4p1', 'x3000c0r24j8p0',
                 'x1000c6r7j100p0', 'x1000c6r7j100p1',
                 'x1000c6r7j101p0', 'x1000c6r7j101p1',
                 'x1000c6r7j102p0', 'x1000c6r7j102p1',
                 'x1000c6r7j103p0', 'x1000c6r7j103p1',
                 'x1000c3r7j103p0', 'x1000c3r7j103p1', 'x1000c3r7j101p1'
                ],
                'fabric': [
                    'x3000c0r24j31p1', 'x3000c0r24j31p0', 'x3000c0r24j1p1',
                    'x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0',
                    'x1000c6r7j6p1', 'x1000c6r7j6p0',
                    'x1000c3r7j4p1', 'x1000c3r7j4p0', 'x1000c3r7j6p1'
                ]
            }
        }

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = self.mock_fc_data
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.get.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

    def test_basic(self):
        """Test Switch: get_switch_ports() basic"""
        result = sat.cli.switch.main.get_switch_ports('x1000c6r7')
        expected = ['x1000c6r7j100p0', 'x1000c6r7j100p1',
                    'x1000c6r7j101p0', 'x1000c6r7j101p1',
                    'x1000c6r7j102p0', 'x1000c6r7j102p1',
                    'x1000c6r7j103p0', 'x1000c6r7j103p1',
                    'x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0',
                    'x1000c6r7j6p1', 'x1000c6r7j6p0']
        self.assertEqual(result, expected)

    def test_only_fabric(self):
        """Test Switch: get_switch_ports() only fabric ports"""
        self.mock_fc_response.json.return_value = {
            'links': [
                {'endpoint1': 'x1000c6r3j24p1', 'endpoint2': 'x1000c6r7j24p1'},
                {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
                {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
                {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'}
            ],
            'ports': {
                'fabric': [
                    'x3000c0r24j31p1', 'x3000c0r24j31p0', 'x3000c0r24j1p1',
                    'x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0',
                    'x1000c6r7j6p1', 'x1000c6r7j6p0',
                    'x1000c3r7j4p1', 'x1000c3r7j4p0', 'x1000c3r7j6p1'
                ]
            }
        }
        result = sat.cli.switch.main.get_switch_ports('x1000c6r7')
        expected = ['x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0',
                    'x1000c6r7j6p1', 'x1000c6r7j6p0']
        self.assertEqual(result, expected)

    def test_only_edge(self):
        """Test Switch: get_switch_ports() only edge ports"""
        self.mock_fc_response.json.return_value = {
            'links': [
                {'endpoint1': 'x1000c6r3j24p1', 'endpoint2': 'x1000c6r7j24p1'},
                {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
                {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
                {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'}
            ],
            'ports': {
                'edge': [
                 'x3000c0r24j4p0', 'x3000c0r24j4p1', 'x3000c0r24j8p0',
                 'x1000c6r7j100p0', 'x1000c6r7j100p1',
                 'x1000c6r7j101p0', 'x1000c6r7j101p1',
                 'x1000c6r7j102p0', 'x1000c6r7j102p1',
                 'x1000c6r7j103p0', 'x1000c6r7j103p1',
                 'x1000c3r7j103p0', 'x1000c3r7j103p1', 'x1000c3r7j101p1'
                ]
            }
        }
        result = sat.cli.switch.main.get_switch_ports('x1000c6r7')
        expected = ['x1000c6r7j100p0', 'x1000c6r7j100p1',
                    'x1000c6r7j101p0', 'x1000c6r7j101p1',
                    'x1000c6r7j102p0', 'x1000c6r7j102p1',
                    'x1000c6r7j103p0', 'x1000c6r7j103p1']
        self.assertEqual(result, expected)

    def test_api_error(self):
        """Test Switch: get_switch_ports() APIError"""
        self.mock_fc_client.get.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_switch_ports('x1000c6r7')
        self.assertEqual(result, None)

    def test_value_error(self):
        """Test Switch: get_switch_ports() ValueError"""
        self.mock_fc_response.json.side_effect = ValueError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_switch_ports('x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_ports_key(self):
        """Test Switch: get_switch_ports() missing ports key"""
        self.mock_fc_response.json.return_value = {
            'links': [
                {'endpoint1': 'x1000c6r3j24p1', 'endpoint2': 'x1000c6r7j24p1'},
                {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
                {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
                {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'}
            ]}
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_switch_ports('x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_fabric_edge_keys(self):
        """Test Switch: get_switch_ports() missing fabric and edge keys"""
        self.mock_fc_response.json.return_value = {
            'links': [
                {'endpoint1': 'x1000c6r3j24p1', 'endpoint2': 'x1000c6r7j24p1'},
                {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
                {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
                {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'}
            ],
            'ports': {}
            }
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_switch_ports('x1000c6r7')
        self.assertEqual(result, None)

    def tearDown(self):
        mock.patch.stopall()


class TestCreatePortSet(unittest.TestCase):
    """Unit test for Switch create_port_set()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.SATSession').start()

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = {}
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.post.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

        self.mock_json_dumps = mock.patch('json.dumps', autospec=True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: create_port_set() basic"""
        portset = {'name': 'SAT-switch', 'ports': []}
        result = sat.cli.switch.main.create_port_set(portset)
        self.mock_json_dumps.assert_called_once()
        self.mock_fc_client.post.assert_called_once()
        self.assertEqual(result, True)

    def test_api_error(self):
        """Test Switch: create_port_set() APIError"""
        self.mock_fc_client.post.side_effect = APIError
        portset = {'name': 'SAT-switch', 'ports': []}
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.create_port_set(portset)
        self.assertEqual(result, False)

class TestGetPortSets(unittest.TestCase):
    """Unit test for Switch get_port_sets()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.SATSession').start()

        # If a test wishes to  change the mock_fc_data, the test can do something like:
        #     self.mock_fc_response.json.return_value = {'foo': 'bar'}

        # The data that will be returned by the firmware response's JSON method
        self.mock_fc_data = {'names': ['fabric-ports', 'edge-ports']}

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = self.mock_fc_data
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.get.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: get_port_sets() basic"""
        result = sat.cli.switch.main.get_port_sets()
        self.assertEqual(result, self.mock_fc_data)

    def test_api_error(self):
        """Test Switch: get_port_sets() APIError"""
        self.mock_fc_client.get.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_port_sets()
        self.assertEqual(result, None)

    def test_value_error(self):
        """Test Switch: get_port_sets() ValueError"""
        self.mock_fc_response.json.side_effect = ValueError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_port_sets()
        self.assertEqual(result, None)


class TestGetPortSetConfig(unittest.TestCase):
    """Unit test for Switch get_port_set_config()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.SATSession').start()

        # If a test wishes to  change the mock_fc_data, the test can do something like:
        #     self.mock_fc_response.json.return_value = {'foo': 'bar'}

        # The data that will be returned by the firmware response's JSON method
        self.mock_fc_data = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j101p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j102p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j102p1'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '200'},
                 'xname': 'x1000c6r7j2p1'}
            ]
        }

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = self.mock_fc_data
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.get.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: get_port_set_config() basic"""
        result = sat.cli.switch.main.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, self.mock_fc_data)

    def test_api_error(self):
        """Test Switch: get_port_set_config() APIError"""
        self.mock_fc_client.get.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)

    def test_value_error(self):
        """Test Switch: get_port_set_config() ValueError"""
        self.mock_fc_response.json.side_effect = ValueError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_ports_key(self):
        """Test Switch: get_port_set_config() missing ports key"""
        self.mock_fc_response.json.return_value = {
            'docks': [{'config': {'ship-size': 'super-tanker'}}]}
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_config_key(self):
        """Test Switch: get_port_set_config() missing config key"""
        self.mock_fc_response.json.return_value = {
            'ports': [{'Perth': {'hemisphere': 'southern'}}]}
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)


class TestUpdatePortSet(unittest.TestCase):
    """Unit test for Switch update_port_set()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.SATSession').start()

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = {}
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.put.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_enable(self):
        """Test Switch: update_port_set() enable"""
        port_config = {'autoneg': True, 'enable': True,
                       'flowControl': {'rx': True, 'tx': True}, 'speed': 100}
        result = sat.cli.switch.main.update_port_set('SAT-port', port_config, True)
        self.mock_fc_client.put.assert_called_once()
        self.assertEqual(result, True)

    def test_disable(self):
        """Test Switch: update_port_set() disable"""
        port_config = {'autoneg': True, 'enable': True,
                       'flowControl': {'rx': True, 'tx': True}, 'speed': 100}
        result = sat.cli.switch.main.update_port_set('SAT-port', port_config, False)
        self.mock_fc_client.put.assert_called_once()
        self.assertEqual(result, True)

    def test_api_error(self):
        """Test Switch: update_port_set() APIError"""
        port_config = {'autoneg': True, 'enable': True,
                       'flowControl': {'rx': True, 'tx': True}, 'speed': 100}
        self.mock_fc_client.put.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.update_port_set('SAT-switch', port_config, True)
        self.assertEqual(result, False)


class TestDeletePortSet(unittest.TestCase):
    """Unit test for Switch delete_port_set()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.SATSession').start()

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = {}
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.delete.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.switch.main.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: delete_port_set() basic"""
        result = sat.cli.switch.main.delete_port_set('SAT-switch')
        self.mock_fc_client.delete.assert_called_once()
        self.assertEqual(result, True)

    def test_api_error(self):
        """Test Switch: delete_port_set() APIError"""
        self.mock_fc_client.delete.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = sat.cli.switch.main.delete_port_set('SAT-switch')
        self.assertEqual(result, False)


if __name__ == '__main__':
    unittest.main()
