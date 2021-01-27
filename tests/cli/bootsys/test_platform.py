"""
Unit tests for the sat.cli.bootsys.platform module.

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

import logging
import socket
import unittest
from argparse import Namespace
from paramiko import SSHException, WarningPolicy
from unittest import mock

from sat.cli.bootsys.platform import (
    CONTAINER_STOP_SCRIPT,
    do_ceph_freeze,
    do_containerd_stop,
    do_platform_action,
    do_platform_start,
    do_platform_stop,
    do_service_action_on_hosts,
    FatalPlatformError,
    PlatformServicesStep,
    prompt_for_ncn_verification,
    RemoteServiceWaiter,
    SERVICE_ACTION_TIMEOUT,
    stop_containers
)


class TestStopContainers(unittest.TestCase):
    """Tests for the stop_containers function."""

    def setUp(self):
        """Set up mocks"""
        self.ssh_client_class = mock.patch('sat.cli.bootsys.platform.SSHClient').start()
        self.ssh_client = self.ssh_client_class.return_value
        self.ssh_client.exec_command.return_value = mock.Mock(), mock.Mock(), mock.Mock()
        self.ssh_client.exec_command.return_value[1].channel.recv_exit_status.return_value = 0
        self.host = 'ncn-w001'

    def tearDown(self):
        mock.patch.stopall()

    def assert_ssh_client_created(self):
        """Assert the SSH client was set up properly."""
        self.ssh_client_class.assert_called_once_with()
        self.ssh_client.load_system_host_keys.assert_called_once_with()
        self.ssh_client.set_missing_host_key_policy.assert_called_once_with(WarningPolicy)
        self.ssh_client.connect.assert_called_once_with(self.host)

    def test_stop_containers(self):
        """Test a basic call of stop_containers."""
        stop_containers(self.host)
        self.assert_ssh_client_created()
        self.ssh_client.exec_command.assert_called_once_with(CONTAINER_STOP_SCRIPT)

    def test_stop_containers_ssh_error(self):
        """Test stop_containers when an SSH error occurs."""
        for exception_type in SSHException, socket.error:
            with self.assertRaises(SystemExit):
                with self.assertLogs(level=logging.ERROR):
                    self.ssh_client.connect.side_effect = exception_type
                    stop_containers(self.host)
                    self.assert_ssh_client_created()

    def test_stop_containers_command_error(self):
        """Test stop_containers when a command exits non-zero."""
        self.ssh_client.exec_command.return_value[1].channel.recv_exit_status.return_value = 1
        with self.assertLogs(level=logging.WARNING):
            stop_containers(self.host)
            self.assert_ssh_client_created()
            self.ssh_client.exec_command.assert_called_once_with(CONTAINER_STOP_SCRIPT)


class TestRemoteServiceWaiter(unittest.TestCase):
    """Tests for the RemoteServiceWaiter class."""
    def setUp(self):
        """Set up mocks."""
        self.host = 'ncn-w001'
        self.service_name = 'exampled'
        self.timeout = 60
        self.service_status = b'active\n'
        self.enabled_status = b'enabled\n'
        # set self.systemctl_works to False to mimic cases when running the command does not
        # change the service's status
        self.systemctl_works = True
        self.ssh_client_class = mock.patch('sat.cli.bootsys.platform.SSHClient').start()
        self.ssh_client = self.ssh_client_class.return_value
        self.ssh_client.exec_command.side_effect = self._fake_ssh_command
        self.ssh_return_values = mock.Mock(), mock.Mock(), mock.Mock()
        self.ssh_return_values[1].channel.recv_exit_status.return_value = 0

        self.waiter = RemoteServiceWaiter(self.host, self.service_name, 'inactive', self.timeout)

    def _fake_ssh_command(self, cmd):
        """Fake the behavior of SSHClient.exec_command."""
        if cmd.startswith('systemctl is-active'):
            self.ssh_return_values[1].read.return_value = self.service_status
        elif cmd.startswith('systemctl is-enabled'):
            self.ssh_return_values[1].read.return_value = self.enabled_status
        if self.systemctl_works:
            if cmd.startswith('systemctl stop'):
                self.service_status = b'inactive\n'
            elif cmd.startswith('systemctl start'):
                self.service_status = b'active\n'
            elif cmd.startswith('systemctl enable'):
                self.enabled_status = b'enabled\n'

        return self.ssh_return_values

    def assert_ssh_connected(self):
        """Assert the SSH client connected to the host."""
        self.ssh_client_class.assert_called_once_with()
        self.ssh_client.load_system_host_keys.assert_called_once_with()
        self.ssh_client.set_missing_host_key_policy.assert_called_once_with(WarningPolicy)
        self.ssh_client.connect.assert_called_once_with(self.host)

    def test_init(self):
        """Test creating a RemoteServiceWaiter."""
        self.assertEqual(self.waiter.timeout, self.timeout)
        self.assertEqual(self.waiter.host, self.host)
        self.assertEqual(self.waiter.service_name, self.service_name)
        self.assertEqual(f'service {self.service_name} inactive on {self.host}',
                         self.waiter.condition_name())

    def test_condition_name_with_enabled(self):
        """Test the condition_name method with target_enabled specified."""
        waiter = RemoteServiceWaiter(self.host, self.service_name, 'active',
                                     self.timeout, target_enabled='enabled')
        self.assertEqual(f'service {self.service_name} active and enabled on {self.host}',
                         waiter.condition_name())

    def test_target_state_validation(self):
        """Test that only valid values for target_state are accepted."""
        valid_vals = ('active', 'inactive')
        invalid_vals = ('', 'ready', 4, None)
        for val in valid_vals:
            RemoteServiceWaiter(self.host, self.service_name, val, self.timeout)
        for val in invalid_vals:
            with self.assertRaisesRegex(ValueError, f'Invalid target state {val}'):
                RemoteServiceWaiter(self.host, self.service_name, val, self.timeout)

    def test_target_enabled_validation(self):
        """Test that only valid values for target_enabled are accepted."""
        valid_vals = ('enabled', 'disabled')
        invalid_vals = ('', 'hibernating', 17)
        for val in valid_vals:
            RemoteServiceWaiter(self.host, self.service_name, 'active', self.timeout,
                                target_enabled=val)
        for val in invalid_vals:
            with self.assertRaisesRegex(ValueError, f'Invalid target enabled {val}'):
                RemoteServiceWaiter(self.host, self.service_name, 'active', self.timeout,
                                    target_enabled=val)

    def test_wait_for_stop(self):
        """When the service stops, the waiter should complete."""
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl stop {self.service_name}'),
                                                       mock.call(f'systemctl is-active {self.service_name}')])

    def test_wait_for_start(self):
        """When the service starts, the waiter should complete."""
        self.waiter.target_state = 'active'
        self.service_status = b'inactive\n'
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl start {self.service_name}'),
                                                       mock.call(f'systemctl is-active {self.service_name}')])

    def test_wait_for_enable_only(self):
        """When target_enabled='enabled', an active but disabled service should be enabled."""
        self.waiter.target_enabled = 'enabled'
        self.waiter.target_state = 'active'
        self.enabled_status = b'disabled\n'
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl is-enabled {self.service_name}'),
                                                       mock.call(f'systemctl enable {self.service_name}')])

    def test_wait_for_start_with_enable(self):
        """When target_enabled='enabled', a disabled service should be enabled."""
        self.waiter.target_enabled = 'enabled'
        self.waiter.target_state = 'active'
        self.service_status = b'inactive\n'
        self.enabled_status = b'disabled\n'
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl start {self.service_name}'),
                                                       mock.call(f'systemctl is-enabled {self.service_name}'),
                                                       mock.call(f'systemctl enable {self.service_name}'),
                                                       mock.call(f'systemctl is-active {self.service_name}')])

    def test_wait_for_start_with_enable_already_enabled(self):
        """When target_enabled='enabled', an already-enabled service should be left alone."""
        self.waiter.target_enabled = 'enabled'
        self.waiter.target_state = 'active'
        self.service_status = b'inactive\n'
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl start {self.service_name}'),
                                                       mock.call(f'systemctl is-enabled {self.service_name}'),
                                                       mock.call(f'systemctl is-active {self.service_name}')])

    def test_wait_for_stop_with_disable(self):
        """When target_enabled='disabled', an enabled service should be disabled."""
        self.waiter.target_enabled = 'disable'
        self.waiter.target_state = 'inactive'
        self.service_status = b'active\n'
        self.enabled_status = b'enabled\n'
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl stop {self.service_name}'),
                                                       mock.call(f'systemctl is-enabled {self.service_name}'),
                                                       mock.call(f'systemctl disable {self.service_name}'),
                                                       mock.call(f'systemctl is-active {self.service_name}')])

    def test_wait_for_stop_with_disable_already_disabled(self):
        """When target_enabled='enabled', an already-enabled service should be left alone."""
        self.waiter.target_enabled = 'disabled'
        self.waiter.target_state = 'inactive'
        self.service_status = b'active\n'
        self.enabled_status = b'disabled\n'
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl stop {self.service_name}'),
                                                       mock.call(f'systemctl is-enabled {self.service_name}'),
                                                       mock.call(f'systemctl is-active {self.service_name}')])

    def test_timeout(self):
        """When the service never stops, the waiter should time out."""
        self.systemctl_works = False
        # fake time so that there is no time spent between iterations, but calls to time.monotonic()
        # make it appear as though time has passed.
        self.waiter.timeout = 2
        self.waiter.poll_interval = 0
        with mock.patch('sat.cli.bootsys.waiting.time.monotonic', side_effect=range(5)):
            with self.assertLogs(level=logging.ERROR):
                self.assertFalse(self.waiter.wait_for_completion())

    def test_nonzero_return(self):
        """When stopping a service returns a nonzero exit code, an error should be logged."""
        self.ssh_return_values[1].channel.recv_exit_status.return_value = 1
        self.systemctl_works = False
        # fake time so that there is no time spent between iterations, but calls to time.monotonic()
        # make it appear as though time has passed.
        self.waiter.timeout = 2
        self.waiter.poll_interval = 0
        with mock.patch('sat.cli.bootsys.waiting.time.monotonic', side_effect=range(5)):
            with self.assertLogs(level=logging.ERROR):
                self.assertFalse(self.waiter.wait_for_completion())

    def test_service_already_stopped(self):
        """When the service is already stopped, just check that it's stopped and return."""
        self.service_status = b'inactive\n'
        self.waiter.wait_for_completion()
        self.ssh_client.exec_command.assert_called_once_with(f'systemctl is-active {self.service_name}')

    def test_unknown_state_stop(self):
        """When stopping a service in 'unknown' state, the waiter should time out."""
        self.service_status = b'unknown\n'
        self.systemctl_works = False
        # fake time so that there is no time spent between iterations, but calls to time.monotonic()
        # make it appear as though time has passed.
        self.waiter.timeout = 2
        self.waiter.poll_interval = 0
        with mock.patch('sat.cli.bootsys.waiting.time.monotonic', side_effect=range(5)):
            with self.assertLogs(level=logging.ERROR):
                self.assertFalse(self.waiter.wait_for_completion())

    def test_unknown_state_start(self):
        """When starting a service in 'unknown' state, the waiter should time out."""
        self.service_status = b'unknown\n'
        self.systemctl_works = False
        self.waiter = RemoteServiceWaiter(self.host, self.service_name, 'active', self.timeout)
        # fake time so that there is no time spent between iterations, but calls to time.monotonic()
        # make it appear as though time has passed.
        self.waiter.timeout = 2
        self.waiter.poll_interval = 0
        with mock.patch('sat.cli.bootsys.waiting.time.monotonic', side_effect=range(5)):
            with self.assertLogs(level=logging.ERROR):
                self.assertFalse(self.waiter.wait_for_completion())


