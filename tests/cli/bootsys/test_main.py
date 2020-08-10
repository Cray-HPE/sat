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
import glob
import logging
import os
from subprocess import CalledProcessError
import unittest
from unittest.mock import call, Mock, patch

import sat
import sat.cli.bootsys.defaults
from sat.cli.bootsys.bos import BOSFailure
from sat.cli.bootsys.main import do_boot, do_bootsys, do_shutdown, dump_pods
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
        self.pod_state_file = '/path/to/pod-state-file'
        self.args.pod_state_file = self.pod_state_file
        self.args.ignore_pod_failures = False
        self.args.ipmi_timeout = 1

        # Mock functions called in do_shutdown
        self.mock_service_activity_check = patch(
            'sat.cli.bootsys.main.do_service_activity_check'
        ).start()
        self.mock_print = patch('builtins.print').start()
        self.mock_dump_pods = patch('sat.cli.bootsys.main.dump_pods').start()
        self.mock_bos_operations = patch('sat.cli.bootsys.main.do_bos_operations').start()
        self.mock_pester_choices = patch('sat.util.pester_choices').start()
        self.mock_pester_choices.return_value = 'yes'
        self.mock_do_shutdown_playbook = patch('sat.cli.bootsys.main.do_shutdown_playbook').start()
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
        self.mock_dump_pods.assert_called_once_with(self.pod_state_file)
        self.mock_print.assert_has_calls([
            call('Proceeding with BOS shutdown of computes and UAN.'),
            call('Proceeding with shutdown of management platform services.'),
            call('Succeeded with shutdown of management platform services.'),
            call('Proceeding with shutdown of management NCNs.'),
            call('Succeeded with shutdown of management NCNs.')
        ])
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_do_shutdown_playbook.assert_called_once_with()
        self.mock_ssh_client.load_system_host_keys.assert_called_once_with()
        self.mock_get_user_pass.assert_called_once()
        self.mock_mgmt_shutdown.assert_called_once_with(
            self.mock_ssh_client, self.mock_username,
            self.mock_password, self.args.ipmi_timeout, self.args.dry_run
        )

    def test_do_shutdown_dump_pods_errors(self):
        """Test do_shutdown with dump_pods raising various errors."""
        possible_errors = [CalledProcessError(returncode=1, cmd='fail'),
                           FileNotFoundError(), PermissionError()]

        for err in possible_errors:
            with self.subTest('test do_shutdown with dump_pods raising '
                              '{}'.format(type(err))):
                self.mock_dump_pods.side_effect = err

                with self.assertLogs(level=logging.ERROR) as cm:
                    with self.assertRaises(SystemExit):
                        do_shutdown(self.args)

                self.assert_in_element(str(err), cm.output)

                self.mock_dump_pods.assert_called_with(self.pod_state_file)
                self.mock_service_activity_check.assert_not_called()
                self.mock_bos_operations.assert_not_called()
                self.mock_do_shutdown_playbook.assert_not_called()
                self.mock_get_user_pass.assert_not_called()
                self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_dump_pods_ignore_errors(self):
        """Test do_shutdown with dump_pods raising various errors."""
        self.args.ignore_pod_failures = True

        possible_errors = [CalledProcessError(returncode=1, cmd='fail'),
                           FileNotFoundError(), PermissionError()]

        for err in possible_errors:
            with self.subTest('test do_shutdown with dump_pods raising '
                              '{}'.format(type(err))):
                self.mock_dump_pods.side_effect = err

                with self.assertLogs(level=logging.WARNING) as cm:
                    do_shutdown(self.args)

                self.assert_in_element(str(err), cm.output)

                self.mock_dump_pods.assert_called_with(self.pod_state_file)
                self.mock_service_activity_check.assert_called_with(self.args)
                self.mock_bos_operations.assert_called_with('shutdown')
                self.mock_do_shutdown_playbook.assert_called_with()
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
        self.mock_dump_pods.assert_called_once_with(self.pod_state_file)
        self.mock_print.assert_has_calls([
            call('Capturing state of k8s pods.'),
            call('Proceeding with BOS shutdown of computes and UAN.')
        ])
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_do_shutdown_playbook.assert_not_called()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_do_not_proceed_bos(self):
        """Test do_shutdown with a 'no' answer to the first proceed prompt."""
        self.mock_pester_choices.return_value = 'no'

        with self.assertRaises(SystemExit):
            do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_dump_pods.assert_called_once_with(self.pod_state_file)
        self.mock_bos_operations.assert_not_called()
        self.mock_do_shutdown_playbook.assert_not_called()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_do_not_proceed_playbook(self):
        """Test do_shutdown with a 'no' answer to the second proceed prompt."""
        self.mock_pester_choices.side_effect = ['yes', 'no']

        with self.assertRaises(SystemExit):
            do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_dump_pods.assert_called_once_with(self.pod_state_file)
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_do_shutdown_playbook.assert_not_called()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()

    def test_do_shutdown_do_not_proceed_mgmt(self):
        """Test do_shutdown with a 'no' answer to the second proceed prompt."""
        self.mock_pester_choices.side_effect = ['yes', 'yes', 'no']

        with self.assertRaises(SystemExit):
            do_shutdown(self.args)

        self.mock_service_activity_check.assert_called_once_with(self.args)
        self.mock_dump_pods.assert_called_once_with(self.pod_state_file)
        self.mock_bos_operations.assert_called_once_with('shutdown')
        self.mock_do_shutdown_playbook.assert_called_once_with()
        self.mock_get_user_pass.assert_not_called()
        self.mock_mgmt_shutdown.assert_not_called()


