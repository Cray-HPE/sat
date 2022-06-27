#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.bootsys.platform module.
"""
from argparse import Namespace
from contextlib import contextmanager
import logging
from paramiko import SSHException, WarningPolicy
import socket
import threading
import unittest
from unittest import mock

from sat.cli.bootsys.ceph import CephHealthCheckError
from sat.cli.bootsys.etcd import EtcdInactiveFailure, EtcdSnapshotFailure
from sat.cli.bootsys.platform import (
    CONTAINER_STOP_SCRIPT,
    ContainerStopThread,
    do_ceph_freeze,
    do_ceph_unfreeze,
    do_etcd_snapshot,
    do_etcd_start,
    do_etcd_stop,
    do_platform_action,
    do_platform_start,
    do_platform_stop,
    do_service_action_on_hosts,
    do_stop_containers,
    FatalPlatformError,
    NonFatalPlatformError,
    PlatformServicesStep,
    RemoteServiceWaiter,
    SERVICE_ACTION_TIMEOUT,
)
from sat.cli.bootsys.util import FatalBootsysError


class TestContainerStopThread(unittest.TestCase):
    """Test the ContainerStopThread class."""

    def setUp(self):
        """Set up some mocks and a ContainerStopThread"""
        self.host = 'ncn-w001'
        self.get_ssh_client = mock.patch('sat.cli.bootsys.platform.get_ssh_client').start()
        self.ssh_client = self.get_ssh_client.return_value

        self.cst = ContainerStopThread(self.host)

    def tearDown(self):
        mock.patch.stopall()

    def assert_ssh_connected(self):
        """Assert the SSHClient is created and connected."""
        self.get_ssh_client.assert_called_once_with()
        self.ssh_client.connect.assert_called_once_with(self.host)

    @contextmanager
    def assert_exits_with_err(self, err_msg, log_level=logging.ERROR):
        """Context manager to assert code raises SystemExit(1), logs an error, and sets success to False

        Args:
            err_msg (str): the error message to assert is logged
            log_level (int): the logging level to look for. Used by test methods
                that also need to test that warnings are logged for timeouts.

        Yields:
            The value yielded by `self.assertLogs`.
        """
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=log_level) as logs_cm:
                yield logs_cm

        self.assertFalse(self.cst.success)
        err_log_records = [record for record in logs_cm.records
                           if record.levelno == logging.ERROR]
        self.assertEqual(1, len(err_log_records))
        self.assertEqual(err_msg, err_log_records[0].message)
        self.assertEqual(1, raises_cm.exception.code)

    @contextmanager
    def assert_exits_successfully(self, info_msg):
        """Context manager to assert code raises SystemExit(0), logs an info msg, and sets success to True

        Args:
            info_msg (str): the info message to assert is logged

        Yields:
            The value yielded by `self.assertLogs`.
        """
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.INFO) as logs_cm:
                yield logs_cm

        self.assertTrue(self.cst.success)
        info_log_records = [record for record in logs_cm.records
                            if record.levelno == logging.INFO]
        self.assertEqual(1, len(info_log_records))
        self.assertEqual(info_msg, info_log_records[0].message)
        self.assertEqual(0, raises_cm.exception.code)

    def test_init(self):
        """Test the creation of a new ContainerStopThread."""
        self.assertEqual(self.host, self.cst.host)
        self.assertFalse(self.cst.success)

    def test_err_exit(self):
        """Test the _err_exit method logs an error, raises SystemExit(1), and sets success to False."""
        err_msg = 'error message'
        with self.assert_exits_with_err(err_msg):
            self.cst._err_exit(err_msg)

    def test_success_exit(self):
        """Test the _success_exit method logs info msg, raises SystemExit(0), and sets success to True"""
        info_msg = 'all done'
        with self.assert_exits_successfully(info_msg):
            self.cst._success_exit(info_msg)

    def test_ssh_client_success(self):
        """Test the ssh_client property of ContainerStopThread."""
        ssh_client = self.cst.ssh_client
        self.assertEqual(self.ssh_client, ssh_client)
        self.assert_ssh_connected()
        # Check that the property is cached by accessing it again and verifying
        # that the SSHClient and its methods are not called again.
        _ = self.cst.ssh_client
        # The below assertion uses assert_called_once_with, which will fail if
        # methods are called multiple times.
        self.assert_ssh_connected()

    def test_ssh_client_ssh_exception(self):
        """Test the ssh_client property when SSHException is raised by connect."""
        self.ssh_client.connect.side_effect = SSHException('ssh failed')

        with self.assert_exits_with_err(f'Failed to connect to host {self.host}: ssh failed'):
            _ = self.cst.ssh_client

        self.assert_ssh_connected()

    def test_ssh_client_socket_error(self):
        """Test the ssh_client property when socket.error is raised by connect."""
        self.ssh_client.connect.side_effect = socket.error
        with self.assert_exits_with_err(f'Failed to connect to host {self.host}: '):
            _ = self.cst.ssh_client

        self.assert_ssh_connected()

    def set_up_mock_exec_command(self, exit_status, stdout_bytes, stderr_bytes):
        """Set up mock return value for exec_command method of SSHClient.

        Args:
            exit_status (int): the exit status for recv_exit_status
            stdout_bytes (bytes): the byte string of stdout
            stderr_bytes (bytes): the byte string of stderr
        """
        mock_channel = mock.Mock()
        mock_channel.recv_exit_status.return_value = exit_status
        mock_stdout = mock.Mock()
        mock_stdout.channel = mock_channel
        mock_stdout.read.return_value = stdout_bytes
        mock_stderr = mock.Mock()
        mock_stderr.read.return_value = stderr_bytes
        self.ssh_client.exec_command.return_value = mock.Mock(), mock_stdout, mock_stderr

    def test_run_remote_command_success(self):
        """Test _run_remote_command method in the successful case."""
        self.set_up_mock_exec_command(0, b'containerid1\ncontainerid2\n', b'')
        command = 'crictl ps -q'

        exit_status, stdout, stderr = self.cst._run_remote_command(command)

        self.ssh_client.exec_command.assert_called_once_with(command)
        self.assertEqual(0, exit_status)
        self.assertEqual('containerid1\ncontainerid2\n', stdout)
        self.assertEqual('', stderr)

    def test_run_remote_command_ssh_exception(self):
        """Test _run_remote_command method when exec_command raises SSHException"""
        self.ssh_client.exec_command.side_effect = SSHException('ssh failure')
        command = 'crictl ps -q'

        with self.assert_exits_with_err(f'Failed to execute {command} on {self.host}: ssh failure'):
            self.cst._run_remote_command(command)

        self.ssh_client.exec_command.assert_called_once_with(command)

    def test_run_remote_command_non_zero_exit(self):
        """Test _run_remote_command method when command exits non-zero"""
        self.set_up_mock_exec_command(1, b'', b'containerd down')
        command = 'crictl ps -q'
        err_msg = (f'Command "{command}" on {self.host} exited with exit status 1. '
                   f'stdout: , stderr: containerd down')

        with self.assert_exits_with_err(err_msg):
            self.cst._run_remote_command(command)

        self.ssh_client.exec_command.assert_called_once_with(command)

    def test_run_remote_command_non_zero_exit_ignored(self):
        """Test _run_remote_command method when command exits non-zero"""
        self.set_up_mock_exec_command(1, b'okay', b'just a warning')
        command = 'failing_command'

        exit_status, stdout, stderr = self.cst._run_remote_command(command, err_on_non_zero=False)

        self.ssh_client.exec_command.assert_called_once_with(command)
        self.assertEqual(1, exit_status)
        self.assertEqual('okay', stdout)
        self.assertEqual('just a warning', stderr)

    def test_get_running_containers(self):
        """Test _get_running_containers method."""
        container_ids = [
            '858ce8607776a7c2c3904b742211735818fc1c25100163c5e49a5d2df15332ca',
            '9f93f6c4bd634c789158502a8a3e7bd1a11490e3238b0a9b33e969ed89d95caa',
            'a9d50ed782bdb89f798a1b7d1a78b50cede1a0a76fbfaf84eec2728128b86490',
            'f3575f8e17f1455d183b5464fe67aa478ea1dfe8d4c358400c13f3e8c2653f91'
        ]

        with mock.patch.object(self.cst, '_run_remote_command') as mock_run:
            mock_run.return_value = 0, '\n'.join(container_ids), ''
            running_containers = self.cst._get_running_containers()

        self.assertEqual(container_ids, running_containers)

    def set_up_mock_run_remote_command(self, systemctl_fail=False, containerd_active=True,
                                       stop_timeout=False):
        """Set up a mocked version of _run_remote_command for testing the run method.

        Args:
            systemctl_fail (bool): If True, simulate a failure of 'systemctl is-active'
            containerd_active (bool): Whether containerd is active or not.
            stop_timeout (bool): Whether the stop command should time out and exit non-zero.
        """
        # These don't really matter for the tests
        container_ids = ['a', 'b', 'c', 'd']

        def fake_run_remote_command(command, *args, **kwargs):
            if 'systemctl' in command:
                if systemctl_fail:
                    return 1, '', 'error'
                elif containerd_active:
                    return 0, 'active\n', ''
                else:
                    return 1, 'inactive\n', ''
            elif 'crictl stop' in command:
                if stop_timeout:
                    return 1, '\n'.join(container_ids[:2]), ''
                else:
                    return 0, '\n'.join(container_ids), ''
            else:
                # Unknown command, fail
                self.fail(f'_run_remote_command called with unexpected command "{command}"')

        mock_run = mock.patch.object(self.cst, '_run_remote_command').start()
        mock_run.side_effect = fake_run_remote_command

    def test_run_success(self):
        """Test run method in the successful case."""
        self.set_up_mock_run_remote_command()
        mock_get_containers = mock.patch.object(self.cst, '_get_running_containers').start()
        # On first call, containers are running; on second call, there are none
        mock_get_containers.side_effect = [['a', 'b', 'c'], []]

        with self.assert_exits_successfully(f'All containers stopped on {self.host}.'):
            self.cst.run()

        self.assertEqual(
            [mock.call('systemctl is-active containerd', err_on_non_zero=False),
             mock.call(CONTAINER_STOP_SCRIPT, err_on_non_zero=False)],
            self.cst._run_remote_command.mock_calls
        )
        self.assertEqual([mock.call()] * 2, mock_get_containers.mock_calls)

    def test_run_containerd_inactive(self):
        """Test run method when containerd is inactive."""
        self.set_up_mock_run_remote_command()
        mock_get_containers = mock.patch.object(self.cst, '_get_running_containers').start()
        self.set_up_mock_run_remote_command(containerd_active=False)

        with self.assert_exits_successfully(f'containerd is not active on {self.host} so '
                                            f'there are no containers to stop.'):
            self.cst.run()

        self.cst._run_remote_command.assert_called_once_with('systemctl is-active containerd',
                                                             err_on_non_zero=False)
        mock_get_containers.assert_not_called()

    def test_run_systemctl_failure(self):
        """Test run method when containerd fails to query whether containerd is active."""
        self.set_up_mock_run_remote_command()
        mock_get_containers = mock.patch.object(self.cst, '_get_running_containers').start()
        self.set_up_mock_run_remote_command(systemctl_fail=True)

        with self.assert_exits_with_err(f'Failed to query if containerd is active. '
                                        f'stdout: , stderr: error'):
            self.cst.run()

        self.assertEqual(
            [mock.call('systemctl is-active containerd', err_on_non_zero=False)],
            self.cst._run_remote_command.mock_calls
        )
        mock_get_containers.assert_not_called()

    def test_run_no_running_containers(self):
        """Test run method when there are no running containers."""
        self.set_up_mock_run_remote_command()
        mock_get_containers = mock.patch.object(self.cst, '_get_running_containers').start()
        # On first call, no containers are running
        mock_get_containers.return_value = []

        with self.assert_exits_successfully(f'No containers to stop on {self.host}.'):
            self.cst.run()

        self.assertEqual(
            [mock.call('systemctl is-active containerd', err_on_non_zero=False)],
            self.cst._run_remote_command.mock_calls
        )
        mock_get_containers.assert_called_once_with()

    def test_run_timeout_all_containers_stopped(self):
        """Test run method when the stop command times out, but no containers remain running."""
        self.set_up_mock_run_remote_command(stop_timeout=True)
        mock_get_containers = mock.patch.object(self.cst, '_get_running_containers').start()
        # On first call, containers are running; on second call, there are none
        mock_get_containers.side_effect = [['a', 'b', 'c'], []]

        with self.assert_exits_successfully(f'All containers stopped on {self.host}.') as logs_cm:
            self.cst.run()

        self.assertEqual(
            [mock.call('systemctl is-active containerd', err_on_non_zero=False),
             mock.call(CONTAINER_STOP_SCRIPT, err_on_non_zero=False)],
            self.cst._run_remote_command.mock_calls
        )
        warnings = [record for record in logs_cm.records if record.levelno == logging.WARNING]
        self.assertEqual(1, len(warnings))
        self.assertEqual(f'One or more "crictl stop" commands timed out on {self.host}',
                         warnings[0].message)
        self.assertEqual([mock.call()] * 2, mock_get_containers.mock_calls)

    def test_run_timeout_running_containers_exist(self):
        """Test run method when the stop command times out, and containers remain running."""
        self.set_up_mock_run_remote_command(stop_timeout=True)
        mock_get_containers = mock.patch.object(self.cst, '_get_running_containers').start()
        # On first call, 3 containers are running; on second call, one remains
        mock_get_containers.side_effect = [['a', 'b', 'c'], ['c']]

        err_msg = (f'Failed to stop 1 container(s) on {self.host}. Execute "crictl ps -q" '
                   f'on the host to view running containers.')

        with self.assert_exits_with_err(err_msg, log_level=logging.WARNING) as logs_cm:
            self.cst.run()

        self.assertEqual(
            [mock.call('systemctl is-active containerd', err_on_non_zero=False),
             mock.call(CONTAINER_STOP_SCRIPT, err_on_non_zero=False)],
            self.cst._run_remote_command.mock_calls
        )
        warnings = [record for record in logs_cm.records if record.levelno == logging.WARNING]
        self.assertEqual(1, len(warnings))
        self.assertEqual(f'One or more "crictl stop" commands timed out on {self.host}',
                         warnings[0].message)
        self.assertEqual([mock.call()] * 2, mock_get_containers.mock_calls)


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
        self.get_ssh_client = mock.patch('sat.cli.bootsys.platform.get_ssh_client').start()
        self.ssh_client = self.get_ssh_client.return_value
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
        self.get_ssh_client.assert_called_once_with()
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
        self.mock_args = mock.Mock()
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

        self.mock_get_and_verify_ncn_groups = mock.patch(
            'sat.cli.bootsys.platform.get_and_verify_ncn_groups').start()

        self.mock_print = mock.patch('builtins.print').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_invalid_action(self):
        """Test giving an invalid action."""
        invalid_action = 'bounce'
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                do_platform_action(self.mock_args, invalid_action)

        expected_err = f'Invalid action "{invalid_action}" to perform on platform services.'
        self.assertEqual(cm.records[0].message, expected_err)

    def test_failed_ncn_verification(self):
        """Test do_platform_action when NCN verification fails."""
        bad_ncn_msg = 'bad NCNs'
        self.mock_get_and_verify_ncn_groups.side_effect = FatalBootsysError(bad_ncn_msg)
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                do_platform_action(self.mock_args, self.known_action)

        expected_err = f'Not proceeding with platform {self.known_action}: {bad_ncn_msg}'
        self.assertEqual(cm.records[0].message, expected_err)

    def test_do_platform_action_success(self):
        """Test do_platform_action when all steps are successful."""
        with self.assertLogs(level=logging.INFO) as cm:
            do_platform_action(self.mock_args, self.known_action)

        self.mock_get_and_verify_ncn_groups.assert_called_once_with(self.mock_args.excluded_ncns)
        self.mock_print.assert_has_calls([
            mock.call('Executing step: first step'),
            mock.call('Executing step: second step')
        ])
        self.assertEqual(cm.records[0].message, 'Executing step: first step')
        self.assertEqual(cm.records[1].message, 'Executing step: second step')

    def test_do_platform_action_fatal_step(self):
        """Test do_platform_action when a step fails fatally."""
        self.mock_first_step.side_effect = FatalPlatformError('fail')
        with self.assertLogs(level=logging.INFO) as cm:
            with self.assertRaises(SystemExit):
                do_platform_action(self.mock_args, self.known_action)

        self.mock_get_and_verify_ncn_groups.assert_called_once_with(self.mock_args.excluded_ncns)
        self.mock_print.assert_called_once_with("Executing step: first step")
        self.assertEqual(cm.records[0].message, 'Executing step: first step')
        self.assertEqual(cm.records[0].levelno, logging.INFO)
        self.assertEqual(cm.records[1].message, f'Fatal error in step "first step" of '
                                                f'platform services {self.known_action}: fail')
        self.assertEqual(cm.records[1].levelno, logging.ERROR)

    @mock.patch('sat.cli.bootsys.platform.pester_choices', return_value='no')
    def test_do_platform_action_non_fatal_step_abort(self, mock_pester_choices):
        """Test do_platform_action when a step fails non-fatally, but the user aborts."""
        self.mock_first_step.side_effect = NonFatalPlatformError('fail')
        with self.assertLogs(level=logging.INFO) as cm:
            with self.assertRaises(SystemExit):
                do_platform_action(self.mock_args, self.known_action)

        self.mock_get_and_verify_ncn_groups.assert_called_once_with(self.mock_args.excluded_ncns)
        mock_pester_choices.assert_called_once()
        self.assertEqual([mock.call("Executing step: first step"),
                          mock.call("Aborting.")],
                         self.mock_print.mock_calls)
        self.assertEqual(cm.records[0].message, 'Executing step: first step')
        self.assertEqual(cm.records[0].levelno, logging.INFO)
        self.assertEqual(cm.records[1].message, f'Non-fatal error in step "first step" of '
                                                f'platform services {self.known_action}: fail')
        self.assertEqual(cm.records[1].levelno, logging.WARNING)
        self.assertEqual(cm.records[2].message, 'Aborting.')
        self.assertEqual(cm.records[2].levelno, logging.INFO)

    @mock.patch('sat.cli.bootsys.platform.pester_choices', return_value='yes')
    def test_do_platform_action_non_fatal_step_continue(self, mock_pester_choices):
        """Test do_platform_action when a step fails non-fatally, and the user continues."""
        self.mock_first_step.side_effect = NonFatalPlatformError('fail')
        with self.assertLogs(level=logging.INFO) as cm:
            do_platform_action(self.mock_args, self.known_action)

        self.mock_get_and_verify_ncn_groups.assert_called_once_with(self.mock_args.excluded_ncns)
        mock_pester_choices.assert_called_once()
        self.assertEqual([mock.call("Executing step: first step"),
                          mock.call("Continuing."),
                          mock.call("Executing step: second step")],
                         self.mock_print.mock_calls)
        self.assertEqual(cm.records[0].message, 'Executing step: first step')
        self.assertEqual(cm.records[0].levelno, logging.INFO)
        self.assertEqual(cm.records[1].message, f'Non-fatal error in step "first step" of '
                                                f'platform services {self.known_action}: fail')
        self.assertEqual(cm.records[1].levelno, logging.WARNING)
        self.assertEqual(cm.records[2].message, 'Continuing.')
        self.assertEqual(cm.records[2].levelno, logging.INFO)
        self.assertEqual(cm.records[3].message, 'Executing step: second step')
        self.assertEqual(cm.records[3].levelno, logging.INFO)


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
        self.mock_do_platform_action.assert_called_once_with(self.args, 'start')

    def test_do_platform_stop(self):
        """Test that do_platform_stop correctly calls do_platform_action."""
        do_platform_stop(self.args)
        self.mock_do_platform_action.assert_called_once_with(self.args, 'stop')


class TestDoStopContainers(unittest.TestCase):
    """Tests for the do_stop_containers function."""
    def setUp(self):
        """Set up mocks."""
        self.k8s_ncns = ['ncn-w001', 'ncn-w002', 'ncn-w003', 'ncn-m001', 'ncn-m002']
        self.failed_ncns = failed_ncns = []

        class MockContainerStopThread(threading.Thread):
            """Mock the ContainerStopThread for these tests."""

            def __init__(self, host):
                super().__init__()
                self.host = host
                self.success = False

            def run(self):
                self.success = self.host not in failed_ncns

        self.ncn_groups = {'kubernetes': self.k8s_ncns}
        mock.patch('sat.cli.bootsys.platform.ContainerStopThread', MockContainerStopThread).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_do_stop_containers_threads_executed(self):
        """Test that do_stop_containers calls thread methods appropriately."""
        mock_threads = [mock.Mock(host=ncn, success=True) for ncn in self.k8s_ncns]

        with mock.patch('sat.cli.bootsys.platform.ContainerStopThread') as mock_cst:
            mock_cst.side_effect = mock_threads
            do_stop_containers(self.ncn_groups)

        self.assertEqual([mock.call(ncn) for ncn in self.k8s_ncns],
                         mock_cst.mock_calls)
        for mock_thread in mock_threads:
            self.assertEqual([mock.call.start(), mock.call.join()], mock_thread.mock_calls)

    def test_do_stop_containers_successful(self):
        """Test a do_stop_containers with all successful."""
        do_stop_containers(self.ncn_groups)

    def test_do_stop_containers_errors(self):
        """Test a call of do_stop_containers when there a couple NCNs fail"""
        self.failed_ncns.extend(['ncn-w002', 'ncn-m001'])

        err_regex = r'Failed to stop containers on the following NCN\(s\): ncn-w002, ncn-m001'

        with self.assertRaisesRegex(NonFatalPlatformError, err_regex):
            do_stop_containers(self.ncn_groups)


class TestDoCephFreeze(unittest.TestCase):
    """Tests for the do_ceph_freeze function."""

    def setUp(self):
        """Set up mocks."""
        # NCN groups are not used by this step of stopping platform services
        self.ncn_groups = {}
        self.check_ceph_health = mock.patch('sat.cli.bootsys.platform.check_ceph_health').start()
        self.toggle_ceph_freeze_flags = mock.patch('sat.cli.bootsys.platform.toggle_ceph_freeze_flags').start()

    def test_do_ceph_freeze_success(self):
        """Test do_ceph_freeze in the successful case."""
        do_ceph_freeze(self.ncn_groups)
        self.check_ceph_health.assert_called_once_with()
        self.toggle_ceph_freeze_flags.assert_called_once_with(freeze=True)

    def test_do_ceph_freeze_unhealthy(self):
        """When Ceph is not healthy, do not freeze Ceph."""
        self.check_ceph_health.side_effect = CephHealthCheckError
        with self.assertRaises(FatalPlatformError):
            do_ceph_freeze(self.ncn_groups)
        self.toggle_ceph_freeze_flags.assert_not_called()


class TestDoCephUnfreeze(unittest.TestCase):
    """Tests for the do_ceph_unfreeze function."""

    def setUp(self):
        """Set up mocks."""
        self.ncn_groups = {
            'storage':  ['ncn-s001', 'ncn-s002']
        }
        self.ceph_services = [
            'ceph-osd.target', 'ceph-radosgw.target', 'ceph-mon.target', 'ceph-mgr.target', 'ceph-mds.target'
        ]
        self.toggle_ceph_freeze_flags = mock.patch('sat.cli.bootsys.platform.toggle_ceph_freeze_flags').start()
        self.get_config_value = mock.patch('sat.cli.bootsys.platform.get_config_value').start()
        self.ceph_waiter_cls = mock.patch('sat.cli.bootsys.platform.CephHealthWaiter').start()
        self.ceph_waiter = self.ceph_waiter_cls.return_value

    def test_do_ceph_unfreeze_success(self):
        """Test do_ceph_unfreeze in the successful case."""
        do_ceph_unfreeze(self.ncn_groups)
        self.toggle_ceph_freeze_flags.assert_called_once_with(freeze=False)
        self.get_config_value.assert_called_once_with('bootsys.ceph_timeout')
        self.ceph_waiter_cls.assert_called_once_with(
            self.get_config_value.return_value, self.ncn_groups['storage'], retries=1
        )
        self.ceph_waiter.wait_for_completion.assert_called_once_with()

    def test_do_ceph_unfreeze_unhealthy(self):
        """do_ceph_unfreeze should unfreeze Ceph and wait, raising an error if a healthy state is never reached."""
        self.ceph_waiter.wait_for_completion.return_value = False
        expected_error_regex = 'Ceph is not healthy. Please correct Ceph health and try again.'
        with self.assertRaisesRegex(FatalPlatformError, expected_error_regex):
            do_ceph_unfreeze(self.ncn_groups)
        self.toggle_ceph_freeze_flags.assert_called_once_with(freeze=False)
        self.get_config_value.assert_called_once_with('bootsys.ceph_timeout')
        self.ceph_waiter_cls.assert_called_once_with(
            self.get_config_value.return_value, self.ncn_groups['storage'], retries=1
        )
        self.ceph_waiter.wait_for_completion.assert_called_once_with()


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


class TestDoEtcdSnapshotStartStop(unittest.TestCase):
    """Test the do_etcd_snapshot, do_etcd_stop, and do_etcd_start functions."""

    def setUp(self):
        """Set up some mocks and input data."""
        self.managers = ['ncn-m001', 'ncn-m002', 'ncn-m003']
        self.ncn_groups = {'managers': self.managers}

        self.mock_save_snapshot = mock.patch('sat.cli.bootsys.platform'
                                             '.save_etcd_snapshot_on_host').start()
        self.mock_do_service_action = mock.patch('sat.cli.bootsys.platform'
                                                 '.do_service_action_on_hosts').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_do_etcd_snapshot_success(self):
        """Test do_etcd_snapshot in with no errors."""
        do_etcd_snapshot(self.ncn_groups)
        self.mock_save_snapshot.assert_has_calls([mock.call(manager) for manager in self.managers])

    def test_do_etcd_snapshot_all_etcd_inactive(self):
        """Test do_etcd_snapshot when etcd is inactive on all managers."""
        self.mock_save_snapshot.side_effect = [EtcdInactiveFailure('etcd inactive')] * len(self.managers)
        err_regex = f'Failed to create etcd snapshot on hosts: {", ".join(self.managers)}'

        with self.assertRaisesRegex(NonFatalPlatformError, err_regex):
            with self.assertLogs(level=logging.WARNING) as logs:
                do_etcd_snapshot(self.ncn_groups)

        self.assertEqual(len(self.managers), len(logs.records))
        log_messages = [record.message for record in logs.records]
        for manager in self.managers:
            self.assertIn(f'Failed to create etcd snapshot on {manager}: etcd inactive',
                          log_messages)

    def test_do_etcd_snapshot_one_etcd_inactive(self):
        """Test do_etcd_snapshot when etcd is inactive on one manager."""
        self.mock_save_snapshot.side_effect = [
            None,                                  # ncn-m001
            EtcdInactiveFailure('etcd inactive'),  # ncn-m002
            None,                                  # ncn-m003
        ]
        err_regex = 'Failed to create etcd snapshot on hosts: ncn-m002'

        with self.assertRaisesRegex(NonFatalPlatformError, err_regex):
            with self.assertLogs(level=logging.WARNING) as logs:
                do_etcd_snapshot(self.ncn_groups)

        self.assertEqual(1, len(logs.records))
        self.assertEqual('Failed to create etcd snapshot on ncn-m002: etcd inactive',
                         logs.records[0].message)

    def test_do_etcd_snapshot_one_failure(self):
        """Test do_etcd_snapshot when etcd ommand failed on one manager."""
        self.mock_save_snapshot.side_effect = [
            None,                                  # ncn-m001
            EtcdSnapshotFailure('etcd failure'),   # ncn-m002
            None,                                  # ncn-m003
        ]
        err_regex = 'Failed to create etcd snapshot on hosts: ncn-m002'

        with self.assertRaisesRegex(FatalPlatformError, err_regex):
            with self.assertLogs(level=logging.ERROR) as logs:
                do_etcd_snapshot(self.ncn_groups)

        self.assertEqual(1, len(logs.records))
        self.assertEqual('Failed to create etcd snapshot on ncn-m002: etcd failure',
                         logs.records[0].message)

    def test_do_etcd_snapshot_one_inactive_one_failure(self):
        """Test do_etcd_snapshot when etcd inactive on on manager, failed command on another."""
        self.mock_save_snapshot.side_effect = [
            None,                                  # ncn-m001
            EtcdInactiveFailure('etcd inactive'),  # ncn-m002
            EtcdSnapshotFailure('etcd failure'),   # ncn-m003
        ]
        err_regex = 'Failed to create etcd snapshot on hosts: ncn-m002, ncn-m003'

        with self.assertRaisesRegex(FatalPlatformError, err_regex):
            with self.assertLogs(level=logging.WARNING) as logs:
                do_etcd_snapshot(self.ncn_groups)

        self.assertEqual(2, len(logs.records))
        self.assertEqual('Failed to create etcd snapshot on ncn-m002: etcd inactive',
                         logs.records[0].message)
        self.assertEqual(logging.WARNING, logs.records[0].levelno)
        self.assertEqual('Failed to create etcd snapshot on ncn-m003: etcd failure',
                         logs.records[1].message)
        self.assertEqual(logging.ERROR, logs.records[1].levelno)

    def test_do_etcd_stop(self):
        """Test that do_etcd_stop function properly calls do_service_action_on_hosts."""
        do_etcd_stop(self.ncn_groups)
        self.mock_do_service_action.assert_called_once_with(self.managers, 'etcd',
                                                            target_state='inactive')

    def test_do_etcd_start(self):
        """Test that do_etcd_start function properly calls do_service_action_on_hosts."""
        do_etcd_start(self.ncn_groups)
        self.mock_do_service_action.assert_called_once_with(self.managers, 'etcd',
                                                            target_state='active',
                                                            target_enabled='enabled')