class TestDoPlatformAction(unittest.TestCase):
    """Tests for the do_platform_action function."""

    def setUp(self):
        """Set up mocks."""
        self.known_action = 'start'
        self.mock_first_step = mock.Mock()
        self.mock_second_step = mock.Mock()
        self.mock_steps = {
            self.known_action: [
                PlatformServicesStep('first step', self.mock_first_step),
                PlatformServicesStep('second step', self.mock_second_step)
            ]
            # Not necessary to test another valid action. Code path is the same.
        }
        mock.patch('sat.cli.bootsys.platform.STEPS_BY_ACTION', self.mock_steps).start()

        self.mock_prompt_for_ncn_verification = mock.patch(
            'sat.cli.bootsys.platform.prompt_for_ncn_verification').start()

        self.mock_print = mock.patch('builtins.print').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_invalid_action(self):
        """Test giving an invalid action."""
        invalid_action = 'bounce'
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                do_platform_action(invalid_action)

        expected_err = f'Invalid action "{invalid_action}" to perform on platform services.'
        self.assertEqual(cm.records[0].message, expected_err)

    def test_failed_ncn_verification(self):
        """Test do_platform_action when NCN verification fails."""
        bad_ncn_msg = 'bad NCNs'
        self.mock_prompt_for_ncn_verification.side_effect = FatalPlatformError(bad_ncn_msg)
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                do_platform_action(self.known_action)

        expected_err = f'Not proceeding with platform {self.known_action}: {bad_ncn_msg}'
        self.assertEqual(cm.records[0].message, expected_err)

    def test_do_platform_action_success(self):
        """Test do_platform_action when all steps are successful."""
        with self.assertLogs(level=logging.INFO) as cm:
            do_platform_action(self.known_action)

        self.mock_print.assert_has_calls([
            mock.call('Executing step: first step'),
            mock.call('Executing step: second step')
        ])
        self.assertEqual(cm.records[0].message, 'Executing step: first step')
        self.assertEqual(cm.records[1].message, 'Executing step: second step')

    def test_do_platform_action_failed_step(self):
        """Test do_platform_action when a step fails."""
        self.mock_first_step.side_effect = FatalPlatformError('fail')
        with self.assertLogs(level=logging.INFO) as cm:
            with self.assertRaises(SystemExit):
                do_platform_action(self.known_action)

        self.mock_print.assert_called_once_with("Executing step: first step")
        self.assertEqual(cm.records[0].message, 'Executing step: first step')
        self.assertEqual(cm.records[1].message, 'Fatal error while stopping platform services '
                                                'during step "first step": fail')


