"""
Start and stop platform services to boot and shut down a Shasta system.

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
from paramiko import SSHClient, SSHException, WarningPolicy
from threading import Thread

from sat.cli.bootsys.util import get_mgmt_ncn_hostnames
from sat.cli.bootsys.waiting import Waiter

LOGGER = logging.getLogger(__name__)

# Get a list of containers using crictl ps. With a 5 minute overall timeout, run up to 50 'crictl ps' commands at
# a time with up to 3 containers per command. Each 'crictl stop' command has a timeout of 5 seconds per container,
# adding up to 15 seconds if they all time out.
CONTAINER_STOP_SCRIPT = (
    'crictl ps -q | '
    'timeout -s 9 5m xargs -n 3 -P 50 '
    'timeout -s 9 --foreground 15s crictl stop --timeout 5'
)


class RemoteServiceWaiter(Waiter):
    """A class to stop a service over SSH and wait for it to be inactive."""
    def __init__(self, host, service_name, target_state, timeout, poll_interval=5, enable_service=False):
        """Construct a new RemoteServiceWaiter.

        Args:
            host (str): the hostname on which to stop the service.
            service_name (str): the name of the service on the remote host.
            target_state (str): the desired state of the service, e.g.
                'active' or 'inactive'
            timeout (int): the timeout, in seconds, for the wait operation.
            poll_interval (int): the interval, in seconds, between polls for
                completion.
            enable_service (bool): if target_state is 'active', then check
                and optionally enable the service. Ignored if target_state is
                not 'active'.
        """
        super().__init__(timeout, poll_interval=poll_interval)
        self.host = host
        self.service_name = service_name
        self.target_state = target_state
        self.enable_service = enable_service
        self.ssh_client = SSHClient()

    def _run_remote_command(self, command, nonzero_error=True):
        """Run the given command on the remote host.

        Args:
            command (str): The command to run on the remote host.
            nonzero_error (bool): If true, raise a RuntimeError for
                non-zero exit codes.

        Returns:
            A 2-tuple of paramiko.channel.ChannelFile objects representing
            stdout and stderr from the command.

        Raises:
            RuntimeError: if the command returned a non-zero exit code
                and nonzero_exit = True.
            SSHException: if the server failed to execute the command.
        """
        stdin, stdout, stderr = self.ssh_client.exec_command(command)
        exit_code = stdout.channel.recv_exit_status()
        if exit_code and nonzero_error:
            error_message = (f'Command {command} on host {self.host} returned non-zero exit code {exit_code}. '
                             f'Stdout: "{stdout.read()}" Stderr: "{stderr.read()}"')
            raise RuntimeError(error_message)

        return stdout, stderr

    def wait_for_completion(self):
        """Wait for completion but catch and log errors, and fail if errors are caught."""
        try:
            return super().wait_for_completion()
        except (RuntimeError, socket.error, SSHException) as e:
            LOGGER.error(e)
            return False

    def condition_name(self):
        return f'service {self.service_name} {self.target_state} on {self.host}'

    def pre_wait_action(self):
        """Connect to remote host and start/stop the service if needed.

        This method will set `self.completed` to True if no action is needed.

        Raises:
            SSHException, socket.error: if connecting to the host fails,
                or if the server failed to execute a command.
            RuntimeError, SSHException: from _run_remote_command.
        """
        systemctl_action = ('stop', 'start')[self.target_state == 'active']
        self.ssh_client.load_system_host_keys()
        self.ssh_client.set_missing_host_key_policy(WarningPolicy)
        self.ssh_client.connect(self.host)
        if self.has_completed():
            self.completed = True
        else:
            self._run_remote_command(f'systemctl {systemctl_action} {self.service_name}')

        # If desired, enable the service
        if self.target_state == 'active' and self.enable_service and self._get_enabled() != 'enabled':
            self._run_remote_command(f'systemctl enable {self.service_name}')

    def _get_active(self):
        """Check whether the service is active or not according to systemctl.

        Returns:
            The string representation of the service's state; e.g.
                'active', 'inactive' or 'unknown'.

        Raises:
            RuntimeError, SSHException: from _run_remote_command.
        """
        # systemctl is-active always exits with a non-zero code if the service is not active
        stdout, stderr = self._run_remote_command(f'systemctl is-active {self.service_name}',
                                                  nonzero_error=False)
        return stdout.read().decode().strip()

    def _get_enabled(self):
        """Check whether the service is enabled or not according to systemctl.

        Returns:
            The string representation of the service's enabled status; e.g.
                'enabled', 'disabled', or 'unknown'.

        Raises:
            RuntimeError, SSHException: from _run_remote_command.
        """
        # systemctl is-enabled always exits with a non-zero code if the service is not active
        stdout, stderr = self._run_remote_command(f'systemctl is-enabled {self.service_name}',
                                                  nonzero_error=False)
        return stdout.read().decode().strip()

    def has_completed(self):
        """Check that the service is active or inactive on the remote host.

        Raises:
            RuntimeError, SSHException: from _get_active.
        """
        current_state = self._get_active()
        return current_state == self.target_state


def stop_containers(host):
    """Stop containers running on a host under containerd using crictl.

    Args:
        host (str): The hostname of the node on which the containers should be
            stopped.

    Returns:
        None

    Raises:
        SystemExit: if connecting to the host failed or if the command exited
            with a non-zero code.
    """
    # Raises SSHException or socket.error
    try:
        ssh_client = SSHClient()
        ssh_client.load_system_host_keys()
        ssh_client.set_missing_host_key_policy(WarningPolicy)
        ssh_client.connect(host)
    except (socket.error, SSHException) as e:
        LOGGER.error(f'Failed to connect to host {host}: {e}')
        raise SystemExit(1)

    stdin, stdout, stderr = ssh_client.exec_command(CONTAINER_STOP_SCRIPT)
    if stdout.channel.recv_exit_status():
        LOGGER.warning(
            f'Stopping containerd containers on host {host} return non-zero exit status. '
            f'Stdout:"{stdout.read()}". Stderr:"{stderr.read()}".'
        )


def do_platform_stop(args):
    """Stop services to shut down a Shasta system.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.

    Returns:
        None
    """
    k8s_ncns = get_mgmt_ncn_hostnames(subroles=['managers', 'workers'])
    if not k8s_ncns:
        LOGGER.error('No Kubernetes NCN hostnames found. Please check the contents of /etc/hosts.')
        raise SystemExit(1)
    container_stop_info_message = (
        f'Stopping containers running under containerd on all Kubernetes NCNs using crictl. Hosts: {k8s_ncns}'
    )
    LOGGER.info(container_stop_info_message)
    print(container_stop_info_message)
    # This currently stops all containers in parallel before stopping containerd
    # on each ncn in parallel.  It probably could be faster if it was all in parallel.
    container_stop_threads = [Thread(target=stop_containers, args=(ncn,)) for ncn in k8s_ncns]
    for thread in container_stop_threads:
        thread.start()
    for thread in container_stop_threads:
        thread.join()

    containerd_stop_info_message = (
        f'Stopping containerd on all Kubernetes NCNs using systemctl. Hosts: {k8s_ncns}'
    )
    LOGGER.info(containerd_stop_info_message)
    print(containerd_stop_info_message)
    containerd_stop_timeout = 30
    containerd_stop_waiters = [RemoteServiceWaiter(ncn, 'containerd', target_state='inactive',
                                                   timeout=containerd_stop_timeout)
                               for ncn in k8s_ncns]
    for waiter in containerd_stop_waiters:
        waiter.wait_for_completion_async()
    for waiter in containerd_stop_waiters:
        waiter.wait_for_completion_await()


def do_platform_start(args):
    """Start services to boot a Shasta system.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    k8s_ncns = get_mgmt_ncn_hostnames(subroles=['managers', 'workers'])
    if not k8s_ncns:
        LOGGER.error('No Kubernetes NCN hostnames found. Please check the contents of /etc/hosts.')
        raise SystemExit(1)
    containerd_start_info_message = (
        f'Starting containerd on all Kubernetes NCNs using systemctl. Hosts: {k8s_ncns}'
    )
    print(containerd_start_info_message)
    LOGGER.info(containerd_start_info_message)
    # Start containerd on each NCN
    containerd_start_timeout = 30
    containerd_start_waiters = [RemoteServiceWaiter(ncn, 'containerd', target_state='active',
                                                    timeout=containerd_start_timeout, enable_service=True)
                                for ncn in k8s_ncns]
    for waiter in containerd_start_waiters:
        waiter.wait_for_completion_async()
    for waiter in containerd_start_waiters:
        waiter.wait_for_completion_await()
