"""
Unit tests for the sat.cli.bootsys.ceph module.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
import logging
from io import StringIO
import unittest
from unittest.mock import patch, Mock, call

from paramiko import SSHException
import subprocess
from subprocess import CalledProcessError

from sat.cli.bootsys.ceph import ceph_healthy, freeze_ceph, restart_ceph_services, CephHealthWaiter
from tests.common import ExtendedTestCase


class TestRestartCephServices(ExtendedTestCase):
    """Test restart_ceph_services()"""

    def setUp(self):
        self.mock_ssh_client_cls = patch('sat.cli.bootsys.ceph.SSHClient').start()
        self.mock_ssh_client = self.mock_ssh_client_cls.return_value
        self.mock_connect = self.mock_ssh_client.connect
        self.mock_load_system_host_keys = self.mock_ssh_client.load_system_host_keys
        self.mock_exec_command = self.mock_ssh_client.exec_command
        self.mock_stdin, self.mock_stdout, self.mock_stderr = Mock(), Mock(), Mock()
        self.mock_stdin.channel.recv_exit_status.return_value = 0
        self.mock_stdout.channel.recv_exit_status.return_value = 0
        self.mock_stderr.channel.recv_exit_status.return_value = 0
        self.mock_exec_command.return_value = (self.mock_stdin, self.mock_stdout, self.mock_stderr)

        self.mock_get_ncns = patch('sat.cli.bootsys.ceph.get_mgmt_ncn_hostnames').start()
        self.hosts = ['ncn-s001', 'ncn-s002', 'ncn-s003']
        self.mock_get_ncns.return_value = self.hosts

        self.services_to_restart = ['ceph-mon.target', 'ceph-mgr.target', 'ceph-mds.target']

    def tearDown(self):
        patch.stopall()

    def assert_client(self):
        """Helper for test cases to assert that the SSH client was initialized correctly"""
        self.mock_get_ncns.assert_called_once_with(['storage'])
        self.mock_ssh_client_cls.assert_called_once()
        self.mock_load_system_host_keys.assert_called_once()

    def test_basic_restart(self):
        """Test a basic invocation of restart_ceph_services"""
        restart_ceph_services()
        self.assert_client()
        self.mock_connect.assert_has_calls([call(host) for host in self.hosts])
        self.mock_exec_command.assert_has_calls([call(f'systemctl restart {service}')
                                                 for service in self.services_to_restart] * len(self.hosts))

    def test_connect_failed(self):
        """Test when connecting to a host fails"""
        self.mock_connect.side_effect = SSHException('the system is down')
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                restart_ceph_services()

        self.assert_client()
        self.mock_connect.assert_called_once_with(self.hosts[0])
        self.assert_in_element(f'Connecting to {self.hosts[0]} failed.  Error: the system is down', cm.output)

    def test_command_failed(self):
        """Test when running a command fails"""
        self.mock_exec_command.side_effect = SSHException('the system crashed')
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                restart_ceph_services()

        self.assert_client()
        self.mock_connect.assert_called_once_with(self.hosts[0])
        self.mock_exec_command.assert_called_once_with(f'systemctl restart ceph-mon.target')
        self.assert_in_element(f'Command "systemctl restart ceph-mon.target" failed.  Host: {self.hosts[0]}.  '
                               f'Error: the system crashed', cm.output)

    def test_command_exit_nonzero(self):
        """Test when running a command completes but returns a nonzero exit code"""
        self.mock_stdout.read.return_value = ''
        self.mock_stderr.read.return_value = 'command failed!'
        # stdin/stderr/stdout all have recv_exit_status() set on a nonzero return
        self.mock_stdin.chanel.recv_exit_status.return_value = 1
        self.mock_stdout.channel.recv_exit_status.return_value = 1
        self.mock_stderr.channel.recv_exit_status.return_value = 1

        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                restart_ceph_services()

        self.assert_client()
        self.mock_connect.assert_called_once_with(self.hosts[0])
        self.mock_exec_command.assert_called_once_with('systemctl restart ceph-mon.target')
        self.assert_in_element(f'Command "systemctl restart ceph-mon.target" failed.  Host: {self.hosts[0]}.  '
                               f'Stderr: command failed!', cm.output)


class TestCephWaiter(unittest.TestCase):
    """Tests for the CephHealthWaiter class"""

    def setUp(self):
        self.mock_ssh_client = patch('sat.cli.bootsys.ceph.SSHClient').start()

        # TODO: if the Ceph health criteria change, these will need to
        # be modified. (See SAT-559 for further information.)
        self.HEALTH_OK = StringIO('{"health": {"status": "HEALTH_OK"}}')
        self.HEALTH_WARN = StringIO('{"health": {"status": "HEALTH_WARN"}}')

        self.mock_ssh_client.return_value.exec_command.return_value = (None, self.HEALTH_OK, None)

        self.waiter = CephHealthWaiter(10)

    def tearDown(self):
        patch.stopall()

    def test_ceph_health_connects_ssh(self):
        """Test that CephHealthWaiter connects over SSH properly."""
        self.waiter.has_completed()
        self.mock_ssh_client.return_value.load_system_host_keys.assert_called_once()
        self.mock_ssh_client.return_value.connect.assert_called_once_with(self.waiter.host)
        self.mock_ssh_client.return_value.exec_command.assert_called_once()

    def test_ceph_health_is_ready(self):
        """Test that Ceph readiness is detected."""
        self.assertTrue(self.waiter.has_completed())

    def test_ceph_health_is_not_ready(self):
        """Test that Ceph not being ready is detected."""
        self.mock_ssh_client.return_value.exec_command.return_value = (None, self.HEALTH_WARN, None)
        self.assertFalse(self.waiter.has_completed())

    def test_ceph_health_ssh_broken(self):
        """Test that Ceph health is not complete if there's an SSH problem."""
        self.mock_ssh_client.return_value.exec_command.side_effect = SSHException()
        self.assertFalse(self.waiter.has_completed())

    @patch('sat.cli.bootsys.ceph.json.loads')
    def test_ceph_health_malformed_json(self, mock_json_loads):
        """Test that Ceph health is not complete if Ceph returns malformed JSON."""
        mock_json_loads.side_effect = json.decoder.JSONDecodeError('bad json', 'it is wrong', 0)
        self.assertFalse(self.waiter.has_completed())

    def test_ceph_health_json_bad_schema(self):
        """Test that Ceph health is not complete if the JSON schema is incorrect."""
        self.mock_ssh_client.return_value.exec_command.return_value = (None, StringIO('{"foo": {"bar": "baz"}'), None)
        self.assertFalse(self.waiter.has_completed())