class TestDoPlatformStartStop(unittest.TestCase):
    """Tests for the do_platform_start and do_platform_stop functions."""

    def setUp(self):
        """Set up mocks."""
        self.args = Namespace()
        self.mock_do_platform_action = mock.patch('sat.cli.bootsys.platform.do_platform_action').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_do_platform_start(self):
        """Test that do_platform_start correctly calls do_platform_action."""
        do_platform_start(self.args)
        self.mock_do_platform_action.assert_called_once_with('start')

    def test_do_platform_stop(self):
        """Test that do_platform_stop correctly calls do_platform_action."""
        do_platform_stop(self.args)
        self.mock_do_platform_action.assert_called_once_with('stop')


class TestDoContainerdStop(unittest.TestCase):
    """Tests for the do_containerd_stop function."""
    def setUp(self):
        """Set up mocks."""
        self.k8s_ncns = ['ncn-w001', 'ncn-w002', 'ncn-w003', 'ncn-m001', 'ncn-m002']
        self.ncn_groups = {'kubernetes': self.k8s_ncns}
        self.stop_containers = mock.patch('sat.cli.bootsys.platform.stop_containers').start()
        self.mock_do_service_action = mock.patch(
            'sat.cli.bootsys.platform.do_service_action_on_hosts').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_do_containerd_stop(self):
        """Test a basic call of do_containerd_stop."""
        do_containerd_stop(self.ncn_groups)
        self.stop_containers.assert_has_calls([mock.call(ncn) for ncn in self.k8s_ncns],
                                              any_order=True)
        self.mock_do_service_action.assert_called_once_with(self.k8s_ncns,
                                                            'containerd', target_state='inactive')

    def test_do_containerd_stop_error(self):
        """Test a call of do_containerd_stop when there is a SystemExit in one of the threads."""
        self.stop_containers.side_effect = SystemExit
        do_containerd_stop(self.ncn_groups)
        self.stop_containers.assert_has_calls([mock.call(ncn) for ncn in self.k8s_ncns],
                                              any_order=True)
        self.mock_do_service_action.assert_called_once_with(self.k8s_ncns,
                                                            'containerd', target_state='inactive')


