#
# MIT License
#
# (C) Copyright 2020-2022 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.cli.swap.swap
"""

import logging
import unittest
from unittest import mock
from tests.test_util import ExtendedTestCase

from sat.cli.swap.swap import SwitchSwapper, CableSwapper, output_json
from sat.cli.swap import swap


class TestCableSwapper(ExtendedTestCase):

    def setUp(self):
        """Mock functions called."""
        self.mock_port_manager = mock.patch('sat.cli.swap.swap.PortManager',
                                            autospec=True).start().return_value
        self.mock_port_manager.get_jack_port_data_list.return_value = [
            {'xname': 'x1000c6r7j101p0',
             'port_link': '/fabric/ports/x1000c6r7j101p0',
             'policy_link': '/fabric/port-policies/fabric-policy'},
            {'xname': 'x1000c6r7j101p1',
             'port_link': '/fabric/ports/x1000c6r7j101p1',
             'policy_link': '/fabric/port-policies/fabric-policy'},
            {'xname': 'x1000c6r7j2p0',
             'port_link': '/fabric/ports/x1000c6r7j2p0',
             'policy_link': '/fabric/port-policies/edge-policy'},
            {'xname': 'x1000c6r7j2p1',
             'port_link': '/fabric/ports/x1000c6r7j2p1',
             'policy_link': '/fabric/port-policies/edge-policy'}
        ]

        self.mock_pester = mock.patch('sat.cli.swap.swap.pester', autospec=True).start()
        self.mock_pester.return_value = True
        self.mock_print = mock.patch('builtins.print', autospec=True).start()
        self.mock_output_json = mock.patch('sat.cli.swap.swap.output_json', autospec=True).start()

        self.swap_args = {
            'action': None,
            'component_id': ['x1000c6r7j101'],
            'disruptive': True,
            'dry_run': True,
            'force': False,
            'save_ports': False
        }

    def tearDown(self):
        mock.patch.stopall()

    def run_swap_component(self):
        """Run swap_component()"""
        CableSwapper().swap_component(**self.swap_args)

    def test_basic(self):
        """Test basic swap cable"""
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in xnames])}",
            f"Dry run, so not enabling/disabling cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_swap_force(self):
        """Test swap cable with force"""
        self.swap_args['force'] = True
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once_with(
            self.swap_args['component_id'], force=True
        )
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in xnames])}",
            f"Dry run, so not enabling/disabling cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_save_ports_file(self):
        """Test swap_component saves a ports file"""
        self.swap_args['save_ports'] = True
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_called_once()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in xnames])}",
            f"Dry run, so not enabling/disabling cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable(self):
        """Test swap_component enables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Enabling ports on cable {self.swap_args['component_id'][0]}",
                         "Cable has been enabled."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_disable(self):
        """Test swap_component disables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.mock_port_manager.update_port_policy_link.assert_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on cable {self.swap_args['component_id'][0]}",
                         "Cable has been disabled and is ready for replacement."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_not_disruptive_not_dry(self):
        """Test swap_component not disruptive and not dry run"""
        self.swap_args['disruptive'] = False
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Enabling ports on cable {self.swap_args['component_id'][0]}",
                         "Cable has been enabled."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_get_ports_data_error(self):
        """Test swap_component error getting ports data"""
        self.mock_port_manager.get_jack_port_data_list.return_value = None
        with self.assertRaises(SystemExit) as cm, \
             self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()

    def test_no_jack_ports(self):
        """Test swap_component when no jack ports are returned"""
        self.mock_port_manager.get_jack_port_data_list.return_value = []
        with self.assertRaises(SystemExit) as cm, \
             self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_NO_PORTS_FOUND)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        self.assert_in_element(
            f"No ports found for cable {self.swap_args['component_id']}",
            logs_cm.output)

    def test_create_port_policy_error(self):
        """Test swap_component disable with an error creating port policy"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.create_offline_port_policy.return_value = None
        with self.assertRaises(SystemExit) as cm, \
             self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_CREATE_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        self.mock_port_manager.get_jack_port_data_list.return_value
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable_update_port_policy_link_error(self):
        """Test swap_component enable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.mock_port_manager.update_port_policy_link.return_value = None
        with self.assertRaises(SystemExit) as cm, \
             self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_link.call_count, 4)
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Enabling ports on cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_disable_update_port_policy_link_error(self):
        """Test swap_component disable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.update_port_policy_link.return_value = None
        with self.assertRaises(SystemExit) as cm, \
             self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_link.call_count, 4)
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on cable {self.swap_args['component_id'][0]}",
                         f"Failed to disable cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)