class TestDoBootsys(unittest.TestCase):
    """Test the do_bootsys function."""

    def setUp(self):
        """Mock the methods called by do_bootsys.
        """
        self.mock_do_boot = patch('sat.cli.bootsys.main.do_boot').start()
        self.mock_do_shutdown = patch('sat.cli.bootsys.main.do_shutdown').start()

        self.default_dir = os.path.join(os.path.dirname(__file__), '../..', 'resources', 'podstates/')
        self.default_podstate = os.path.join(self.default_dir, 'pod-state.json')

        patch('sat.cli.bootsys.main.DEFAULT_PODSTATE_DIR', self.default_dir).start()
        patch('sat.cli.bootsys.main.DEFAULT_PODSTATE_FILE', self.default_podstate).start()

        self.pod_mock = patch(
            'sat.cli.bootsys.main.get_pods_as_json',
            return_value='hello').start()

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

    def test_dump_pods_custom_path(self):
        """dump_pods should write text to a custom file location.

        More specifically, it should write the output of get_pods_as_json.
        """
        dir_in = self.default_dir
        outfile = os.path.join(dir_in, 'custom-path')

        try:
            dump_pods(outfile)

            with open(outfile, 'r') as f:
                lines = f.read()

            self.assertEqual('hello', lines)

        finally:
            os.remove(outfile)

    def test_dump_pods_default(self):
        """dump_pods should create a symlink that points to the next log.
        """
        try:
            dump_pods(sat.cli.bootsys.main.DEFAULT_PODSTATE_FILE)
            with open(self.default_podstate, 'r') as f:
                lines = f.read()
            self.assertEqual('hello', lines)

        finally:
            files = glob.glob(self.default_dir + 'pod-state*')
            for f in files:
                os.remove(f)

    def test_dump_pods_rotating_logs(self):
        """dump_pods should rotate the logs.

        A maximum number of logs should be kept as specified
        in the config file.
        """
        class MockNamer:
            _num = -1
            @classmethod
            def genName(cls):
                MockNamer._num = MockNamer._num + 1
                return self.default_dir + 'pod-state.{:02d}.json'.format(MockNamer._num)

        patch('sat.cli.bootsys.main._new_file_name', MockNamer.genName).start()
        patch('sat.cli.bootsys.main.get_config_value', return_value=5).start()

        # At the end of this, there should only be 5 logs plus the symlink.
        try:
            for i in range(1, 15):
                dump_pods(sat.cli.bootsys.main.DEFAULT_PODSTATE_FILE)

            files = [x for x in sorted(os.listdir(self.default_dir)) if x.startswith('pod-state')]

            # There should be 6 files left including the symlink, and the earliest
            # should appear first.
            self.assertEqual(6, len(files))
            self.assertEqual('pod-state.09.json', files[0])

        finally:
            files = glob.glob(self.default_dir + 'pod-state*')
            for f in files:
                os.remove(f)


if __name__ == '__main__':
    unittest.main()