class TestDoCephFreeze(unittest.TestCase):
    """Tests for the do_ceph_freeze function."""

    def setUp(self):
        """Set up mocks."""
        # NCN groups are not used by this step of stopping platform services
        self.ncn_groups = {}
        self.ceph_healthy = mock.patch('sat.cli.bootsys.platform.ceph_healthy').start()
        self.ceph_healthy.return_value = True
        self.freeze_ceph = mock.patch('sat.cli.bootsys.platform.freeze_ceph').start()

    def test_do_ceph_freeze_success(self):
        """Test do_ceph_freeze in the successful case."""
        do_ceph_freeze(self.ncn_groups)
        self.ceph_healthy.assert_called_once_with()
        self.freeze_ceph.assert_called_once_with()

    def test_do_ceph_freeze_unhealthy(self):
        """When Ceph is not healthy, do not freeze Ceph."""
        self.ceph_healthy.return_value = False
        with self.assertRaises(FatalPlatformError):
            do_ceph_freeze(self.ncn_groups)
        self.freeze_ceph.assert_not_called()


class TestPromptForNCNVerification(unittest.TestCase):
    """Tests for prompt_for_ncn_verification function."""

    def setUp(self):
        """Set up mocks."""
        self.mock_print = mock.patch('builtins.print').start()

        self.mock_managers = ['ncn-m001', 'ncn-m002', 'ncn-m003']
        self.mock_workers = ['ncn-w001', 'ncn-w002', 'ncn-w003']

        def mock_get_hostnames(subroles):
            if subroles == ['managers']:
                return set(self.mock_managers)
            elif subroles == ['workers']:
                return set(self.mock_workers)
            elif subroles == ['managers', 'workers']:
                return set(self.mock_managers + self.mock_workers)
            else:
                return set()

        self.mock_get_hostnames = mock.patch(
            'sat.cli.bootsys.platform.get_mgmt_ncn_hostnames', mock_get_hostnames).start()

        self.mock_pester_choices = mock.patch(
            'sat.cli.bootsys.platform.pester_choices').start()

    def tearDown(self):
        mock.patch.stopall()

    def assert_printed_messages(self):
        """Helper function to assert proper messages printed."""
        self.mock_print.assert_has_calls([
            mock.call('Identified the following Non-compute Node (NCN) groups as follows.'),
            mock.call(f'managers: {self.mock_managers}'),
            mock.call(f'workers: {self.mock_workers}'),
            mock.call(f'kubernetes: {self.mock_managers + self.mock_workers}')
        ])

    @staticmethod
    def get_empty_group_message(group_names):
        """Helper to get a message for the empty group(s)

        Args:
            group_names (list of str): The list of empty group names.
        """
        return f'Failed to identify members of the following NCN group(s): {group_names}'

    def test_empty_managers(self):
        """Test with no managers identified."""
        self.mock_managers = []
        with self.assertRaises(FatalPlatformError) as err:
            prompt_for_ncn_verification()
        self.assertEqual(str(err.exception), self.get_empty_group_message(['managers']))
        self.assert_printed_messages()

    def test_empty_workers(self):
        """Test with no workers identified."""
        self.mock_workers = []
        with self.assertRaises(FatalPlatformError) as err:
            prompt_for_ncn_verification()
        self.assertEqual(str(err.exception), self.get_empty_group_message(['workers']))
        self.assert_printed_messages()

    def test_empty_managers_and_workers(self):
        """Test with no managers or workers identified."""
        self.mock_managers = []
        self.mock_workers = []
        with self.assertRaises(FatalPlatformError) as err:
            prompt_for_ncn_verification()
        self.assertEqual(str(err.exception),
                         self.get_empty_group_message(['managers', 'workers', 'kubernetes']))
        self.assert_printed_messages()

    def test_groups_confirmed(self):
        """Test with user confirming the identified groups."""
        self.mock_pester_choices.return_value = 'yes'
        ncn_groups = prompt_for_ncn_verification()
        expected_groups = {
            'managers': self.mock_managers,
            'workers': self.mock_workers,
            'kubernetes': self.mock_managers + self.mock_workers
        }
        self.assertEqual(expected_groups, ncn_groups)

    def test_groups_denied(self):
        """Test with user denying the identified groups."""
        self.mock_pester_choices.return_value = 'no'
        err_regex = 'User indicated NCN groups are incorrect'
        with self.assertRaisesRegex(FatalPlatformError, err_regex):
            prompt_for_ncn_verification()