class TestFreezeCeph(ExtendedTestCase):
    """Tests for the freeze_ceph function."""
    def setUp(self):
        """Set up patches."""
        self.ceph_osd_command = patch('sat.cli.bootsys.ceph.subprocess.check_output').start()
        self.ceph_osd_command.side_effect = TestFreezeCeph.fake_ceph_freeze
        self.expected_params = ['noout', 'norecover', 'nobackfill']
        self.expected_calls = [call(['ceph', 'osd', 'set', param], stderr=subprocess.STDOUT)
                               for param in self.expected_params]

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    @staticmethod
    def fake_ceph_freeze(cmd, stderr):
        """Mimic the output of the 'ceph osd set <param>' command"""
        param = cmd[-1]
        return f'{param} is set'.encode()

    def test_freeze_ceph_success(self):
        """Test freeze_ceph in the successful case."""
        with self.assertLogs(level=logging.INFO) as logs:
            freeze_ceph()
        self.assert_in_element('Freezing Ceph', logs.output)
        for expected_param in self.expected_params:
            self.assert_in_element(f'Running command: ceph osd set {expected_param}', logs.output)
            self.assert_in_element(f'Command output: {expected_param} is set', logs.output)
        self.ceph_osd_command.assert_has_calls(self.expected_calls)

    def test_freeze_ceph_failure(self):
        """Test an error is raised when a ceph freezing command fails."""
        self.ceph_osd_command.side_effect = CalledProcessError(returncode=1, cmd='ceph osd set noout')
        with self.assertRaises(RuntimeError):
            freeze_ceph()


class TestCephHealthy(ExtendedTestCase):
    """Tests for the ceph_healthy function."""
    def setUp(self):
        """Set up patches."""
        self.ceph_health_command = patch('sat.cli.bootsys.ceph.subprocess.check_output').start()
        self.HEALTH_OK = json.dumps({'health': {'status': 'HEALTH_OK'}})
        self.HEALTH_ERR = json.dumps({'health': {'status': 'HEALTH_ERR'}})
        self.HEALTH_WARN_OK = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                    'LARGE_OMAP_OBJECTS': {},
                    'TOO_FEW_PGS': {}
                }
            }
        })
        self.HEALTH_WARN_NOT_OK = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                    'POOL_TARGET_SIZE_BYTES_OVERCOMMITTED': {},
                    'TOO_FEW_PGS': {}
                }
            }
        })

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    def test_ceph_healthy(self):
        """Test ceph_healthy returns True when ceph is healthy."""
        self.ceph_health_command.return_value = self.HEALTH_OK
        self.assertTrue(ceph_healthy())
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_unhealthy(self):
        """Test ceph_healthy returns False when ceph is unhealthy with HEALTH_ERR."""
        self.ceph_health_command.return_value = self.HEALTH_ERR
        self.assertFalse(ceph_healthy())
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_warn_healthy(self):
        """Test ceph_healthy returns True when ceph is in an 'acceptable' warning state."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OK
        with self.assertLogs(level=logging.WARNING) as logs:
            self.assertTrue(ceph_healthy())
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])
        self.assert_in_element('Ceph health check failed: LARGE_OMAP_OBJECTS', logs.output)
        self.assert_in_element('Ceph health check failed: TOO_FEW_PGS', logs.output)
        self.assert_in_element('Ceph is healthy with warnings', logs.output)

    def test_ceph_warn_unhealthy(self):
        """Test ceph_healthy returns False when ceph is in an 'unacceptable' warning state."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_NOT_OK
        with self.assertLogs(level=logging.WARNING) as logs:
            self.assertFalse(ceph_healthy())
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])
        self.assert_in_element('Ceph health check failed: TOO_FEW_PGS', logs.output)
        self.assert_in_element('Ceph health check failed: POOL_TARGET_SIZE_BYTES_OVERCOMMITTED', logs.output)
        self.assert_not_in_element('Ceph is healthy with warnings', logs.output)

    def test_ceph_healthy_command_failed(self):
        """Test ceph_healthy when the ceph health command fails."""
        self.ceph_health_command.side_effect = CalledProcessError(returncode=1, cmd='ceph -s --format=json')
        with self.assertLogs(level=logging.ERROR):
            self.assertFalse(ceph_healthy())
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_healthy_malformed_json(self):
        """Test ceph_healthy when the ceph health command returns non-json."""
        self.ceph_health_command.return_value = '{'
        with self.assertLogs(level=logging.ERROR):
            self.assertFalse(ceph_healthy())
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_healthy_missing_key(self):
        """Test ceph_healthy when the ceph health command returns incomplete data."""
        self.ceph_health_command.return_value = json.dumps({'health': {}})
        with self.assertLogs(level=logging.ERROR):
            self.assertFalse(ceph_healthy())
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])
