#
# MIT License
#
# (C) Copyright 2021, 2023 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.bootsys.etcd module.
"""
import socket
import unittest
from unittest import mock

from paramiko import SSHException

from sat.cli.bootsys.etcd import (EtcdInactiveFailure, EtcdSnapshotFailure,
                                  save_etcd_snapshot_on_host)


class TestSaveEtcdSnapshotOnHost(unittest.TestCase):
    """Tests for the save_etcd_snapshot_on_host function."""

    def setUp(self):
        """Set up some mocks."""
        self.hostname = 'ncn-m001'
        self.mock_get_ssh_client = mock.patch('sat.cli.bootsys.etcd.get_ssh_client').start()
        self.mock_ssh_client = self.mock_get_ssh_client.return_value
        # Whether the corresponding exec_command should raise SSHException
        self.systemctl_raises = False
        self.mkdir_raises = False
        self.etcdctl_raises = False
        # Exit status for corresponding exec_command
        self.systemctl_exit_status = 0
        self.mkdir_exit_status = 0
        self.etcdctl_exit_status = 0
        # stdout and stderr for every exec_command
        self.stderr_str = 'error'
        self.stdout_str = 'output'

        def fake_exec_command(cmd):
            if "systemctl" in cmd:
                should_raise = self.systemctl_raises
                exit_status = self.systemctl_exit_status
            elif "mkdir" in cmd:
                should_raise = self.mkdir_raises
                exit_status = self.mkdir_exit_status
            elif "etcdctl" in cmd:
                should_raise = self.etcdctl_raises
                exit_status = self.etcdctl_exit_status
            else:
                should_raise = False
                exit_status = 0

            if should_raise:
                raise SSHException()

            fake_stdout = mock.Mock()
            fake_stdout.channel.recv_exit_status.return_value = exit_status
            fake_stdout.read.return_value = self.stdout_str
            fake_stderr = mock.Mock()
            fake_stderr.read.return_value = self.stderr_str

            return mock.Mock(), fake_stdout, fake_stderr

        self.mock_ssh_client.exec_command.side_effect = fake_exec_command

    def tearDown(self):
        mock.patch.stopall()

    def assert_ssh_client_connect(self):
        """Assert the SSHClient was created and connected to the hostname."""
        self.mock_get_ssh_client.assert_called_once()
        self.mock_ssh_client.connect.assert_called_once_with(self.hostname)

    def assert_exec_commands(self):
        """Assert the appropriate exec_command calls were made on the SSHClient."""
        expected_calls = [mock.call('systemctl is-active etcd')]
        if not (self.systemctl_raises or self.systemctl_exit_status):
            expected_calls.append(mock.call('mkdir -p /root/etcd_backup'))
            if not (self.mkdir_raises or self.mkdir_exit_status):
                expected_calls.append(mock.call(
                    'ETCDCTL_API=3 etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt '
                    '--cert /etc/kubernetes/pki/etcd/peer.crt '
                    '--key /etc/kubernetes/pki/etcd/peer.key '
                    'snapshot save /root/etcd_backup/backup.db'
                ))

        self.mock_ssh_client.exec_command.assert_has_calls(expected_calls)

    def test_save_etcd_snapshot_successful(self):
        """Test saving an etcd snapshot on a host in the successful case."""
        save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.assert_exec_commands()

    def test_save_etcd_snapshot_ssh_exception(self):
        """Test saving an etcd snapshot on a host when connect raises SSHException."""
        self.mock_ssh_client.connect.side_effect = SSHException

        with self.assertRaisesRegex(EtcdSnapshotFailure, f'Failed to connect to {self.hostname}'):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.mock_ssh_client.exec_command.assert_not_called()

    def test_save_etcd_snapshot_socket_error(self):
        """Test saving an etcd snapshot on a host when connect raises a socket.error."""
        self.mock_ssh_client.connect.side_effect = socket.error

        with self.assertRaisesRegex(EtcdSnapshotFailure, f'Failed to connect to {self.hostname}'):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.mock_ssh_client.exec_command.assert_not_called()

    def test_save_etcd_snapshot_systemctl_failure(self):
        """Test saving an etcd snapshot on a host when systemctl command raises SSHException."""
        self.systemctl_raises = True
        err_regex = f'Failed to determine if etcd is active on {self.hostname}'

        with self.assertRaisesRegex(EtcdSnapshotFailure, err_regex):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.assert_exec_commands()

    def test_save_etcd_snapshot_etcd_inactive(self):
        """Test saving an etcd snapshot on a host when etcd is not active."""
        self.systemctl_exit_status = 1
        err_regex = f'The etcd service is not active on {self.hostname}'

        with self.assertRaisesRegex(EtcdInactiveFailure, err_regex):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.assert_exec_commands()

    def test_save_etcd_snapshot_mkdir_ssh_exception(self):
        """Test saving an etcd snapshot when mkdir command raises SSHException."""
        self.mkdir_raises = True
        err_regex = f'Failed to execute "mkdir .*" on {self.hostname}'

        with self.assertRaisesRegex(EtcdSnapshotFailure, err_regex):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.assert_exec_commands()

    def test_save_etcd_snapshot_mkdir_non_zero_exit(self):
        """Test saving an etcd snapshot when mkdir command exits non-zero."""
        self.mkdir_exit_status = 1
        err_regex = f'Command "mkdir .*" on {self.hostname} exited with non-zero exit status'

        with self.assertRaisesRegex(EtcdSnapshotFailure, err_regex):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.assert_exec_commands()

    def test_save_etcd_snapshot_etcdctl_ssh_exception(self):
        """Test saving an etcd snapshot when etcdctl command raises SSHException."""
        self.etcdctl_raises = True
        err_regex = f'Failed to execute ".* etcdctl .* snapshot save .*" on {self.hostname}'

        with self.assertRaisesRegex(EtcdSnapshotFailure, err_regex):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.assert_exec_commands()

    def test_save_etcd_snapshot_etcdctl_non_zero_exit(self):
        """Test saving an etcd snapshot when etcdctl command exits non-zero."""
        self.etcdctl_exit_status = 1
        err_regex = (f'Command ".* etcdctl .* snapshot save .*" on {self.hostname} '
                     f'exited with non-zero exit status')

        with self.assertRaisesRegex(EtcdSnapshotFailure, err_regex):
            save_etcd_snapshot_on_host(self.hostname)

        self.assert_ssh_client_connect()
        self.assert_exec_commands()


if __name__ == '__main__':
    unittest.main()
