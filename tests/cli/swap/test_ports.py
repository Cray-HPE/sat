"""
Unit tests for sat.cli.swap.ports

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
from unittest import mock

from sat.apiclient import APIError
from sat.cli.swap.ports import PortManager


class TestGetSwitchPorts(unittest.TestCase):
    """Unit test for Switch get_switch_ports()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

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
                    'x3000c0r7j4p0', 'x3000c0r7j4p1', 'x3000c0r7j8p0', 'x1000c6r7j100p0', 'x1000c6r7j100p1',
                    'x1000c6r7j10p0', 'x1000c6r7j10p1', 'x1000c6r7j102p0', 'x1000c6r7j102p1', 'x1000c6r7j103p0',
                    'x1000c6r7j103p1', 'x1000c3r7j103p0', 'x1000c3r7j103p1', 'x1000c3r7j10p1'
                ],
                'fabric': [
                    'x3000c0r7j31p1', 'x3000c0r7j31p0', 'x3000c0r7j1p1', 'x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0', 'x1000c6r7j6p1', 'x1000c6r7j6p0', 'x1000c3r7j4p1',
                    'x1000c3r7j4p0', 'x1000c3r7j6p1'
                ]
            }
        }

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = self.mock_fc_data
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.get.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()
        self.pm = PortManager()

    def test_basic(self):
        """Test Switch: get_switch_ports() basic"""
        result = self.pm.get_switch_ports('x1000c6r7')
        expected = ['x1000c6r7j100p0', 'x1000c6r7j100p1',
                    'x1000c6r7j10p0', 'x1000c6r7j10p1',
                    'x1000c6r7j102p0', 'x1000c6r7j102p1',
                    'x1000c6r7j103p0', 'x1000c6r7j103p1',
                    'x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0',
                    'x1000c6r7j6p1', 'x1000c6r7j6p0']
        self.assertEqual(result, expected)

    def test_only_fabric(self):
        """Test Switch: get_switch_ports() only fabric ports"""
        del self.mock_fc_data['ports']['edge']
        result = self.pm.get_switch_ports('x1000c6r7')
        expected = ['x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0',
                    'x1000c6r7j6p1', 'x1000c6r7j6p0']
        self.assertEqual(result, expected)

    def test_only_edge(self):
        """Test Switch: get_switch_ports() only edge ports"""
        del self.mock_fc_data['ports']['fabric']
        result = self.pm.get_switch_ports('x1000c6r7')
        expected = ['x1000c6r7j100p0', 'x1000c6r7j100p1',
                    'x1000c6r7j10p0', 'x1000c6r7j10p1',
                    'x1000c6r7j102p0', 'x1000c6r7j102p1',
                    'x1000c6r7j103p0', 'x1000c6r7j103p1']
        self.assertEqual(result, expected)

    def test_api_error(self):
        """Test Switch: get_switch_ports() APIError"""
        self.mock_fc_client.get.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_switch_ports('x1000c6r7')
        self.assertEqual(result, None)

    def test_value_error(self):
        """Test Switch: get_switch_ports() ValueError"""
        self.mock_fc_response.json.side_effect = ValueError
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_switch_ports('x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_ports_key(self):
        """Test Switch: get_switch_ports() missing ports key"""
        del self.mock_fc_data['ports']
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_switch_ports('x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_fabric_edge_keys(self):
        """Test Switch: get_switch_ports() missing fabric and edge keys"""
        del self.mock_fc_data['ports']['fabric']
        del self.mock_fc_data['ports']['edge']

        result = self.pm.get_switch_ports('x1000c6r7')
        self.assertEqual(result, [])

    def tearDown(self):
        mock.patch.stopall()


class TestCreatePortSet(unittest.TestCase):
    """Unit test for Switch create_port_set()."""

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

        self.mock_json_dumps = mock.patch('json.dumps', autospec=True).start()
        self.pm = PortManager()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: create_port_set() basic"""
        portset = {'name': 'SAT-switch', 'ports': []}
        result = self.pm.create_port_set(portset)
        self.mock_json_dumps.assert_called_once_with(portset)
        self.mock_fc_client.post.assert_called_once_with('port-sets', payload=self.mock_json_dumps.return_value)
        self.assertEqual(result, True)

    def test_api_error(self):
        """Test Switch: create_port_set() APIError"""
        self.mock_fc_client.post.side_effect = APIError
        portset = {'name': 'SAT-switch', 'ports': []}
        with self.assertLogs(level='ERROR'):
            result = self.pm.create_port_set(portset)
        self.assertEqual(result, False)


class TestGetPortSets(unittest.TestCase):
    """Unit test for Switch get_port_sets()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

        # The data that will be returned by the firmware response's JSON method
        self.mock_fc_data = {'names': ['fabric-ports', 'edge-ports']}

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = self.mock_fc_data
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.get.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()
        self.pm = PortManager()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: get_port_sets() basic"""
        result = self.pm.get_port_sets()
        self.assertEqual(result, self.mock_fc_data)

    def test_api_error(self):
        """Test Switch: get_port_sets() APIError"""
        self.mock_fc_client.get.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_port_sets()
        self.assertEqual(result, None)

    def test_value_error(self):
        """Test Switch: get_port_sets() ValueError"""
        self.mock_fc_response.json.side_effect = ValueError
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_port_sets()
        self.assertEqual(result, None)


class TestGetPortSetConfig(unittest.TestCase):
    """Unit test for Switch get_port_set_config()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

        # The data that will be returned by the firmware response's JSON method
        self.mock_fc_data = {
            'ports': [
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j10p0'},
                {'config':
                    {'autoneg': True, 'enable': True,
                     'flowControl': {'rx': True, 'tx': True},
                     'mac': '02:00:00:00:00:00', 'speed': '100'},
                 'xname': 'x1000c6r7j10p1'},
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
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()
        self.pm = PortManager()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: get_port_set_config() basic"""
        result = self.pm.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, self.mock_fc_data)

    def test_api_error(self):
        """Test Switch: get_port_set_config() APIError"""
        self.mock_fc_client.get.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)

    def test_value_error(self):
        """Test Switch: get_port_set_config() ValueError"""
        self.mock_fc_response.json.side_effect = ValueError
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_ports_key(self):
        """Test Switch: get_port_set_config() missing ports key"""
        self.mock_fc_response.json.return_value = {
            'docks': [{'config': {'ship-size': 'super-tanker'}}]}
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)

    def test_missing_config_key(self):
        """Test Switch: get_port_set_config() missing config key"""
        self.mock_fc_response.json.return_value = {
            'ports': [{'Perth': {'hemisphere': 'southern'}}]}
        with self.assertLogs(level='ERROR'):
            result = self.pm.get_port_set_config('SAT-x1000c6r7')
        self.assertEqual(result, None)


class TestUpdatePortSet(unittest.TestCase):
    """Unit test for Switch update_port_set()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = {}
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.put.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()
        self.pm = PortManager()

    def tearDown(self):
        mock.patch.stopall()

    def test_enable(self):
        """Test Switch: update_port_set() enable"""
        port_config = {'autoneg': True, 'enable': True,
                       'flowControl': {'rx': True, 'tx': True}, 'speed': 100}
        result = self.pm.update_port_set('SAT-port', port_config, True)
        self.mock_fc_client.put.assert_called_once_with('port-sets', 'SAT-port', 'config',
                                                        payload=json.dumps(port_config))
        self.assertEqual(result, True)

    def test_disable(self):
        """Test Switch: update_port_set() disable"""
        port_config = {'autoneg': True, 'enable': True,
                       'flowControl': {'rx': True, 'tx': True}, 'speed': 100}
        result = self.pm.update_port_set('SAT-port', port_config, False)
        self.mock_fc_client.put.assert_called_once_with('port-sets', 'SAT-port', 'config',
                                                        payload=json.dumps(port_config))
        self.assertEqual(result, True)

    def test_api_error(self):
        """Test Switch: update_port_set() APIError"""
        port_config = {'autoneg': True, 'enable': True,
                       'flowControl': {'rx': True, 'tx': True}, 'speed': 100}
        self.mock_fc_client.put.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = self.pm.update_port_set('SAT-switch', port_config, True)
        self.assertEqual(result, False)


class TestDeletePortSet(unittest.TestCase):
    """Unit test for Switch delete_port_set()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = {}
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.delete.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()
        self.pm = PortManager()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test Switch: delete_port_set() basic"""
        result = self.pm.delete_port_set('SAT-switch')
        self.mock_fc_client.delete.assert_called_once_with('port-sets', 'SAT-switch')
        self.assertEqual(result, True)

    def test_api_error(self):
        """Test Switch: delete_port_set() APIError"""
        self.mock_fc_client.delete.side_effect = APIError
        with self.assertLogs(level='ERROR'):
            result = self.pm.delete_port_set('SAT-switch')
        self.assertEqual(result, False)


class TestGetJackPorts(unittest.TestCase):

    def setUp(self):
        """Mock functions called."""
        self.mock_sat_session = mock.Mock()
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.SATSession').start()

        # x1000 and x3000 ports simulate standard fabric and edge cables

        # x5000c6r[7-8] ports show a bifurcated fabric cable in which a total of 8 ports must be found
        # for one cable.

        # x5000c6r9j9 is meant to simulate a Y-type edge cable in which the diverging ends are plugged into compute
        # nodes.  This is handled the same as any other edge cable.

        # x5000c6r10j9 and x5000c6r11j[10-11] are meant to simulate a Y-type fabric cable in which the diverging ends
        # are plugged into other fabric ports, although I'm not sure this is really possible.
        # In this scenario we have x5000c6r10j9p0 connected to x5000c6r11j10p0 on one jack and x5000c6r10j9p1
        # connected to x5000c6r11j11p0 on another.  It is making the assumption that because x5000c6r11j10p1 and
        # x5000c6r11j11p1 cannot be linked to anything they won't be included in the list of fabric ports, which
        # may be a bad assumption.

        self.mock_fc_data = {
            'links': [
                {'endpoint1': 'x1000c6r3j24p1', 'endpoint2': 'x1000c6r7j24p1'},
                {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
                {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
                {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'},
                {'endpoint1': 'x5000c6r7j9p0',  'endpoint2': 'x5000c6r8j9p0'},
                {'endpoint1': 'x5000c6r7j9p1',  'endpoint2': 'x5000c6r8j10p0'},
                {'endpoint1': 'x5000c6r7j10p0', 'endpoint2': 'x5000c6r8j9p1'},
                {'endpoint1': 'x5000c6r7j10p1', 'endpoint2': 'x5000c6r8j10p1'},
                {'endpoint1': 'x5000c6r10j9p0', 'endpoint2': 'x5000c6r11j10p0'},
                {'endpoint1': 'x5000c6r10j9p1', 'endpoint2': 'x5000c6r11j11p0'}
            ],
            'ports': {
                'edge': [
                    'x3000c0r7j4p0',   'x3000c0r7j4p1',   'x3000c0r7j8p0',   'x1000c6r7j100p0', 'x1000c6r7j100p1',
                    'x1000c6r7j10p0', 'x1000c6r7j10p1', 'x1000c6r7j102p0', 'x1000c6r7j102p1', 'x1000c6r7j103p0',
                    'x1000c6r7j103p1', 'x1000c3r7j103p0', 'x1000c3r7j103p1', 'x1000c3r7j10p1',
                    'x5000c6r9j9p0',   'x5000c6r9j9p1',
                ],
                'fabric': [
                    'x3000c0r7j31p1', 'x3000c0r7j31p0', 'x3000c0r7j1p1', 'x1000c6r7j2p1', 'x1000c6r7j2p0',
                    'x1000c6r7j4p1', 'x1000c6r7j4p0', 'x1000c6r7j6p1', 'x1000c6r7j6p0', 'x1000c3r7j4p1',
                    'x1000c3r7j4p0', 'x1000c3r7j6p1', 'x1000c6r3j24p1', 'x1000c6r7j24p1', 'x1000c3r7j11p0',
                    'x1000c6r7j9p1', 'x1000c0r3j13p0', 'x1000c6r7j13p0', 'x1000c3r7j13p1', 'x1000c6r3j9p0',
                    'x5000c6r7j9p0', 'x5000c6r7j9p1', 'x5000c6r7j10p0', 'x5000c6r7j10p1', 'x5000c6r8j9p0',
                    'x5000c6r8j9p1', 'x5000c6r8j10p0', 'x5000c6r8j10p1',
                    'x5000c6r10j9p0', 'x5000c6r10j9p1', 'x5000c6r11j10p0', 'x5000c6r11j11p0',
                ]
            }
        }

        self.mock_fc_response = mock.Mock()
        self.mock_fc_response.json.return_value = self.mock_fc_data
        self.mock_fc_client = mock.Mock()
        self.mock_fc_client.get.return_value = self.mock_fc_response
        self.mock_fc_client_cls = mock.patch('sat.cli.swap.ports.FabricControllerClient',
                                             return_value=self.mock_fc_client).start()
        self.pm = PortManager()

    def test_get_jack_ports_basic(self):
        """get_jack_ports with a single jack returns the endpoints for that jack"""
        expected = ['x1000c6r3j24p1', 'x1000c6r7j24p1']
        actual = self.pm.get_jack_ports(['x1000c6r3j24'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_both_jacks(self):
        """get_jack_ports with jacks connected by a cable returns the endpoints for the jacks"""
        expected = ['x1000c6r3j24p1', 'x1000c6r7j24p1']
        actual = self.pm.get_jack_ports(['x1000c6r3j24', 'x1000c6r7j24'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_bad_jacks(self):
        """get_jack_ports with jacks that are not connected returns an error"""
        self.assertIs(self.pm.get_jack_ports(['x1000c6r3j24', 'x1000c6r3j9']), None)

    def test_get_jack_ports_bad_jacks_force(self):
        """get_jack_ports with jacks that are not connected can be forced to return all endpoints"""
        expected = ['x1000c6r3j24p1', 'x1000c6r7j24p1', 'x1000c6r3j9p0', 'x1000c3r7j13p1']
        actual = self.pm.get_jack_ports(['x1000c6r3j24', 'x1000c6r3j9'], force=True)
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_junk(self):
        """Giving nonsense values to get_jack_ports gives nothing"""
        with self.assertLogs(level='ERROR'):
            self.assertEqual(self.pm.get_jack_ports(['abc', '123']), [])

    def test_get_jack_ports_junk_force(self):
        """Supplying nonsense values and one good value gives an empty list"""
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(['abc', 'x1000c6r3j24', 'x1000c6r7j24'])
            self.assertCountEqual(actual, [])

    def test_get_jack_ports_no_port_links(self):
        """When no links are returned but we're querying a fabric port, log an error and return None"""
        self.mock_fc_data['links'] = []
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(['x1000c6r3j24'])
        self.assertIs(None, actual)

    def test_get_jack_ports_no_port_links_force(self):
        """When no links are returned for a fabric port but forcing, warn and return ports for that jack"""
        self.mock_fc_data['links'] = []
        expected = ['x1000c6r3j24p1']
        with self.assertLogs(level='WARNING'):
            actual = self.pm.get_jack_ports(['x1000c6r3j24'], force=True)
        self.assertEqual(expected, actual)

    def test_get_jack_ports_missing_port_link(self):
        """When querying a fabric port but we're missing a link, error and return None"""
        self.mock_fc_data['links'] = [
            {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
            {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
            {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'}
        ]
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(['x1000c6r3j24'])
        self.assertIs(None, actual)

    def test_get_jack_ports_missing_port_link_force(self):
        """When forcing and missing a link, warn and return ports for just the given jack"""
        self.mock_fc_data['links'] = [
            {'endpoint1': 'x1000c3r7j11p0', 'endpoint2': 'x1000c6r7j9p1'},
            {'endpoint1': 'x1000c0r3j13p0', 'endpoint2': 'x1000c6r7j13p0'},
            {'endpoint1': 'x1000c3r7j13p1', 'endpoint2': 'x1000c6r3j9p0'}
        ]
        expected = ['x1000c6r3j24p1']
        with self.assertLogs(level='WARNING'):
            actual = self.pm.get_jack_ports(['x1000c6r3j24'], force=True)
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_no_port_links_edge(self):
        """When no links are returned for a jack with only edge ports, we should just get the ports for that jack"""
        self.mock_fc_data['links'] = []
        expected = ['x3000c0r7j4p0', 'x3000c0r7j4p1']
        with mock.patch('sat.cli.swap.ports.LOGGER') as fake_logger:
            actual = self.pm.get_jack_ports(['x3000c0r7j4'])
        self.assertCountEqual(expected, actual)

        fake_logger.warn.assert_not_called()
        fake_logger.error.assert_not_called()

    def test_get_jack_ports_no_ports(self):
        """When the portinfo query has no 'ports' get_jack_ports should error and return None"""
        del self.mock_fc_data['ports']
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(['x3000c0r7j4'])
        self.assertIs(None, actual)

    def test_get_jack_ports_no_links(self):
        """When the portinfo query has no 'links' get_jack_ports should error and return None"""
        del self.mock_fc_data['links']
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(['x3000c0r7j4'])
        self.assertIs(None, actual)

    def test_get_jack_ports_no_ports_fabric(self):
        """When the portinfo query has no ['ports']['fabric'] get_jack_ports should error and return None"""
        del self.mock_fc_data['ports']['fabric']
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(['x3000c0r7j4'])
        self.assertIs(None, actual)

    def test_get_jack_ports_no_ports_edge(self):
        """When the portinfo query has no ['ports']['edge'] get_jack_ports should error and return None"""
        del self.mock_fc_data['ports']['edge']
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(['x3000c0r7j4'])
        self.assertIs(None, actual)

    def test_get_jack_ports_bifurcated_cable(self):
        """Test getting jack ports for a bifurcated cable given a single jack xname"""
        # all 8 ports should be returned
        expected = [
            'x5000c6r7j9p0', 'x5000c6r7j9p1', 'x5000c6r7j10p0', 'x5000c6r7j10p1', 'x5000c6r8j9p0', 'x5000c6r8j9p1',
            'x5000c6r8j10p0', 'x5000c6r8j10p1'
        ]
        actual = self.pm.get_jack_ports(['x5000c6r7j9'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_bifurcated_cable_multiple_jacks(self):
        """Test getting jack ports for a bifurcated cable given several jack xnames"""
        expected = [
            'x5000c6r7j9p0', 'x5000c6r7j9p1', 'x5000c6r7j10p0', 'x5000c6r7j10p1', 'x5000c6r8j9p0', 'x5000c6r8j9p1',
            'x5000c6r8j10p0', 'x5000c6r8j10p1'
        ]
        actual = self.pm.get_jack_ports(['x5000c6r7j9', 'x5000c6r7j10'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_bifurcated_cable_all_jacks(self):
        """Test getting jack ports for a bifurcated cable given all jack xnames"""
        expected = [
            'x5000c6r7j9p0', 'x5000c6r7j9p1', 'x5000c6r7j10p0', 'x5000c6r7j10p1', 'x5000c6r8j9p0', 'x5000c6r8j9p1',
            'x5000c6r8j10p0', 'x5000c6r8j10p1'
        ]
        actual = self.pm.get_jack_ports(['x5000c6r7j9', 'x5000c6r7j10', 'x5000c6r8j9', 'x5000c6r8j10'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_bifurcated_cable_one_bad_jack(self):
        """One invalid jack xname on a bifurcated cable should return None"""
        with self.assertLogs(level='ERROR'):
            actual = self.pm.get_jack_ports(
                ['x5000c6r7j9', 'x5000c6r7j10', 'x5000c6r8j9', 'x5000c6r8j10', 'x3000c0r7j4']
            )
        self.assertIs(None, actual)

    def test_get_jack_ports_bifurcated_cable_one_bad_jack_force(self):
        """One invalid jack xname among others on a bifurcated cable when forcing should return all of the ports"""
        expected = [
            'x5000c6r8j10p0', 'x3000c0r7j4p0', 'x5000c6r7j10p0', 'x5000c6r8j9p1', 'x3000c0r7j4p1', 'x5000c6r7j10p1',
            'x5000c6r7j9p0', 'x5000c6r8j10p1', 'x5000c6r8j9p0', 'x5000c6r7j9p1'
        ]
        with self.assertLogs(level='WARNING'):
            actual = self.pm.get_jack_ports(
                ['x5000c6r7j9', 'x5000c6r7j10', 'x5000c6r8j9', 'x5000c6r8j10', 'x3000c0r7j4'], force=True
            )
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_y_edge_cable(self):
        """Test getting jack ports for a 'Y' edge cable with one jack xname"""

        # A Y edge cable is pretty simple because it does not have any port links and we can only disable the
        # ports local to the jack xname
        expected = [
            'x5000c6r9j9p0', 'x5000c6r9j9p1'
        ]
        actual = self.pm.get_jack_ports(['x5000c6r9j9'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_y_fabric_cable(self):
        """Test getting jack ports for a 'Y' fabric cable with one jack xname"""

        # This is assuming that 'x5000c6r11j10p1' and 'x5000c6r11j11p1' do not exist
        expected = [
            'x5000c6r10j9p0', 'x5000c6r10j9p1', 'x5000c6r11j10p0', 'x5000c6r11j11p0'
        ]
        actual = self.pm.get_jack_ports(['x5000c6r10j9'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_y_fabric_cable_diverging_end(self):
        """Test getting jack ports for a 'Y' fabric cable with the jack xname of a diverging end"""

        # This is assuming that 'x5000c6r11j10p1' and 'x5000c6r11j11p1' do not exist
        expected = [
            'x5000c6r10j9p0', 'x5000c6r10j9p1', 'x5000c6r11j10p0', 'x5000c6r11j11p0'
        ]
        actual = self.pm.get_jack_ports(['x5000c6r11j10'])
        self.assertCountEqual(expected, actual)

    def test_get_jack_ports_y_fabric_cable_all_xnames(self):
        """Test getting jack ports for a 'Y' fabric cable with all jack xnames"""

        # This is assuming that 'x5000c6r11j10p1' and 'x5000c6r11j11p1' do not exist
        expected = [
            'x5000c6r10j9p0', 'x5000c6r10j9p1', 'x5000c6r11j10p0', 'x5000c6r11j11p0'
        ]
        actual = self.pm.get_jack_ports(['x5000c6r10j9', 'x5000c6r11j10', 'x5000c6r11j11'])
        self.assertCountEqual(expected, actual)


if __name__ == '__main__':
    unittest.main()
