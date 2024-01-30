#
# MIT License
#
# (C) Copyright 2020-2022, 2024 Hewlett Packard Enterprise Development LP
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
from os.path import basename, dirname
import typing
import unittest
from unittest import mock

from sat.cli.swap.swap import SwitchSwapper, CableSwapper, output_json, POL_PRE
from sat.cli.swap import swap
from tests.test_util import ExtendedTestCase

# Constants used in the tests
EDGE_POLICY_LINK = '/fabric/port-policies/edge-policy'
FABRIC_POLICY_LINK = '/fabric/port-policies/fabric-policy'
QOS_POLICY_LINK = '/fabric/port-policies/qos-ll_be_bd_et-fabric-policy'
ONLINE_FABRIC_POLICY_LINKS = [FABRIC_POLICY_LINK, QOS_POLICY_LINK]
ONLINE_EDGE_POLICY_LINKS = [EDGE_POLICY_LINK]
OFFLINE_FABRIC_POLICY_LINKS = [f'{dirname(link)}/{POL_PRE}{basename(link)}'
                               for link in ONLINE_FABRIC_POLICY_LINKS]
OFFLINE_EDGE_POLICY_LINKS = [f'{dirname(link)}/{POL_PRE}{basename(link)}'
                             for link in ONLINE_EDGE_POLICY_LINKS]


