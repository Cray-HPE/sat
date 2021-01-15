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

from sat.cli.bootsys.platform import do_platform_stop, stop_containers, RemoteServiceWaiter, \
    CONTAINER_STOP_SCRIPT


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

    def test_wait_for_start_with_enable(self):
        """When enable_service = True, a disabled service should be enabled."""
        self.waiter.enable_service = True
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
        """When enable_service = True, an already-enabled service should be left alone."""
        self.waiter.enable_service = True
        self.waiter.target_state = 'active'
        self.service_status = b'inactive\n'
        self.assertTrue(self.waiter.wait_for_completion())
        self.assert_ssh_connected()
        self.ssh_client.exec_command.assert_has_calls([mock.call(f'systemctl is-active {self.service_name}'),
                                                       mock.call(f'systemctl start {self.service_name}'),
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


class TestDoPlatformStop(unittest.TestCase):
    """Tests for the do_platform_stop function."""
    def setUp(self):
        """Set up mocks."""
        self.args = Namespace()
        self.expected_subroles = ['managers', 'workers']
        self.get_mgmt_ncn_hostnames = mock.patch('sat.cli.bootsys.platform.get_mgmt_ncn_hostnames').start()
        self.hosts = ['ncn-w001', 'ncn-w002', 'ncn-w003', 'ncn-m001', 'ncn-m002']
        self.get_mgmt_ncn_hostnames.return_value = self.hosts
        self.stop_containers = mock.patch('sat.cli.bootsys.platform.stop_containers').start()
        self.remote_service_stopped_waiter = mock.patch('sat.cli.bootsys.platform.RemoteServiceWaiter').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_do_platform_stop(self):
        """Test a basic call of do_platform_stop."""
        do_platform_stop(self.args)
        self.get_mgmt_ncn_hostnames.assert_called_once_with(subroles=self.expected_subroles)
        self.stop_containers.assert_has_calls([mock.call(host) for host in self.hosts], any_order=True)
        self.remote_service_stopped_waiter.assert_has_calls(
            [mock.call(host, 'containerd', target_state='inactive', timeout=30) for host in self.hosts]
        )
        self.remote_service_stopped_waiter.return_value.wait_for_completion_async.assert_has_calls(
            [mock.call() for host in self.hosts]
        )
        self.remote_service_stopped_waiter.return_value.wait_for_completion_await.assert_has_calls(
            [mock.call() for host in self.hosts]
        )

    def test_do_platform_stop_error(self):
        """Test a call of do_platform_stop when there is a SystemExit in one of the threads."""
        self.stop_containers.side_effect = SystemExit
        do_platform_stop(self.args)
        self.get_mgmt_ncn_hostnames.assert_called_once_with(subroles=self.expected_subroles)
        self.stop_containers.assert_has_calls([mock.call(host) for host in self.hosts], any_order=True)

    def test_do_platform_stop_waiter_error(self):
        """Test a call of do_platform_stop when there is a RuntimeError in one of the waiters."""
        self.remote_service_stopped_waiter.return_value.has_completed.side_effect = RuntimeError
        do_platform_stop(self.args)
        self.get_mgmt_ncn_hostnames.assert_called_once_with(subroles=self.expected_subroles)
        self.stop_containers.assert_has_calls([mock.call(host) for host in self.hosts], any_order=True)
        self.remote_service_stopped_waiter.return_value.wait_for_completion_async.assert_has_calls(
            [mock.call() for host in self.hosts]
        )

    def test_do_platform_stop_no_ncns(self):
        """When get_mgmt_ncn_hostnames returns no NCNs, exit with an error."""
        self.get_mgmt_ncn_hostnames.return_value = []
        with self.assertLogs(level=logging.ERROR):
            with self.assertRaises(SystemExit):
                do_platform_stop(self.args)
