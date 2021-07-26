"""
Unit tests for the ipmi_console module.

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
import io
import logging
import socket
from textwrap import dedent
import unittest
from unittest.mock import Mock, call, patch

from paramiko import BadHostKeyException, AuthenticationException, SSHException


from sat.cli.bootsys.ipmi_console import (
    ConsoleLoggingError,
    IPMIConsoleLogger,
)


class TestIPMIConsoleLogger(unittest.TestCase):
    """Tests for the IPMIConsoleLogger context manager."""

    def setUp(self):
        """Set up mock objects"""
        self.hosts = ['ncn-w002', 'ncn-w003', 'ncn-w004', 'ncn-m001', 'ncn-m002']
        self.username = 'root'
        self.password = 'hunter2'

        self.mock_get_ssh_client = patch('sat.cli.bootsys.ipmi_console.get_ssh_client').start()
        self.mock_ssh_client = self.mock_get_ssh_client.return_value

        self.console_logger = IPMIConsoleLogger(self.hosts, self.username, self.password)

    def tearDown(self):
        """Stop all patches"""
        patch.stopall()

    def test_init(self):
        """Test creation of an IPMIConsoleLogger with default value for always_cleanup."""
        self.assertEqual(self.hosts, self.console_logger.hosts)
        self.assertEqual(self.username, self.console_logger.username)
        self.assertEqual(self.password, self.console_logger.password)
        self.assertEqual([f'{host}-mgmt' for host in self.hosts],
                         self.console_logger.bmc_hostnames)
        self.assertFalse(self.console_logger.always_cleanup)

    def test_init_always_cleanup(self):
        """Test creation of an IPMIConsoleLogger with always_cleanup=True."""
        console_logger = IPMIConsoleLogger(self.hosts, self.username, self.password, always_cleanup=True)
        self.assertEqual(self.hosts, console_logger.hosts)
        self.assertEqual(self.username, console_logger.username)
        self.assertEqual(self.password, console_logger.password)
        self.assertEqual([f'{host}-mgmt' for host in self.hosts],
                         console_logger.bmc_hostnames)
        self.assertTrue(console_logger.always_cleanup)

    def test_ssh_client(self):
        """Test the ssh_client property."""
        ssh_client = self.console_logger.ssh_client
        self.mock_get_ssh_client.assert_called_once_with()
        self.mock_ssh_client.connect.assert_called_once_with(IPMIConsoleLogger.CONSOLE_MONITORING_HOST)
        self.assertEqual(self.mock_ssh_client, ssh_client)

    # Patches are necessary to avoid having to really construct a proper BadHostKeyException
    @patch.object(BadHostKeyException, '__init__', return_value=None)
    @patch.object(BadHostKeyException, '__str__', return_value='')
    def test_ssh_client_errors(self, *args):
        """Test that accessing the ssh_client property raises ConsoleLoggingError if errors occur."""
        caught_errors = [BadHostKeyException, AuthenticationException,
                         SSHException, socket.error]
        for error in caught_errors:
            with self.subTest(error=error):
                self.mock_ssh_client.connect.side_effect = error
                with self.assertRaisesRegex(ConsoleLoggingError, 'Unable to connect to host'):
                    _ = self.console_logger.ssh_client

    def test_get_screen_session_ids_none(self):
        """Test _get_screen_session_ids with none present."""
        screen_ls_output = dedent("""\
            No Sockets found in /run/screens/S-root.
        """)
        self.console_logger._execute_remote_command = Mock(return_value=io.StringIO(screen_ls_output))
        self.assertEqual([], self.console_logger._get_screen_session_ids())
        self.console_logger._execute_remote_command.assert_called_once_with("screen -ls",
                                                                            ignore_error=True)

    def test_get_screen_session_ids_one_non_match(self):
        """Test _get_screen_session_ids with one non-matching one present."""
        screen_ls_output = dedent("""\
            There is a screen on:
            \t16493.joedeveloper\t(Detached)
            1 Socket in /run/screens/S-root.
        """)
        self.console_logger._execute_remote_command = Mock(return_value=io.StringIO(screen_ls_output))
        self.assertEqual([], self.console_logger._get_screen_session_ids())
        self.console_logger._execute_remote_command.assert_called_once_with("screen -ls",
                                                                            ignore_error=True)

    def test_get_screen_session_ids_one_match(self):
        """Test _get_screen_session_ids with one matching one present."""
        matching_screens = [f'16494.{IPMIConsoleLogger.SCREEN_SESSION_PREFIX}ncn-w001']
        screen_ls_output = dedent(f"""\
            There is a screen on:
            \t{matching_screens[0]}\t(Detached)
            1 Socket in /run/screens/S-root.
        """)
        self.console_logger._execute_remote_command = Mock(return_value=io.StringIO(screen_ls_output))
        self.assertEqual(matching_screens, self.console_logger._get_screen_session_ids())
        self.console_logger._execute_remote_command.assert_called_once_with("screen -ls",
                                                                            ignore_error=True)

    def test_get_screen_session_ids_multiple_matches(self):
        """Test _get_screen_session_ids with multiple matches present."""
        matching_screens = [
            f'16795.{IPMIConsoleLogger.SCREEN_SESSION_PREFIX}ncn-w001',
            f'16495.{IPMIConsoleLogger.SCREEN_SESSION_PREFIX}ncn-w002'
        ]
        screen_ls_output = dedent(f"""\
            There are screens on:
            \t{matching_screens[0]}\t(Detached)
            \t16611.janedeveloper\t(Detached)
            \t{matching_screens[1]}\t(Attached)
            \t16611.joedeveloper\t(Detached)
            4 Sockets in /run/screens/S-root.
        """)
        self.console_logger._execute_remote_command = Mock(return_value=io.StringIO(screen_ls_output))
        self.assertEqual(matching_screens, self.console_logger._get_screen_session_ids())
        self.console_logger._execute_remote_command.assert_called_once_with("screen -ls",
                                                                            ignore_error=True)

    def test_get_screen_session_ids_command_failure(self):
        """Test _get_screen_session_ids with the remote command to list them failing."""
        self.console_logger._execute_remote_command = Mock(side_effect=ConsoleLoggingError)
        with self.assertRaises(ConsoleLoggingError):
            self.console_logger._get_screen_session_ids()

    def test_get_screen_session_ids_parse_errors(self):
        """Test _get_screen_session_ids with output that is not in the expect format."""
        matching_screens = [f'16494.{IPMIConsoleLogger.SCREEN_SESSION_PREFIX}ncn-w001']

        screen_ls_output = dedent(f"""\
            There are screens on:

            12345
            \t{matching_screens[0]}\t(Detached)
        """)
        self.console_logger._execute_remote_command = Mock(return_value=io.StringIO(screen_ls_output))
        with self.assertLogs(level=logging.WARNING) as logs:
            result = self.console_logger._get_screen_session_ids()

        self.assertEqual(logs.records[0].message,
                         'Unable to split screen session ID into PID and name components: 12345')
        self.assertEqual(matching_screens, result)

    def set_up_mock_ssh_client(self, exit_status=0, stdout_str='', stderr_str='', ssh_exc_str=''):
        """Set up a mock ssh_client on self.console_logger."""
        # _ssh_client is the underlying attribute used by the property
        self.console_logger._ssh_client = ssh_client = Mock()
        self.mock_stdin = Mock()
        self.mock_stdout = Mock()
        self.mock_stdout.channel.recv_exit_status.return_value = exit_status
        self.mock_stderr = Mock()
        if ssh_exc_str:
            ssh_client.exec_command.side_effect = SSHException(ssh_exc_str)
        else:
            ssh_client.exec_command.return_value = self.mock_stdin, self.mock_stdout, self.mock_stderr
            self.mock_stdout.read = io.StringIO(stdout_str).read
            self.mock_stderr.read = io.StringIO(stderr_str).read

    def test_execute_remote_command_success(self):
        """Test _execute_remote_command when command succeeds."""
        command = 'screen -ls'
        self.set_up_mock_ssh_client()
        result = self.console_logger._execute_remote_command(command)
        self.console_logger.ssh_client.exec_command.assert_called_once_with(command, environment=None)
        self.assertEqual(self.mock_stdout, result)

    def test_execute_remote_command_ssh_exception(self):
        """Test _execute_remote_command when it gets an SSHException."""
        command = 'screen -ls'
        exception_msg = 'Failed to SSH'
        err_regex = (f'Failed to execute command "{command}" on host '
                     f'{self.console_logger.CONSOLE_MONITORING_HOST}: {exception_msg}')
        self.set_up_mock_ssh_client(ssh_exc_str=exception_msg)
        with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
            self.console_logger._execute_remote_command(command)

    def test_execute_remote_command_error(self):
        """Test _execute_remote_command when the command exits with non-zero status."""
        command = 'coordinated_attack.sh'
        stdout_str = 'leeeeeroy jenkins'
        stderr_str = 'game over'
        err_regex = (f'Command "{command}" exited with non-zero exit status: 1, '
                     f'stderr: {stderr_str}, stdout: {stdout_str}')
        self.set_up_mock_ssh_client(exit_status=1, stdout_str=stdout_str, stderr_str=stderr_str)
        with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
            self.console_logger._execute_remote_command(command)

    def test_execute_remote_command_ignore_error(self):
        """Test _execute_remote_command when command exits non-zero but is ignored."""
        command = 'coordinated_attack.sh'
        stdout_str = 'leeeeeroy jenkins'
        stderr_str = 'game over'
        debug_msg = (f'Command "{command}" exited with non-zero exit status: 1, '
                     f'stderr: {stderr_str}, stdout: {stdout_str}')
        self.set_up_mock_ssh_client(exit_status=1, stdout_str=stdout_str, stderr_str=stderr_str)

        with self.assertLogs(level=logging.DEBUG) as logs:
            result = self.console_logger._execute_remote_command(command, ignore_error=True)

        debugs = [r for r in logs.records if r.levelno == logging.DEBUG]
        self.assertEqual(2, len(debugs))
        self.assertEqual(debug_msg, debugs[1].message)
        self.assertEqual(self.mock_stdout, result)

    def test_get_ipmitool_cmd_and_env(self):
        """Test _get_ipmitool_cmd_and_env."""
        bmc_hostname = 'ncn-w001-mgmt'
        command = 'sol activate'
        result = self.console_logger._get_ipmitool_cmd_and_env(bmc_hostname, command)
        self.assertEqual(
            f'ipmitool -U {self.username} -E -H {bmc_hostname} -I lanplus {command}',
            result[0]
        )
        self.assertEqual(
            {'IPMITOOL_PASSWORD': self.password},
            result[1]
        )

    def test_execute_ipmitool_command(self):
        """Test _execute_ipmitool_command."""
        bmc_hostname = 'ncn-m001-mgmt'
        base_command = 'sol deactivate'
        ignore_error = True
        mock_full_cmd = Mock()
        mock_env = Mock()
        self.console_logger._get_ipmitool_cmd_and_env = Mock(
            return_value=(mock_full_cmd, mock_env)
        )
        self.console_logger._execute_remote_command = Mock()
        self.console_logger._execute_ipmitool_command(bmc_hostname, base_command, ignore_error)
        self.console_logger._execute_remote_command.assert_called_once_with(
            mock_full_cmd, ignore_error=ignore_error, environment=mock_env
        )

    def test_quit_existing_screens(self):
        """Test _quit_existing_screens."""
        screen_session_ids = [
            '12345.SAT-console-ncn-m002-mgmt',
            '12346.SAT-console-ncn-m003-mgmt'
        ]
        self.console_logger._get_screen_session_ids = Mock(
            return_value=screen_session_ids
        )
        self.console_logger._execute_remote_command = Mock()
        self.console_logger._quit_existing_screens()
        self.console_logger._execute_remote_command.assert_has_calls([
            call(f'screen -XS {session_id} quit') for session_id in screen_session_ids
        ])

    def test_create_logging_directory(self):
        """Test _create_logging_directory."""
        self.console_logger._execute_remote_command = Mock()
        self.console_logger._create_logging_directory()
        self.console_logger._execute_remote_command.assert_called_once_with(
            f'mkdir -p {IPMIConsoleLogger.CONSOLE_LOG_DIR}'
        )

    def test_start_screen_sessions(self):
        """Test _start_screen_sessions."""
        ipmitool_cmd = 'ipmitool sol activate'
        ipmitool_env = Mock()
        self.console_logger._execute_remote_command = Mock()
        self.console_logger._get_ipmitool_cmd_and_env = Mock(
            return_value=(ipmitool_cmd, ipmitool_env)
        )
        self.console_logger._start_screen_sessions()
        self.console_logger._execute_remote_command.assert_has_calls([
            call(f'screen -L -Logfile '
                 f'{IPMIConsoleLogger.CONSOLE_LOG_DIR}/{IPMIConsoleLogger.CONSOLE_LOG_FILE_PREFIX}{bmc}.log '
                 f'-A -m -d -S {IPMIConsoleLogger.SCREEN_SESSION_PREFIX}{bmc} '
                 f'{ipmitool_cmd}',
                 environment=ipmitool_env)
            for bmc in self.console_logger.bmc_hostnames
        ])

    def test_check_screen_session_active_pass(self):
        """Test that _check_screen_sessions_active returns when all are active"""
        screen_session_ids = [
            f'{str(pid)}.SAT-console-{host}-mgmt'
            for host, pid in zip(self.hosts, range(12345, 12345 + len(self.hosts) + 1))
        ]
        self.console_logger._get_screen_session_ids = Mock(return_value=screen_session_ids)

        self.console_logger._check_screen_sessions_active()

        self.console_logger._get_screen_session_ids.assert_called_once_with()

    def test_check_screen_session_active_one_missing(self):
        """Test that _check_screen_sessions_active raises exception when one is not active."""
        missing_index = 2
        screen_session_ids = [
            f'{str(pid)}.SAT-console-{host}-mgmt'
            for host, pid in zip(self.hosts, range(12345, 12345 + len(self.hosts) + 1))
        ]
        del screen_session_ids[missing_index]
        self.console_logger._get_screen_session_ids = Mock(return_value=screen_session_ids)

        err_regex = fr'No screen session exists for BMC\(s\): {self.hosts[missing_index]}-mgmt'
        with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
            self.console_logger._check_screen_sessions_active()

        self.console_logger._get_screen_session_ids.assert_called_once_with()

    def test_check_screen_session_active_all_missing(self):
        """Test that _check_screen_sessions_active raises exception when none are active."""
        self.console_logger._get_screen_session_ids = Mock(return_value=[])

        err_regex = (fr'No screen session exists for BMC\(s\): '
                     fr'{", ".join([f"{h}-mgmt" for h in self.hosts])}')
        with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
            self.console_logger._check_screen_sessions_active()

        self.console_logger._get_screen_session_ids.assert_called_once_with()

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

    def set_up_enter_exit_mocks(self):
        """Set up mocks for the methods called during __enter__ and __exit__."""
        # This mock is used to detect call order of all the console_logger methods
        self.top_mock = top_mock = Mock()
        self.console_logger._ipmitool_sol_deactivate = top_mock._ipmitool_sol_deactivate
        self.console_logger._quit_existing_screens = top_mock._quit_existing_screens
        self.console_logger._create_logging_directory = top_mock._create_logging_directory
        self.console_logger._start_screen_sessions = top_mock._start_screen_sessions
        # Mock sleep so tests don't take too long
        patch('sat.cli.bootsys.ipmi_console.sleep', top_mock.sleep).start()
        self.console_logger._check_screen_sessions_active = top_mock._check_screen_sessions_active

    def assert_console_logs_started_and_stopped(self):
        """Helper to assert the start and stop methods were called."""
        self.assertEqual(
            self.top_mock.mock_calls,
            [call._ipmitool_sol_deactivate(),
             call._quit_existing_screens(),
             call._create_logging_directory(),
             call._start_screen_sessions(),
             call.sleep(IPMIConsoleLogger.SCREEN_ACTIVE_CHECK_DELAY),
             call._check_screen_sessions_active(),
             call._ipmitool_sol_deactivate(),
             call._quit_existing_screens()]
        )

    def assert_console_logs_started_only(self):
        """Helper to assert only the start methods were called"""
        self.assertEqual(
            self.top_mock.mock_calls,
            [call._ipmitool_sol_deactivate(),
             call._quit_existing_screens(),
             call._create_logging_directory(),
             call._start_screen_sessions(),
             call.sleep(IPMIConsoleLogger.SCREEN_ACTIVE_CHECK_DELAY),
             call._check_screen_sessions_active()]
        )

    def test_basic_start_stop_console_logging(self):
        """Test that IPMIConsoleLogger calls the start/stop scripts for all the BMCs and logs info"""
        self.set_up_enter_exit_mocks()
        with self.assertLogs() as logs:
            with self.console_logger:
                self.assert_console_logs_started_only()
                self.assert_only_start_info_logged(logs)

        self.assert_start_stop_info_logged(logs)
        self.assert_console_logs_started_and_stopped()

    def test_start_console_logging_deactivate_failed(self):
        """Test that IPMIConsoleLogger raises exception if deactivate prior to start fails."""
        self.set_up_enter_exit_mocks()
        deactivate_err = 'failed to deactivate'
        err_regex = (f'Failed to clean up old console logging sessions '
                     f'before starting new ones: {deactivate_err}')
        self.console_logger._ipmitool_sol_deactivate.side_effect = ConsoleLoggingError(deactivate_err)
        with self.assertLogs() as logs:
            with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
                self.console_logger.__enter__()

        self.assert_only_start_info_logged(logs)
        self.assertEqual(self.top_mock.mock_calls, [call._ipmitool_sol_deactivate()])

    def test_start_console_logging_quit_failed(self):
        """Test that IPMIConsoleLogger raises exception if quit prior to start fails."""
        self.set_up_enter_exit_mocks()
        quit_err = 'failed to quit screens'
        err_regex = (f'Failed to clean up old console logging sessions '
                     f'before starting new ones: {quit_err}')
        self.console_logger._quit_existing_screens.side_effect = ConsoleLoggingError(quit_err)
        with self.assertLogs() as logs:
            with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
                self.console_logger.__enter__()

        self.assert_only_start_info_logged(logs)
        self.assertEqual(self.top_mock.mock_calls,
                         [call._ipmitool_sol_deactivate(),
                          call._quit_existing_screens()])

    def test_start_console_logging_create_dir_failed(self):
        """Test that IPMIConsoleLogger raises exception if fails to create logging directory"""
        self.set_up_enter_exit_mocks()
        mkdir_err = 'failed to create dir'
        err_regex = f'Failed to start console logging: {mkdir_err}'
        self.console_logger._create_logging_directory.side_effect = ConsoleLoggingError(mkdir_err)
        with self.assertLogs() as logs:
            with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
                self.console_logger.__enter__()

        self.assert_only_start_info_logged(logs)
        self.assertEqual(self.top_mock.mock_calls,
                         [call._ipmitool_sol_deactivate(),
                          call._quit_existing_screens(),
                          call._create_logging_directory()])

    def test_start_console_logging_start_screens_failed(self):
        """Test that IPMIConsoleLogger raises exception if fails to start screen sessions"""
        self.set_up_enter_exit_mocks()
        start_err = 'failed to start screens'
        err_regex = f'Failed to start console logging: {start_err}'
        self.console_logger._start_screen_sessions.side_effect = ConsoleLoggingError(start_err)
        with self.assertLogs() as logs:
            with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
                self.console_logger.__enter__()

        self.assert_only_start_info_logged(logs)
        self.assertEqual(
            self.top_mock.mock_calls,
            [call._ipmitool_sol_deactivate(),
             call._quit_existing_screens(),
             call._create_logging_directory(),
             call._start_screen_sessions()]
        )

    def test_start_console_logging_check_screens_failed(self):
        """Test that IPMIConsoleLogger raises exception if check for active sessions fails"""
        self.set_up_enter_exit_mocks()
        start_err = 'No screen sessions exist'
        err_regex = f'Failed to start console logging: {start_err}'
        self.console_logger._check_screen_sessions_active.side_effect = ConsoleLoggingError(start_err)
        with self.assertLogs() as logs:
            with self.assertRaisesRegex(ConsoleLoggingError, err_regex):
                self.console_logger.__enter__()

        self.assert_only_start_info_logged(logs)
        self.assert_console_logs_started_only()

    def test_stop_console_logging_deactivate_failed(self):
        """Test that IPMIConsoleLogger logs warning if deactivate during cleanup fails."""
        self.set_up_enter_exit_mocks()
        deactivate_err = 'failed to deactivate'
        self.console_logger._ipmitool_sol_deactivate.side_effect = [None,
                                                                    ConsoleLoggingError(deactivate_err)]
        with self.assertLogs() as logs:
            with self.console_logger:
                self.assert_console_logs_started_only()
                self.assert_only_start_info_logged(logs)

        self.assert_start_stop_info_logged(logs)
        self.assertEqual(
            self.top_mock.mock_calls,
            [call._ipmitool_sol_deactivate(),
             call._quit_existing_screens(),
             call._create_logging_directory(),
             call._start_screen_sessions,
             call.sleep(IPMIConsoleLogger.SCREEN_ACTIVE_CHECK_DELAY),
             call._check_screen_sessions_active(),
             call._ipmitool_sol_deactivate()]
        )
        warnings = [r for r in logs.records if r.levelno == logging.WARNING]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].message,
                         f'Failed to clean up console logging: {deactivate_err}')

    def test_stop_console_logging_quit_failed(self):
        """Test that IPMIConsoleLogger logs warning if quit during cleanup fails."""
        self.set_up_enter_exit_mocks()
        quit_err = 'failed to deactivate'
        self.console_logger._quit_existing_screens.side_effect = [None,
                                                                  ConsoleLoggingError(quit_err)]
        with self.assertLogs() as logs:
            with self.console_logger:
                self.assert_console_logs_started_only()
                self.assert_only_start_info_logged(logs)

        self.assert_start_stop_info_logged(logs)
        self.assert_console_logs_started_and_stopped()
        warnings = [r for r in logs.records if r.levelno == logging.WARNING]
        self.assertEqual(len(warnings), 1)
        self.assertEqual(warnings[0].message,
                         f'Failed to clean up console logging: {quit_err}')

    def test_exception_does_not_stop_logging(self):
        """Console logging continues when handling an exception"""
        self.set_up_enter_exit_mocks()
        with self.assertRaises(ValueError):
            with self.assertLogs() as logs:
                with self.console_logger:
                    self.assert_console_logs_started_only()
                    self.assert_only_start_info_logged(logs)
                    raise ValueError

        self.assert_only_start_info_logged(logs)
        self.assert_console_logs_started_only()

    def test_always_cleanup(self):
        """Console logging stops when handling an exception if always_cleanup is set"""
        self.set_up_enter_exit_mocks()
        self.console_logger.always_cleanup = True

        with self.assertRaises(ValueError):
            with self.assertLogs() as logs:
                with self.console_logger:
                    self.assert_console_logs_started_only()
                    self.assert_only_start_info_logged(logs)
                    raise ValueError

        self.assert_start_stop_info_logged(logs)
        self.assert_console_logs_started_and_stopped()

    def test_exit_does_not_stop_logging(self):
        """Console logging continues when handling a SystemExit"""
        self.set_up_enter_exit_mocks()

        with self.assertRaises(SystemExit):
            with self.assertLogs() as logs:
                with self.console_logger:
                    self.assert_console_logs_started_only()
                    self.assert_only_start_info_logged(logs)
                    raise SystemExit(1)

        self.assert_only_start_info_logged(logs)
        self.assert_console_logs_started_only()

    def test_always_cleanup_with_exit(self):
        """Console logging stops when handling a SystemExit if always_cleanup is set"""
        self.set_up_enter_exit_mocks()
        self.console_logger.always_cleanup = True

        with self.assertRaises(SystemExit):
            with self.assertLogs() as logs:
                with self.console_logger:
                    self.assert_console_logs_started_only()
                    self.assert_only_start_info_logged(logs)
                    raise SystemExit(1)

        self.assert_start_stop_info_logged(logs)
        self.assert_console_logs_started_and_stopped()