class TestDoServiceActionOnHosts(unittest.TestCase):
    """Tests for do_service_action_on_hosts function."""

    def setUp(self):
        """Set up mocks."""
        self.hosts = ['ncn-w001', 'ncn-w002', 'ncn-w003', 'ncn-m001', 'ncn-m002']
        self.service = 'exampled'
        self.target_state = 'active'
        self.target_enabled = 'enabled'

        # Create a separate RemoteServiceWaiter per host, and default to successful
        self.mock_waiters = [mock.Mock(completed=True) for _ in self.hosts]
        self.mock_waiter = mock.patch('sat.cli.bootsys.platform.RemoteServiceWaiter',
                                      side_effect=self.mock_waiters).start()

    def test_all_successful(self):
        """Test doing a service action when it is successful on all hosts."""
        do_service_action_on_hosts(self.hosts, self.service, self.target_state,
                                   target_enabled=self.target_enabled)
        self.mock_waiter.assert_has_calls([
            mock.call(host, self.service, target_state=self.target_state,
                      timeout=SERVICE_ACTION_TIMEOUT, target_enabled=self.target_enabled)
            for host in self.hosts
        ])
        for waiter in self.mock_waiters:
            waiter.wait_for_completion_async.assert_called_once_with()
            waiter.wait_for_completion_await.assert_called_once_with()

    def test_one_failure(self):
        """Test doing a service action when it fails on a single host."""
        # Pick a host in the middle
        self.mock_waiters[2].completed = False
        err_regex = (f'Failed to ensure {self.service} is {self.target_state} '
                     f'and {self.target_enabled} on all hosts.')
        with self.assertRaisesRegex(FatalPlatformError, err_regex):
            do_service_action_on_hosts(self.hosts, self.service, self.target_state,
                                       target_enabled=self.target_enabled)
        self.mock_waiter.assert_has_calls([
            mock.call(host, self.service, target_state=self.target_state,
                      timeout=SERVICE_ACTION_TIMEOUT, target_enabled=self.target_enabled)
            for host in self.hosts
        ])
        for waiter in self.mock_waiters:
            waiter.wait_for_completion_async.assert_called_once_with()
            waiter.wait_for_completion_await.assert_called_once_with()
