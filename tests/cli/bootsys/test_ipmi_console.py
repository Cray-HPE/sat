"""
Unit tests for the ipmi_console module.

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

from subprocess import CalledProcessError, DEVNULL, PIPE
import unittest
from unittest.mock import call, patch

from sat.cli.bootsys.ipmi_console import IPMIConsoleLogger


class TestIPMIConsoleLogger(unittest.TestCase):
    """Tests for the IPMIConsoleLogger context manager."""
    def setUp(self):
        """Set up mock objects"""
        self.mock_run = patch('sat.cli.bootsys.ipmi_console.run').start()
        self.hosts = ['ncn-w002', 'ncn-w003', 'ncn-w004', 'ncn-m001', 'ncn-m002']
        self.ipmi_console_start_command = '/root/bin/ipmi_console_start.sh'
        self.ipmi_console_stop_command = '/root/bin/ipmi_console_stop.sh'

    def tearDown(self):
        """Stop all patches"""
        patch.stopall()

    def assert_start_stop_info_logged(self, logs):
        """Helper to assert info-level messages were logged for starting and stopping"""
        info_logs = [record for record in logs.records if record.levelname == 'INFO']
        self.assertEqual(len(info_logs), 2)
        self.assertEqual(info_logs[0].message,
                         f'Starting console logging on {",".join(self.hosts)}.')
        self.assertEqual(info_logs[1].message,
                         f'Stopping console logging on {",".join(self.hosts)}.')

    def assert_only_start_info_logged(self, logs):
        """Helper to assert only the 'start' log messages were logged"""
        info_logs = [record for record in logs.records if record.levelname == 'INFO']
        self.assertEqual(len(info_logs), 1)
        self.assertEqual(info_logs[0].message,
                         f'Starting console logging on {",".join(self.hosts)}.')

    def assert_start_stop_oserror_logged(self, logs, expected_error_text):
        """Helper to assert warning-level messages were logged for starting and stopping"""
        warning_logs = [record.message for record in logs.records if record.levelname == 'WARNING']
        self.assertEqual(warning_logs,
                         [f'Failed to start console logging for {host}: '
                          f'{expected_error_text}'
                          for host in self.hosts] +
                         [f'Failed to stop console logging: {expected_error_text}'])

    def assert_start_stop_stdout_stderr_logged(self, logs, stdout, stderr):
        """Helper to assert warning-level messages were logged for starting and stopping with command output"""
        warning_logs = [record.message for record in logs.records if record.levelname == 'WARNING']
        # Only stdout is logged from the start script (SAT-621)
        self.assertEqual(warning_logs,
                         [f'Failed to start console logging for {host}.  Stdout: "{stdout}"'
                          for host in self.hosts] +
                         [f'Failed to stop console logging.  Stdout: "{stdout}".  Stderr: "{stderr}"'])

    def assert_ipmi_start_stop_scripts_called(self):
        """Helper to assert the ipmi scripts were called correctly"""
        self.assertEqual(self.mock_run.mock_calls,
                         [call([self.ipmi_console_start_command, f'{host}-mgmt'],
                               check=True, stdout=PIPE, stderr=DEVNULL)
                          for host in self.hosts] +
                         [call([self.ipmi_console_stop_command],
                               check=True, stdout=PIPE, stderr=PIPE)])

    def assert_only_ipmi_start_scripts_called(self):
        """Helper to assert only the start scripts were called"""
        self.assertEqual(self.mock_run.mock_calls,
                         [call([self.ipmi_console_start_command, f'{host}-mgmt'], check=True,
                               stdout=PIPE, stderr=DEVNULL)
                          for host in self.hosts])

    def test_basic_start_stop_console_logging(self):
        """Test that IPMIConsoleLogger calls the start/stop scripts for all the BMCs and logs info"""
        with self.assertLogs() as logs:
            with IPMIConsoleLogger(self.hosts):
                self.assert_only_ipmi_start_scripts_called()
                self.assert_only_start_info_logged(logs)

        self.assert_start_stop_info_logged(logs)
        self.assert_ipmi_start_stop_scripts_called()

    def test_start_stop_console_logging_command_failed(self):
        """Test that IPMIConsoleLogger logs warnings from a non-zero script exit code"""
        fake_stdout = 'The script failed.'
        fake_stderr = 'Failed to communicate with BMC.'
        self.mock_run.side_effect = CalledProcessError(1, cmd='cmd', output=fake_stdout, stderr=fake_stderr)
        with self.assertLogs() as logs:
            with IPMIConsoleLogger(self.hosts):
                self.assert_only_ipmi_start_scripts_called()
                self.assert_only_start_info_logged(logs)

        self.assert_start_stop_info_logged(logs)
        self.assert_ipmi_start_stop_scripts_called()
        self.assert_start_stop_stdout_stderr_logged(logs, fake_stdout, fake_stderr)

    def test_start_console_logging_script_not_found(self):
        """Test that IPMIConsoleLogger logs warnings when an OSError (e.g. file not found) occurs"""
        self.mock_run.side_effect = OSError('Not found')
        expected_error_text = 'Not found'
        with self.assertLogs() as logs:
            with IPMIConsoleLogger(self.hosts):
                self.assert_only_ipmi_start_scripts_called()
                self.assert_only_start_info_logged(logs)

        self.assert_start_stop_info_logged(logs)
        self.assert_ipmi_start_stop_scripts_called()
        self.assert_start_stop_oserror_logged(logs, expected_error_text)

    def test_exception_does_not_stop_logging(self):
        """Console logging continues when handling an exception"""
        with self.assertRaises(ValueError):
            with self.assertLogs() as logs:
                with IPMIConsoleLogger(self.hosts):
                    self.assert_only_ipmi_start_scripts_called()
                    self.assert_only_start_info_logged(logs)
                    raise ValueError

        self.assert_only_start_info_logged(logs)
        self.assert_only_ipmi_start_scripts_called()

    def test_always_cleanup(self):
        """Console logging stops when handling an exception if always_cleanup is set"""
        with self.assertRaises(ValueError):
            with self.assertLogs() as logs:
                with IPMIConsoleLogger(self.hosts, always_cleanup=True):
                    self.assert_only_ipmi_start_scripts_called()
                    self.assert_only_start_info_logged(logs)
                    raise ValueError

        self.assert_start_stop_info_logged(logs)
        self.assert_ipmi_start_stop_scripts_called()

    def test_exit_does_not_stop_logging(self):
        """Console logging continues when handling a SystemExit"""
        with self.assertRaises(SystemExit):
            with self.assertLogs() as logs:
                with IPMIConsoleLogger(self.hosts):
                    self.assert_only_ipmi_start_scripts_called()
                    self.assert_only_start_info_logged(logs)
                    raise SystemExit(1)

        self.assert_only_start_info_logged(logs)
        self.assert_only_ipmi_start_scripts_called()

    def test_always_cleanup_with_exit(self):
        """Console logging stops when handling a SystemExit if always_cleanup is set"""
        with self.assertRaises(SystemExit):
            with self.assertLogs() as logs:
                with IPMIConsoleLogger(self.hosts, always_cleanup=True):
                    self.assert_only_ipmi_start_scripts_called()
                    self.assert_only_start_info_logged(logs)
                    raise SystemExit(1)

        self.assert_start_stop_info_logged(logs)
        self.assert_ipmi_start_stop_scripts_called()
