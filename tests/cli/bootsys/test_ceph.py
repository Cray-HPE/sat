#
# MIT License
#
# (C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.bootsys.ceph module.
"""
from functools import partial
from io import BytesIO
import json
import logging
import unittest
import socket
import subprocess
from subprocess import CalledProcessError
from unittest.mock import patch, call, MagicMock

from paramiko import SSHException

from sat.cli.bootsys.ceph import (
    CephHealthWaiter,
    CephHealthCheckError,
    check_ceph_health,
    toggle_ceph_freeze_flags
)
from tests.common import ExtendedTestCase


def mock_ceph_exec_command(cmd_str, stdin=b'', stdout=b'', stderr=b''):
    if cmd_str.startswith('cephadm'):
        stdout = b'[{"systemd_unit": "foo"}]'

    return tuple(BytesIO(content) for content in [stdin, stdout, stderr])


class TestCephWaiter(unittest.TestCase):
    """Tests for the CephHealthWaiter class"""

    def setUp(self):
        self.mock_check_ceph_health = patch('sat.cli.bootsys.ceph.check_ceph_health').start()
        self.storage_hosts = [f'ncn-s00{n}' for n in range(1, 4)]
        self.waiter = CephHealthWaiter(10, self.storage_hosts)

        self.mock_ssh_client = MagicMock()
        self.mock_ssh_client.exec_command.side_effect = mock_ceph_exec_command
        patch('sat.cli.bootsys.ceph.get_ssh_client', return_value=self.mock_ssh_client).start()

    def tearDown(self):
        patch.stopall()

    def test_ceph_waiter_healthy(self):
        """Test that CephHealthWaiter is complete when Ceph is healthy."""
        self.assertTrue(self.waiter.has_completed())
        self.mock_check_ceph_health.assert_called_once_with(allow_osdmap_flags=False)

    def test_ceph_waiter_unhealthy(self):
        """Test that CephHealthWaiter is not complete when Ceph is unhealthy."""
        self.mock_check_ceph_health.side_effect = CephHealthCheckError
        self.assertFalse(self.waiter.has_completed())
        self.mock_check_ceph_health.assert_called_once_with(allow_osdmap_flags=False)

    def test_ceph_restart_services(self):
        """Test that Ceph services can be restarted before retrying."""
        self.waiter.on_retry_action()
        self.mock_ssh_client.connect.assert_has_calls([
            call(host) for host in self.storage_hosts
        ])
        self.mock_ssh_client.exec_command.assert_has_calls([
            call('cephadm ls'),
            call('systemctl restart "foo"')
        ])
        self.mock_ssh_client.close.assert_called()

    def test_ceph_restart_services_fails_on_ssh_connect(self):
        """Test that warnings are logged when service restart encounters SSH errors"""
        for exc in [SSHException, socket.error]:
            self.mock_ssh_client.connect.side_effect = exc
            with self.assertLogs(level='WARNING'):
                self.waiter.on_retry_action()
            self.mock_ssh_client.exec_command.assert_not_called()
            self.mock_ssh_client.close.assert_called()

            self.mock_ssh_client.reset_mock()

    def test_ceph_restart_fails_with_cephadm(self):
        """Test that warnings are logged when service restart fails from cephadm call"""
        self.mock_ssh_client.exec_command.side_effect = partial(mock_ceph_exec_command, stderr=b'something went wrong')
        with self.assertLogs(level='WARNING'):
            self.waiter.on_retry_action()
        self.mock_ssh_client.close.assert_called()

    def test_ceph_restart_fails_with_systemctl(self):
        """Test that warnings are logged when service restart fails from cephadm call"""
        call_results = [tuple(BytesIO(stream) for stream in streams) for streams in [
            [b'', b'[{"systemd_unit": "foo"}]', b''],
            [b'', b'', b'something went wrong']
        ]] * 3
        self.mock_ssh_client.exec_command.side_effect = call_results
        with self.assertLogs(level='WARNING'):
            self.waiter.on_retry_action()
        self.mock_ssh_client.close.assert_called()


class TestToggleCephFreezeFlags(ExtendedTestCase):
    """Tests for the freeze_ceph function."""
    def setUp(self):
        """Set up patches."""
        self.ceph_osd_command = patch('sat.cli.bootsys.ceph.subprocess.check_output').start()
        self.ceph_osd_command.side_effect = TestToggleCephFreezeFlags.fake_ceph_freeze
        self.expected_params = ['noout', 'norecover', 'nobackfill']

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    @staticmethod
    def fake_ceph_freeze(cmd, stderr):
        """Mimic the output of the 'ceph osd set <param>' command"""
        param = cmd[-1]
        action = cmd[-2]
        return f'{param} is {action}'.encode()

    def assert_expected_ceph_osd_calls(self, action):
        """Assert the `ceph osd` command was called in the expected way."""
        self.ceph_osd_command.assert_has_calls(
            [call(['ceph', 'osd', action, param], stderr=subprocess.STDOUT)
             for param in self.expected_params]
        )

    def test_freeze_ceph_success(self):
        """Test freezing Ceph in the successful case."""
        with self.assertLogs(level=logging.INFO) as logs:
            toggle_ceph_freeze_flags(freeze=True)
        self.assert_in_element('Freezing Ceph', logs.output)
        for expected_param in self.expected_params:
            self.assert_in_element(f'Running command: ceph osd set {expected_param}', logs.output)
            self.assert_in_element(f'Command output: {expected_param} is set', logs.output)
        self.assert_expected_ceph_osd_calls('set')

    def test_unfreeze_ceph_success(self):
        """Test unfreezing Ceph in the successful case."""
        with self.assertLogs(level=logging.INFO) as logs:
            toggle_ceph_freeze_flags(freeze=False)
        self.assert_in_element('Unfreezing Ceph', logs.output)
        for expected_param in self.expected_params:
            self.assert_in_element(f'Running command: ceph osd unset {expected_param}', logs.output)
            self.assert_in_element(f'Command output: {expected_param} is unset', logs.output)
        self.assert_expected_ceph_osd_calls('unset')

    def test_freeze_ceph_failure(self):
        """Test an error is raised when a ceph freezing command fails."""
        self.ceph_osd_command.side_effect = CalledProcessError(returncode=1, cmd='ceph osd set noout')
        error_regex = 'Failed to freeze Ceph'
        with self.assertRaisesRegex(RuntimeError, error_regex):
            toggle_ceph_freeze_flags(freeze=True)

    def test_unfreeze_ceph_failure(self):
        """Test an error is logged and we exit when a Ceph unfreezing command fails."""
        self.ceph_osd_command.side_effect = CalledProcessError(returncode=1, cmd='ceph osd unset noout')
        error_regex = 'Failed to unfreeze Ceph'
        with self.assertRaisesRegex(RuntimeError, error_regex):
            toggle_ceph_freeze_flags(freeze=False)


class TestCheckCephHealth(ExtendedTestCase):
    """Tests for the check_ceph_health function."""
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
        self.HEALTH_WARN_MISSING_CHECKS = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
            }
        })
        self.HEALTH_WARN_EMPTY_CHECKS = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                }
            }
        })
        self.HEALTH_WARN_OSDMAP_FLAGS_OK = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                    'OSDMAP_FLAGS': {
                        'severity': 'HEALTH_WARN',
                        'summary': {
                            'message': 'noout,nobackfill,norecover flag(s) set'
                        }
                    }
                }
            }
        })
        self.HEALTH_WARN_OSDMAP_FLAGS_NOT_OK = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                    'OSDMAP_FLAGS': {
                        'severity': 'HEALTH_WARN',
                        'summary': {
                           'message': 'full flag(s) set'
                        }
                    }
                }
            }
        })
        self.HEALTH_WARN_OSDMAP_FLAGS_EMPTY_MESSAGE = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                    'OSDMAP_FLAGS': {
                        'severity': 'HEALTH_WARN',
                        'summary': {
                           'message': ''
                        }
                    }
                }
            }
        })
        self.HEALTH_WARN_OSDMAP_FLAGS_EMPTY_DATA = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                    'OSDMAP_FLAGS': {}
                }
            }
        })
        self.HEALTH_WARN_OSDMAP_FLAGS_BAD_TYPE = json.dumps({
            'health': {
                'status': 'HEALTH_WARN',
                'checks': {
                    'OSDMAP_FLAGS': {
                        'severity': 'HEALTH_WARN',
                        'summary': {
                           'message': True
                        }
                    }
                }
            }
        })

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    def test_check_ceph_health(self):
        """Test check_ceph_health returns when ceph is healthy."""
        self.ceph_health_command.return_value = self.HEALTH_OK
        check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_unhealthy(self):
        """Test check_ceph_health raises CephHealthCheckError when ceph is unhealthy with HEALTH_ERR."""
        self.ceph_health_command.return_value = self.HEALTH_ERR
        with self.assertRaisesRegex(CephHealthCheckError, 'Ceph health is not HEALTH_OK or HEALTH_WARN'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_warn_healthy(self):
        """Test check_ceph_health warns and returns when ceph is in an 'acceptable' warning state."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OK
        with self.assertLogs(level=logging.WARNING) as logs:
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])
        self.assert_in_element('Ceph is healthy with warnings: LARGE_OMAP_OBJECTS,TOO_FEW_PGS', logs.output)

    def test_ceph_warn_unhealthy(self):
        """Test check_ceph_health raises CephHealthCheckError when ceph is in an 'unacceptable' warning state."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_NOT_OK
        with self.assertRaisesRegex(
                CephHealthCheckError,
                'The following fatal Ceph health warnings were found: POOL_TARGET_SIZE_BYTES_OVERCOMMITTED'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_warn_missing_checks(self):
        """Test check_ceph_health raises CephHealthCheckError when ceph is HEALTH_WARN but missing the 'checks' key."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_MISSING_CHECKS
        with self.assertRaisesRegex(CephHealthCheckError, 'Ceph JSON response is missing expected key: \'checks\''):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_warn_empty_checks(self):
        """Test check_ceph_health raises CephHealthCheckError when ceph is HEALTH_WARN but has no 'checks' data."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_EMPTY_CHECKS
        with self.assertRaisesRegex(CephHealthCheckError, 'Ceph is in HEALTH_WARN state with unknown warnings.'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_osd_flags_healthy(self):
        """Test check_ceph_health warns and returns when ceph has OSD_FLAGS that are acceptable"""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OSDMAP_FLAGS_OK
        with self.assertLogs(level=logging.WARNING) as logs:
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])
        self.assert_in_element('Ceph is healthy with warnings: OSDMAP_FLAGS', logs.output)

    def test_ceph_osd_flags_healthy_not_allowed(self):
        """Test check_ceph_health raises an error when 'acceptable' OSD flags are set but not allowed."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OSDMAP_FLAGS_OK
        expected_error_regex = 'The OSDMAP_FLAGS check failed. OSD flags: noout,nobackfill,norecover'
        with self.assertRaisesRegex(CephHealthCheckError, expected_error_regex):
            check_ceph_health(allow_osdmap_flags=False)
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_osd_flags_unhealthy(self):
        """Test check_ceph_health raises CephHealthCheckError when ceph has OSD_FLAGS that are not acceptable"""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OSDMAP_FLAGS_NOT_OK
        with self.assertRaisesRegex(CephHealthCheckError, 'The OSDMAP_FLAGS check failed. OSD flags: full'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_osd_flags_missing_data(self):
        """Test check_ceph_health raises CephHealthCheckError when ceph has OSD_FLAGS and missing summary data."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OSDMAP_FLAGS_EMPTY_DATA
        with self.assertRaisesRegex(CephHealthCheckError, 'The OSDMAP_FLAGS check failed with unknown OSD flags.'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_osd_flags_empty_message(self):
        """Test check_ceph_health raises CephHealthCheckError when ceph has OSD_FLAGS and missing summary message."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OSDMAP_FLAGS_EMPTY_MESSAGE
        with self.assertRaisesRegex(CephHealthCheckError, 'The OSDMAP_FLAGS check failed with unknown OSD flags.'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_ceph_osd_flags_wrong_type(self):
        """Test check_ceph_health raises CephHealthCheckError with OSD_FLAGS and unexpected summary data type."""
        self.ceph_health_command.return_value = self.HEALTH_WARN_OSDMAP_FLAGS_BAD_TYPE
        with self.assertRaisesRegex(CephHealthCheckError, 'The OSDMAP_FLAGS check failed with unknown OSD flags.'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_check_ceph_health_command_failed(self):
        """Test check_ceph_health raises CephHealthCheckError when the ceph health command fails."""
        self.ceph_health_command.side_effect = CalledProcessError(returncode=1, cmd='ceph -s --format=json')
        with self.assertRaisesRegex(CephHealthCheckError, 'Failed to check ceph health'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_check_ceph_health_malformed_json(self):
        """Test check_ceph_health when the ceph health command returns non-json."""
        self.ceph_health_command.return_value = '{'
        with self.assertRaisesRegex(CephHealthCheckError, 'Received malformed response from Ceph'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])

    def test_check_ceph_health_missing_key(self):
        """Test check_ceph_health when the ceph health command returns incomplete data."""
        self.ceph_health_command.return_value = json.dumps({'health': {}})
        with self.assertRaisesRegex(CephHealthCheckError, 'Ceph JSON response is missing expected key'):
            check_ceph_health()
        self.ceph_health_command.assert_called_once_with(['ceph', '-s', '--format=json'])
