"""
Unit tests for the sat.cli.bootsys.main module.

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
import logging
import unittest
from unittest.mock import call, Mock, patch

from sat.cli.bootsys.bos import BOSFailure
from sat.cli.bootsys.main import do_boot, do_bootsys, do_shutdown
from sat.cli.bootsys.state_recorder import StateError
from tests.common import ExtendedTestCase


class TestDoBoot(unittest.TestCase):
    """Test the do_boot function."""

    def setUp(self):
        """Mock the functions called by do_boot."""
        self.mock_do_mgmt_boot = patch('sat.cli.bootsys.main.do_mgmt_boot').start()
        self.mock_do_bos_operations = patch('sat.cli.bootsys.main.do_bos_operations').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_do_boot(self):
        """Test the do_boot function happy path."""
        args = Mock()
        do_boot(args)
        self.mock_do_mgmt_boot.assert_called_once_with(args)
        self.mock_do_bos_operations.assert_called_once_with('boot')

    def test_do_boot_bos_failure(self):
        """Test the do_boot function with a BOS failure to boot nodes."""
        args = Mock()
        self.mock_do_bos_operations.side_effect = BOSFailure

        with self.assertRaises(SystemExit) as cm:
            do_boot(args)

        self.mock_do_mgmt_boot.assert_called_once_with(args)
        self.mock_do_bos_operations.assert_called_once_with('boot')
        self.assertEqual(1, cm.exception.code)


class TestDoShutdown(ExtendedTestCase):
    """Test the do_shutdown function."""

    def setUp(self):
        """Set up mocks."""

        # Set up some mock arguments
        self.args = Mock()
        self.args.dry_run = False
        self.args.redfish_username = None
        self.args.ignore_pod_failures = False
        self.args.ipmi_timeout = 1
        self.args.capmc_timeout = 120

        # Mock functions called in do_shutdown
        self.mock_service_activity_check = patch(
            'sat.cli.bootsys.main.do_service_activity_check'
        ).start()
        self.mock_print = patch('builtins.print').start()
        self.mock_pod_state_recorder = patch('sat.cli.bootsys.main.PodStateRecorder').start().return_value
        self.mock_bos_operations = patch('sat.cli.bootsys.main.do_bos_operations').start()
        self.mock_nodes_power_off = patch('sat.cli.bootsys.main.do_nodes_power_off',
                                          return_value=(set(), set())).start()
        self.mock_pester_choices = patch('sat.util.pester_choices').start()
        self.mock_pester_choices.return_value = 'yes'
        self.mock_do_shutdown_playbook = patch('sat.cli.bootsys.main.do_shutdown_playbook').start()
        self.mock_do_enable_hosts = patch('sat.cli.bootsys.main.do_enable_hosts_entries').start()
        self.mock_ssh_client_cls = patch('sat.cli.bootsys.main.SSHClient').start()
        self.mock_ssh_client = Mock()
        self.mock_ssh_client_cls.return_value = self.mock_ssh_client
        self.mock_username = 'user'
        self.mock_password = 'password'
        self.mock_get_user_pass = patch('sat.cli.bootsys.main.get_username_and_password_interactively').start()
        self.mock_get_user_pass.return_value = self.mock_username, self.mock_password
        self.mock_mgmt_shutdown = patch('sat.cli.bootsys.main.do_mgmt_shutdown_power').start()

    def tearDown(self):
        """Stop all mocks."""
        patch.stopall()

    def test_do_shutdown_no_errors(self):
        """Test the do_shutdown function with no errors."""
        do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_print.assert_has_calls([
            call('Proceeding with BOS shutdown of computes and UAN.'),
            call('Proceeding with shutdown of management platform services.'),
            call('Succeeded with shutdown of management platform services.'),
            call('Enabling required entries in /etc/hosts for NCN mgmt interfaces.'),
            call('Proceeding with shutdown of management NCNs.'),
            call('Succeeded with shutdown of management NCNs.')
        ])
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_nodes_power_off.assert_called_once_with(self.args.capmc_timeout)
        self.mock_do_shutdown_playbook.assert_called_once_with()
        self.mock_do_enable_hosts.assert_called_once_with()
        self.mock_ssh_client.load_system_host_keys.assert_called_once_with()
        self.mock_get_user_pass.assert_called_once()
        self.mock_mgmt_shutdown.assert_called_once_with(
            self.mock_ssh_client, self.mock_username,
            self.mock_password, self.args.ipmi_timeout, self.args.dry_run
        )

    def test_do_shutdown_dump_pods_error(self):
        """Test do_shutdown with pod dumping raising a StateError."""
        err = StateError("failed to capture pod state")
        self.mock_pod_state_recorder.dump_state.side_effect = err

        with self.assertLogs(level=logging.ERROR) as cm:
            with self.assertRaises(SystemExit):
                do_shutdown(self.args)

        self.assert_in_element(str(err), cm.output)

        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_service_activity_check.assert_not_called()
        self.mock_bos_operations.assert_not_called()
        self.mock_nodes_power_off.assert_not_called()
        self.mock_do_shutdown_playbook.assert_not_called()
        self.mock_do_enable_hosts.assert_not_called()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_dump_pods_ignore_errors(self):
        """Test do_shutdown while ignoring pod dump errors."""
        self.args.ignore_pod_failures = True

        err = StateError("failed to capture pod state")
        self.mock_pod_state_recorder.dump_state.side_effect = err

        with self.assertLogs(level=logging.WARNING) as cm:
            do_shutdown(self.args)

        self.assert_in_element(str(err), cm.output)

        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_service_activity_check.assert_called_with(self.args)
        self.mock_bos_operations.assert_called_with('shutdown')
        self.mock_nodes_power_off.assert_called_once_with(self.args.capmc_timeout)
        self.mock_do_shutdown_playbook.assert_called_with()
        self.mock_do_enable_hosts.assert_called_with()
        self.mock_ssh_client.load_system_host_keys.assert_called_with()
        self.mock_get_user_pass.assert_called()
        self.mock_mgmt_shutdown.assert_called_with(
            self.mock_ssh_client, self.mock_username,
            self.mock_password, self.args.ipmi_timeout, self.args.dry_run
        )

    def test_do_shutdown_bos_failure(self):
        """Test do_shutdown with do_bos_shutdown raising a BOSFailure."""
        bos_fail_msg = 'session creation failed'
        self.mock_bos_operations.side_effect = BOSFailure(bos_fail_msg)

        with self.assertLogs(level=logging.ERROR) as cm:
            with self.assertRaises(SystemExit):
                do_shutdown(self.args)

        self.assert_in_element('Failed BOS shutdown of computes and UAN:'
                               ' {}'.format(bos_fail_msg),
                               cm.output)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_print.assert_has_calls([
            call('Capturing state of k8s pods.'),
            call('Proceeding with BOS shutdown of computes and UAN.')
        ])
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_nodes_power_off.assert_not_called()
        self.mock_do_shutdown_playbook.assert_not_called()
        self.mock_do_enable_hosts.assert_not_called()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_capmc_failure(self):
        """Test do_shutdown with a failure and timeout in capmc power off stage."""
        timed_out_nodes = {'x5000c2s4b0n0'}
        failed_nodes = {'x5000c7s3b0n0', 'x5000c0s1b0n0'}
        self.mock_nodes_power_off.return_value = timed_out_nodes, failed_nodes

        do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_print.assert_has_calls([
            call('Proceeding with BOS shutdown of computes and UAN.'),
            call(f'The following node(s) timed out waiting to reach power off state: '
                 f'{", ".join(timed_out_nodes)}'),
            call(f'The following node(s) failed to power off with CAPMC: '
                 f'{", ".join(failed_nodes)}'),
            call('Proceeding with shutdown of management platform services.'),
            call('Succeeded with shutdown of management platform services.'),
            call('Enabling required entries in /etc/hosts for NCN mgmt interfaces.'),
            call('Proceeding with shutdown of management NCNs.'),
            call('Succeeded with shutdown of management NCNs.')
        ])
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_nodes_power_off.assert_called_once_with(self.args.capmc_timeout)
        self.mock_do_shutdown_playbook.assert_called_once_with()
        self.mock_do_enable_hosts.assert_called_once_with()
        self.mock_ssh_client.load_system_host_keys.assert_called_once_with()
        self.mock_get_user_pass.assert_called_once()
        self.mock_mgmt_shutdown.assert_called_once_with(
            self.mock_ssh_client, self.mock_username,
            self.mock_password, self.args.ipmi_timeout, self.args.dry_run
        )

    def test_do_shutdown_do_not_proceed_bos(self):
        """Test do_shutdown with a 'no' answer to the first proceed prompt."""
        self.mock_pester_choices.return_value = 'no'

        with self.assertRaises(SystemExit):
            do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_bos_operations.assert_not_called()
        self.mock_nodes_power_off.assert_not_called()
        self.mock_do_shutdown_playbook.assert_not_called()
        self.mock_do_enable_hosts.assert_not_called()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_do_not_proceed_playbook(self):
        """Test do_shutdown with a 'no' answer to the second proceed prompt."""
        self.mock_pester_choices.side_effect = ['yes', 'no']

        with self.assertRaises(SystemExit):
            do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_nodes_power_off.assert_called_once_with(self.args.capmc_timeout)
        self.mock_do_shutdown_playbook.assert_not_called()
        self.mock_do_enable_hosts.assert_not_called()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_do_not_proceed_mgmt(self):
        """Test do_shutdown with a 'no' answer to the second proceed prompt."""
        self.mock_pester_choices.side_effect = ['yes', 'yes', 'no']

        with self.assertRaises(SystemExit):
            do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_pod_state_recorder.dump_state.assert_called_once()
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_nodes_power_off.assert_called_once_with(self.args.capmc_timeout)
        self.mock_do_shutdown_playbook.assert_called_once_with()
        self.mock_do_enable_hosts.assert_called_once_with()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()


class TestDoBootsys(unittest.TestCase):
    """Test the do_bootsys function."""

    def setUp(self):
        """Mock the methods called by do_bootsys.
        """
        self.mock_do_boot = patch('sat.cli.bootsys.main.do_boot').start()
        self.mock_do_shutdown = patch('sat.cli.bootsys.main.do_shutdown').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_do_bootsys_boot(self):
        """Test do_bootsys with boot action."""
        args = Mock(action='boot')
        do_bootsys(args)
        self.mock_do_boot.assert_called_once_with(args)
        self.mock_do_shutdown.assert_not_called()

    def test_do_bootsys_shutdown(self):
        """Test do_bootsys with shutdown action."""
        args = Mock(action='shutdown')
        do_bootsys(args)
        self.mock_do_shutdown.assert_called_once_with(args)
        self.mock_do_boot.assert_not_called()

    def test_do_bootsys_invalid_action(self):
        """Test do_bootsys with an invalid action."""
        args = Mock(action='invalid')
        with self.assertRaises(SystemExit) as cm:
            do_bootsys(args)
        self.assertEqual(1, cm.exception.code)
        self.mock_do_boot.assert_not_called()
        self.mock_do_shutdown.assert_not_called()


if __name__ == '__main__':
    unittest.main()