class TestCableSwapper(ExtendedTestCase):

    def setUp(self):
        """Mock functions called."""
        self.mock_port_data_list = [
            {'xname': 'x1000c6r7j101p0',
             'port_link': '/fabric/ports/x1000c6r7j101p0',
             'policy_links': ONLINE_FABRIC_POLICY_LINKS},
            {'xname': 'x1000c6r7j101p1',
             'port_link': '/fabric/ports/x1000c6r7j101p1',
             'policy_links': ONLINE_FABRIC_POLICY_LINKS},
            {'xname': 'x1000c6r7j2p0',
             'port_link': '/fabric/ports/x1000c6r7j2p0',
             'policy_links': ONLINE_EDGE_POLICY_LINKS},
            {'xname': 'x1000c6r7j2p1',
             'port_link': '/fabric/ports/x1000c6r7j2p1',
             'policy_links': ONLINE_EDGE_POLICY_LINKS}
        ]
        self.mock_port_manager = mock.patch('sat.cli.swap.swap.PortManager',
                                            autospec=True).start().return_value
        self.mock_port_manager.get_jack_port_data_list.return_value = self.mock_port_data_list

        self.mock_pester = mock.patch('sat.cli.swap.swap.pester', autospec=True).start()
        self.mock_pester.return_value = True
        self.mock_print = mock.patch('builtins.print', autospec=True).start()
        self.mock_output_json = mock.patch('sat.cli.swap.swap.output_json', autospec=True).start()

        # Type hint quiets PyCharm when 'action' value is set to a str in tests
        self.swap_args: dict[str, typing.Any] = {
            'action': None,
            'component_id': ['x1000c6r7j101'],
            'dry_run': True,
            'force': False,
            'save_ports': False
        }

    def tearDown(self):
        mock.patch.stopall()

    def run_swap_component(self):
        """Run swap_component()"""
        CableSwapper().swap_component(**self.swap_args)

    def test_dry_run(self):
        """Test swap cable in dry-run mode"""
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
            f"Dry run, so not enabling/disabling cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_swap_force_dry_run(self):
        """Test swap cable with force in dry-run mode"""
        self.swap_args['force'] = True
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once_with(
            self.swap_args['component_id'], force=True
        )
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
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
        self.mock_port_manager.update_port_policy_links.assert_not_called()
        expected_logs = [
            f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
            f"Dry run, so not enabling/disabling cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable_disabled_cable(self):
        """Test enable action enables a cable which is disabled"""
        # Update port data to use offline policies
        for port in self.mock_port_data_list:
            if len(port['policy_links']) > 1:
                port['policy_links'] = OFFLINE_FABRIC_POLICY_LINKS
            else:
                port['policy_links'] = OFFLINE_EDGE_POLICY_LINKS

        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()

        expected_calls = []
        for port in self.mock_port_data_list:
            if len(port['policy_links']) > 1:
                policy_links = ONLINE_FABRIC_POLICY_LINKS
            else:
                policy_links = ONLINE_EDGE_POLICY_LINKS
            expected_calls.append(mock.call(port['port_link'], policy_links))
        self.mock_port_manager.update_port_policy_links.assert_has_calls(expected_calls, any_order=True)

        expected_logs = [f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
                         f"Enabling ports on cable {self.swap_args['component_id'][0]}",
                         "Cable has been enabled."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable_already_enabled_cable(self):
        """Test enable action keeps the same port policies on an already enabled cable"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()

        expected_calls = [mock.call(port['port_link'], port['policy_links'])
                          for port in self.mock_port_data_list]
        self.mock_port_manager.update_port_policy_links.assert_has_calls(expected_calls, any_order=True)

        expected_logs = [f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
                         f"Enabling ports on cable {self.swap_args['component_id'][0]}",
                         "Cable has been enabled."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_disable_enabled_cable(self):
        """Test disable action disables an enabled cable"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_has_calls(
            [mock.call(policy, POL_PRE)
             for policy in ONLINE_FABRIC_POLICY_LINKS + ONLINE_EDGE_POLICY_LINKS],
            any_order=True
        )

        expected_calls = []
        for port in self.mock_port_data_list:
            if len(port['policy_links']) > 1:
                policy_links = OFFLINE_FABRIC_POLICY_LINKS
            else:
                policy_links = OFFLINE_EDGE_POLICY_LINKS
            expected_calls.append(mock.call(port['port_link'], policy_links))
        self.mock_port_manager.update_port_policy_links.assert_has_calls(expected_calls, any_order=True)

        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on cable {self.swap_args['component_id'][0]}",
                         "Cable has been disabled and is ready for replacement."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_disable_already_disabled_cable(self):
        """Test disable cation keeps the same policies on an already disabled cable"""
        # Update port data to use offline policies
        for port in self.mock_port_data_list:
            if len(port['policy_links']) > 1:
                port['policy_links'] = OFFLINE_FABRIC_POLICY_LINKS
            else:
                port['policy_links'] = OFFLINE_EDGE_POLICY_LINKS

        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            self.run_swap_component()
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        # Offline policy creation is skipped when they already start with the offline prefix
        self.mock_port_manager.create_offline_port_policy.assert_not_called()

        expected_calls = [mock.call(port['port_link'], port['policy_links'])
                          for port in self.mock_port_data_list]
        self.mock_port_manager.update_port_policy_links.assert_has_calls(expected_calls, any_order=True)

        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on cable {self.swap_args['component_id'][0]}",
                         "Cable has been disabled and is ready for replacement."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_get_ports_data_error(self):
        """Test swap_component error getting ports data"""
        self.mock_port_manager.get_jack_port_data_list.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()

    def test_no_jack_ports(self):
        """Test swap_component when no jack ports are returned"""
        self.mock_port_manager.get_jack_port_data_list.return_value = []
        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaises(SystemExit) as cm:
                self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_NO_PORTS_FOUND)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()
        self.assert_in_element(f"No ports found for cable {self.swap_args['component_id']}",
                               logs_cm.output)

    def test_create_port_policy_error(self):
        """Test swap_component disable with an error creating port policy"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.create_offline_port_policy.return_value = None
        with self.assertLogs(level=logging.INFO) as logs_cm:
            with self.assertRaises(SystemExit) as cm:
                self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_CREATE_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
                         f"Disabling ports on cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable_update_port_policy_link_error(self):
        """Test swap_component enable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.mock_port_manager.update_port_policy_links.return_value = None
        with self.assertLogs(level=logging.INFO) as logs_cm:
            with self.assertRaises(SystemExit) as cm:
                self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_links.call_count, 4)
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
                         f"Enabling ports on cable {self.swap_args['component_id'][0]}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_disable_update_port_policy_link_error(self):
        """Test swap_component disable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.update_port_policy_links.return_value = None
        with self.assertLogs(level=logging.INFO) as logs_cm:
            with self.assertRaises(SystemExit) as cm:
                self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_jack_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_links.call_count, 4)
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in self.mock_port_data_list])}",
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
             'policy_links': [FABRIC_POLICY_LINK]},
            {'xname': 'x1000c6r7j101p1',
             'port_link': '/fabric/ports/x1000c6r7j101p1',
             'policy_links': [FABRIC_POLICY_LINK]},
            {'xname': 'x1000c6r7j2p0',
             'port_link': '/fabric/ports/x1000c6r7j2p0',
             'policy_links': [EDGE_POLICY_LINK]},
            {'xname': 'x1000c6r7j2p1',
             'port_link': '/fabric/ports/x1000c6r7j2p1',
             'policy_links': [EDGE_POLICY_LINK]}
        ]
        self.mock_pester = mock.patch('sat.cli.swap.swap.pester', autospec=True).start()
        self.mock_pester.return_value = True
        self.mock_print = mock.patch('builtins.print', autospec=True).start()
        self.mock_output_json = mock.patch('sat.cli.swap.swap.output_json', autospec=True).start()

        # Type hint quiets PyCharm when 'action' value is set to a str in tests
        self.swap_args: dict[str, typing.Any] = {
            'action': None,
            'component_id': 'x1000c6r7',
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
        self.mock_port_manager.update_port_policy_links.assert_not_called()
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
        self.mock_port_manager.update_port_policy_links.assert_not_called()
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
        self.mock_port_manager.update_port_policy_links.assert_called()
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
        self.mock_port_manager.update_port_policy_links.assert_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on switch {self.swap_args['component_id']}",
                         "Switch has been disabled and is ready for replacement."]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_get_ports_data_error(self):
        """Test swap_component error getting ports data"""
        self.mock_port_manager.get_switch_port_data_list.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_GET_PORTS_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()

    def test_no_jack_ports(self):
        """Test swap_component when no jack ports are returned"""
        self.mock_port_manager.get_switch_port_data_list.return_value = []
        with self.assertLogs(level=logging.INFO) as logs_cm:
            with self.assertRaises(SystemExit) as cm:
                self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_NO_PORTS_FOUND)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()
        self.assert_in_element(f"No ports found for switch {self.swap_args['component_id']}",
                               logs_cm.output)

    def test_create_port_policy_error(self):
        """Test swap_component disable with an error creating port policy"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.create_offline_port_policy.return_value = None
        with self.assertLogs(level=logging.INFO) as logs_cm:
            with self.assertRaises(SystemExit) as cm:
                self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_CREATE_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.mock_port_manager.update_port_policy_links.assert_not_called()
        xnames = self.mock_port_manager.get_jack_port_data_list.return_value
        expected_logs = [f"Ports: {' '.join([p['xname'] for p in xnames])}",
                         f"Disabling ports on switch {self.swap_args['component_id']}"]
        for msg in expected_logs:
            self.assert_in_element(msg, logs_cm.output)

    def test_enable_update_port_policy_link_error(self):
        """Test swap_component enable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'enable'
        self.mock_port_manager.update_port_policy_links.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_not_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_links.call_count, 4)

    def test_disable_update_port_policy_link_error(self):
        """Test swap_component disable with an error updating port policy link"""
        self.swap_args['dry_run'] = False
        self.swap_args['action'] = 'disable'
        self.mock_port_manager.update_port_policy_links.return_value = None
        with self.assertRaises(SystemExit) as cm:
            self.run_swap_component()
        self.assertEqual(cm.exception.code, swap.ERR_PORT_POLICY_TOGGLE_FAIL)
        self.mock_port_manager.get_switch_port_data_list.assert_called_once()
        self.mock_output_json.assert_not_called()
        self.mock_port_manager.create_offline_port_policy.assert_called()
        self.assertEqual(self.mock_port_manager.update_port_policy_links.call_count, 4)


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
