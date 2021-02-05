"""
IPMI console logging support.

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
import logging
import os
import socket

from paramiko import SSHClient, SSHException

from sat.cached_property import cached_property

LOGGER = logging.getLogger(__name__)


class ConsoleLoggingError(Exception):
    """Error occurred during console logging setup or teardown."""
    pass


class IPMIConsoleLogger:
    """A context manager that starts/stops IPMI console logging when entering/exiting.

    When entered, for each host, this context manager will SSH to the
    CONSOLE_MONITORING_HOST and do the following:

    * Deactivate any existing ipmitool serial console connections
    * Quit any existing screen session left from failed boot/shutdown attempts
    * Create a new detached screen session that runs `ipmitool ... sol activate`
      and logs all output to a file.

    When exited, for each host, this context manager will SSH to the
    CONSOLE_MONITORING_HOST and do the following:

    * Deactivate any existing ipmitool serial console connections
    * Quit the screen sessions for each host.
    """
    # SSH to this host to launch screen sessions for ipmitool console monitoring
    CONSOLE_MONITORING_HOST = 'ncn-m001'

    # The prefix for screen sessions created for ipmitool console monitoring
    SCREEN_SESSION_PREFIX = "SAT-console-"

    # The directory where log files are written on CONSOLE_MONITORING_HOST
    CONSOLE_LOG_DIR = '/var/log/cray/console_logs'

    # Prefix for console log files
    CONSOLE_LOG_FILE_PREFIX = 'console-'

    BMC_HOSTNAME_SUFFIX = "-mgmt"

    def __init__(self, hosts, username, password, always_cleanup=False):
        """Create an IPMIConsoleLogger.

        Args:
            hosts: ([str]): A list of hostnames for which to start console
                logging (not BMC hostnames). The suffix in BMC_HOSTNAME_SUFFIX
                will be appended to each one to get the BMC hostname. E.g.,
                ncn-w001 becomes ncn-w001-mgmt.
            username (str): The username for connecting to the console with
                ipmitool
            password (str): The password for connecting to the console with
                ipmitool
            always_cleanup (bool): if True, stop console logging even when
                handling an exception.
        """
        self.hosts = hosts
        self.bmc_hostnames = [f'{host}{self.BMC_HOSTNAME_SUFFIX}' for host in self.hosts]
        self.username = username
        self.password = password
        self.always_cleanup = always_cleanup

    @cached_property
    def ssh_client(self):
        """paramiko.client.SSHClient: The SSH client connected to the console monitoring host.

        Raises:
            ConsoleLoggingError: if there is a failure to connect to the remote monitoring host.
        """
        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        try:
            ssh_client.connect(self.CONSOLE_MONITORING_HOST)
        except (SSHException, socket.error) as err:
            raise ConsoleLoggingError(f'Unable to connect to host {self.CONSOLE_MONITORING_HOST}: {err}')
        return ssh_client

    def _execute_remote_command(self, command, ignore_error=False, environment=None):
        """Execute the given remote command on CONSOLE_MONITORING_HOST.

        Args:
            command (str): The command to execute on the remote host
            ignore_error (bool): If True, do not raise an error for a non-zero
                exit status from `command`. Just log a debug message.
            environment (dict): A dict of environment variables to use when
                executing the remote command.

        Returns:
            The stdout resulting from running self.ssh_client.exec_command.

        Raises:
            ConsoleLoggingError: if the given command fails or exits with
                non-zero exit status and `ignore_error` is False.
        """
        LOGGER.debug('Executing command "%s" on host %s.', command,
                     self.CONSOLE_MONITORING_HOST)
        try:
            stdin, stdout, stderr = self.ssh_client.exec_command(command,
                                                                 environment=environment)
        except SSHException as err:
            raise ConsoleLoggingError(f'Failed to execute command "{command}" on '
                                      f'host {self.CONSOLE_MONITORING_HOST}: {err}')

        exit_status = stdout.channel.recv_exit_status()
        if exit_status:
            message = (f'Command "{command}" exited with non-zero exit status: '
                       f'{exit_status}, stderr: {stderr.read()}, stdout: {stdout.read()}')
            if ignore_error:
                LOGGER.debug(message)
            else:
                raise ConsoleLoggingError(message)

        return stdout

    def _get_ipmitool_cmd_and_env(self, bmc_hostname, base_command):
        """Get a full ipmitool command and environment for the given host and base command.

        Args:
            bmc_hostname (str): the BMC to target with the ipmitool "-H" option
            base_command (str): the command to execute with ipmitool, e.g.
                'sol activate' or 'sol deactivate'.

        Returns:
            A tuple of the full ipmitool command as a string and the environment
            in which it should run as a dict. The environment is used to hide
            the BMC passwords.
        """
        # Tell ipmitool to use the password from the env variable using '-E'
        return (
            f'ipmitool -U {self.username} -E -H {bmc_hostname} -I lanplus {base_command}',
            {'IPMITOOL_PASSWORD': self.password}
        )

    def _execute_ipmitool_command(self, bmc_hostname, base_command, ignore_error=False):
        """Execute the given ipmitool command on the CONSOLE_MONITORING_HOST.

        Args:
            bmc_hostname (str): the host to target with the ipmitool "-H" option.
            base_command (str): the command to execute with ipmitool, e.g.
                'sol activate' or 'sol deactivate'.
            ignore_error (bool): If True, do not raise an error for a non-zero
                exit status from `command`. Just log a debug message.

        Raises:
            ConsoleLoggingError: if ipmitool command fails
        """
        full_command, environment = self._get_ipmitool_cmd_and_env(bmc_hostname, base_command)
        self._execute_remote_command(full_command, ignore_error=ignore_error,
                                     environment=environment)

    def _ipmitool_sol_deactivate(self):
        """Run "ipmitool ... sol deactivate" for each of the BMCs.

        This ensures that the console is freed up to be obtained by a subsequent
        "ipmitool ... sol activate" command.

        Raises:
            ConsoleLoggingError: if any ipmitool command fails
        """
        for bmc_hostname in self.bmc_hostnames:
            # TODO: Test whether it is necessary to allow non-zero exit status
            # This command may exit with non-zero status if sol is not active
            self._execute_ipmitool_command(bmc_hostname, 'sol deactivate', ignore_error=True)

    def _get_screen_session_ids(self):
        """Get the session IDs of screen sessions whose names start with a prefix.

        Returns:
            A list of full IDs of screen sessions whose names start with the given
            prefix.

        Raises:
            ConsoleLoggingError: if there is a failure to get screen session IDs
        """
        matching_session_ids = []
        list_command = 'screen -ls'

        # The command has non-zero exit status if no screen sessions exist
        stdout = self._execute_remote_command(list_command, ignore_error=True)

        for line in stdout.readlines():
            if 'No Sockets found' in line or "Socket in" in line or "Sockets in" in line:
                # No sockets to return or last line of output
                break
            elif "There is a screen on" in line or "There are screens on" in line:
                # First line of output
                continue

            # Strip and extract screen session ID
            stripped = line.strip()
            if not stripped:
                # Blank line
                continue

            # Example:
            # 	16493.my_screen_session_name	(Attached)
            full_session_id = stripped.split(maxsplit=1)[0]

            try:
                session_name = full_session_id.split('.', 1)[1]
            except IndexError:
                LOGGER.warning('Unable to split screen session ID into PID and name '
                               'components: %s', full_session_id)
                continue

            if session_name.startswith(self.SCREEN_SESSION_PREFIX):
                matching_session_ids.append(full_session_id)

        return matching_session_ids

    def _quit_existing_screens(self):
        """Quit existing screen sessions for console monitoring.

        This ensures that there will only be one set of screen sessions for
        monitoring the console of nodes.

        Raises:
            ConsoleLoggingError: if any commands to quit screen sessions failed
        """
        session_ids = self._get_screen_session_ids()
        for session_id in session_ids:
            screen_quit_cmd = f'screen -XS {session_id} quit'
            self._execute_remote_command(screen_quit_cmd)

    def _create_logging_directory(self):
        """Ensure the `self.CONSOLE_LOG_DIR` exists on `self.CONSOLE_MONITORING_HOST`.

        Raises:
            ConsoleLoggingError: if there is a failure to create this directory.
        """
        self._execute_remote_command(f'mkdir -p {self.CONSOLE_LOG_DIR}')

    def _start_screen_sessions(self):
        """Start new screen sessions to monitor console of all hosts.

        Raises:
            ConsoleLoggingError: if failed to execute command to start console
                logs in screen sessions.
        """
        for bmc_hostname in self.bmc_hostnames:
            ipmitool_cmd, environment = self._get_ipmitool_cmd_and_env(bmc_hostname, 'sol activate')
            log_file = os.path.join(self.CONSOLE_LOG_DIR,
                                    f'{self.CONSOLE_LOG_FILE_PREFIX}{bmc_hostname}.log')
            screen_cmd = (
                f'screen -L -Logfile {log_file} '
                f'-A -m -d -S {self.SCREEN_SESSION_PREFIX}{bmc_hostname} {ipmitool_cmd}'
            )
            self._execute_remote_command(screen_cmd, environment=environment)

    def __enter__(self):
        """Start console logging using SSH, screen, and ipmitool

        Raises:
            ConsoleLoggingError: if failed to clean up or start console logging.
        """
        LOGGER.info(f'Starting console logging on {",".join(self.hosts)}.')
        try:
            self._ipmitool_sol_deactivate()
            self._quit_existing_screens()
        except ConsoleLoggingError as err:
            raise ConsoleLoggingError(f'Failed to clean up old console logging sessions '
                                      f'before starting new ones: {err}')
        try:
            self._create_logging_directory()
            self._start_screen_sessions()
        except ConsoleLoggingError as err:
            raise ConsoleLoggingError(f'Failed to start console logging: {err}')

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Stop console logging w/ "ipmitool sol deactivate" and by quitting screen sessions."""
        # Only stop console logging if not handling an exception.  That way, if
        # 'sat bootsys' fails console logging will continue so that the user
        # may debug or investigate.
        if exc_type is None or self.always_cleanup:
            LOGGER.info(f'Stopping console logging on {",".join(self.hosts)}.')
            try:
                self._ipmitool_sol_deactivate()
                self._quit_existing_screens()
            except ConsoleLoggingError as err:
                LOGGER.warning(f'Failed to clean up console logging: {err}')