class TestSwitchSwapper(ExtendedTestCase):

    def setUp(self):
        """Mock functions called."""
        self.mock_port_manager = mock.patch('sat.cli.swap.swap.PortManager',
                                            autospec=True).start().return_value
        self.mock_port_manager.get_switch_port_data_list.return_value = [
            {'xname': 'x1000c6r7j101p0',
             'port_link': '/fabric/ports/x1000c6r7j101p0',
             'policy_link': '/fabric/port-policies/fabric-policy'},
            {'xname': 'x1000c6r7j101p1',
             'port_link': '/fabric/ports/x1000c6r7j101p1',
             'policy_link': '/fabric/port-policies/fabric-policy'},
            {'xname': 'x1000c6r7j2p0',
             'port_link': '/fabric/ports/x1000c6r7j2p0',
             'policy_link': '/fabric/port-policies/edge-policy'},
            {'xname': 'x1000c6r7j2p1',
             'port_link': '/fabric/ports/x1000c6r7j2p1',
             'policy_link': '/fabric/port-policies/edge-policy'}
        ]
        self.mock_pester = mock.patch('sat.cli.swap.swap.pester', autospec=True).start()
        self.mock_pester.return_value = True
        self.mock_print = mock.patch('builtins.print', autospec=True).start()
        self.mock_output_json = mock.patch('sat.cli.swap.swap.output_json', autospec=True).start()

        self.swap_args = {
            'action': None,
            'component_id': 'x1000c6r7',
            'disruptive': True,
            'dry_run': True,
            'force': False,
            'save_ports': False
        }

    def tearDown(self):
        mock.patch.stopall()

    def run_swap_component(self):
        """Run swap_component()"""
        SwitchSwapper().swap_component(**self.swap_args)

    def test_basic(self):
        """Test basic swap switch"""
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in xnames])}",
            f"Dry run, so not enabling/disabling switch {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_save_ports_file(self):
        """Test swap_component saves a ports file"""
        self.swap_args['save_ports'] = True
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_switch_port_data_list.assert_called_once_with(switch_xname='x1000c6r7')
        self.mock_output_json.assert_called_once()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in xnames])}",
            f"Dry run, so not enabling/disabling switch {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable(self):
        """Test swap_component enables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Enabling ports on switch {self.swap_args['component_id']}",
                         "Switch has been enabled."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_disable(self):
        """Test swap_component disables components"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.mock_port_manager.update_port_policy_link.assert_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on switch {self.swap_args['component_id']}",
                         "Switch has been disabled and is ready for replacement."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_not_disruptive_not_dry(self):
        """Test swap_component not disruptive and not dry run"""
        self.swap_args['disruptive'] = False
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Enabling ports on switch {self.swap_args['component_id']}",
                         'Switch has been enabled.']
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_get_ports_data_error(self):
        """Test swap_component error getting ports data"""
        self.mock_port_manager.get_switch_port_data_list.return_value = None
        with self.assertRaises(SystemExit) as cm, \
             self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()

    def test_no_jack_ports(self):
        """Test swap_component when no jack ports are returned"""
        self.mock_port_manager.get_switch_port_data_list.return_value = []
        with self.assertRaises(SystemExit) as cm, \
                self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_NO_PORTS_FOUND)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        self.assert_in_element(f"No ports found for switch {self.swap_args['component_id']}",
                               logs_cm.output)

    def test_create_port_policy_error(self):
        """Test swap_component disable with an error creating port policy"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.create_offline_port_policy.return_value = None
        with self.assertRaises(SystemExit) as cm, \
                self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_CREATE_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.mock_port_manager.update_port_policy_link.assert_not_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on switch {self.swap_args['component_id']}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable_update_port_policy_link_error(self):
        """Test swap_component enable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.mock_port_manager.update_port_policy_link.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_link.call_count, 4)

    def test_disable_update_port_policy_link_error(self):
        """Test swap_component disable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.update_port_policy_link.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_link.call_count, 4)


class TestOutputJson(unittest.TestCase):
    """Unit test for swap output_json()."""

    def setUp(self):
        """Mock functions called."""

        self.mock_json_dump = mock.patch('json.dump', autospec=True).start()
        self.mock_open = mock.patch('builtins.open', autospec=True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_basic(self):
        """Test output_json basic"""
        output_json({}, 'filepath')
        self.mock_open.assert_called_once()
        self.mock_json_dump.assert_called_once()

    def test_api_error(self):
        """Test output_json OSError"""
        self.mock_open.side_effect = OSError
        with self.assertLogs(level='ERROR'):
            output_json({}, 'filepath')
