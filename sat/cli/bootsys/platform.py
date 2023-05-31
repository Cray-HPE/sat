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
Start and stop platform services to boot and shut down a Shasta system.
"""

import logging
import socket
from collections import namedtuple
from threading import Thread

from csm_api_client.k8s import load_kube_api
from fabric import SerialGroup, ThreadingGroup
from fabric.exceptions import GroupException
from kubernetes.client import BatchV1Api
from kubernetes.config import ConfigException

from sat.cached_property import cached_property
from sat.cli.bootsys.ceph import (
    check_ceph_health,
    toggle_ceph_freeze_flags,
    CephHealthCheckError,
    CephHealthWaiter
)
from sat.cli.bootsys.etcd import save_etcd_snapshot_on_host, EtcdInactiveFailure, EtcdSnapshotFailure
from sat.cli.bootsys.util import get_and_verify_ncn_groups, get_ssh_client, FatalBootsysError
from sat.config import get_config_value
from sat.cronjob import recreate_namespaced_stuck_cronjobs
from sat.util import BeginEndLogger, pester_choices, prompt_continue
from sat.waiting import Waiter

LOGGER = logging.getLogger(__name__)

# Get a list of containers using crictl ps. With a 5 minute overall timeout, run up to 50 'crictl ps' commands at
# a time with up to 3 containers per command. Each 'crictl stop' command has a timeout of 5 seconds per container,
# adding up to 15 seconds if they all time out.
CONTAINER_STOP_SCRIPT = (
    'crictl ps -q | '
    'timeout -s 9 5m xargs -n 3 -P 50 '
    'timeout -s 9 --foreground 15s crictl stop --timeout 5'
)
# Default timeout in seconds for service start/stop actions
SERVICE_ACTION_TIMEOUT = 30


class FatalPlatformError(Exception):
    """A fatal error occurred during the shutdown or startup of platform services.

    If this error is raised by a step, the stage will be aborted, and the admin
    will have to try again.
    """
    pass


class NonFatalPlatformError(Exception):
    """A non-fatal error occurred during the shutdown or startup of platform services.

    If this error is raised by a step, we will prompt the admin if they want to
    continue with the stage or exit.
    """
    pass


class RemoteServiceWaiter(Waiter):
    """Start/stop and optionally enable/disable a service over SSH and wait for it to reach target state."""

    VALID_TARGET_STATE_VALUES = ('active', 'inactive')
    VALID_TARGET_ENABLED_VALUES = ('enabled', 'disabled')

    def __init__(self, host, service_name, target_state, timeout, poll_interval=5, target_enabled=None):
        """Construct a new RemoteServiceWaiter.

        Args:
            host (str): the hostname on which to operate.
            service_name (str): the name of the service on the remote host.
            target_state (str): the desired state of the service, e.g.
                'active' or 'inactive'
            timeout (int): the timeout, in seconds, for the wait operation.
            poll_interval (int): the interval, in seconds, between polls for
                completion.
            target_enabled (str or None): If 'enabled', enable the service.
                If 'disabled', disable the service. If None, do neither.
        """
        super().__init__(timeout, poll_interval=poll_interval)

        # Validate input
        if target_state not in self.VALID_TARGET_STATE_VALUES:
            raise ValueError(f'Invalid target state {target_state}. '
                             f'Must be one of {self.VALID_TARGET_STATE_VALUES}')
        if target_enabled is not None and target_enabled not in self.VALID_TARGET_ENABLED_VALUES:
            raise ValueError(f'Invalid target enabled {target_enabled}. '
                             f'Must be one of {self.VALID_TARGET_ENABLED_VALUES}')

        self.host = host
        self.service_name = service_name
        self.target_state = target_state
        self.target_enabled = target_enabled
        self.ssh_client = get_ssh_client()

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
        LOGGER.debug('Executing command "%s" on host %s', command, self.host)
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
        return (f'service {self.service_name} {self.target_state} '
                f'{f"and {self.target_enabled} " if self.target_enabled else ""}'
                f'on {self.host}')

    def pre_wait_action(self):
        """Connect to remote host and start/stop the service if needed.

        This method will set `self.completed` to True if no action is needed.

        Raises:
            SSHException, socket.error: if connecting to the host fails,
                or if the server failed to execute a command.
            RuntimeError, SSHException: from _run_remote_command.
        """
        systemctl_action = ('stop', 'start')[self.target_state == 'active']
        self.ssh_client.connect(self.host)
        if self.has_completed():
            self.completed = True
        else:
            LOGGER.debug('Found service not in %s state on host %s.', self.target_state, self.host)
            self._run_remote_command(f'systemctl {systemctl_action} {self.service_name}')

        if self.target_enabled and self._get_enabled() != self.target_enabled:
            LOGGER.debug('Found service not in %s state on host %s.', self.target_enabled, self.host)
            systemctl_action = ('disable', 'enable')[self.target_enabled == 'enabled']
            self._run_remote_command(f'systemctl {systemctl_action} {self.service_name}')

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


class ContainerStopThread(Thread):
    """A thread that will stop containers on hosts."""
    def __init__(self, host):
        """Create a thread to stop containers in containerd on the given host.

        Args:
            host (str): The host on which to stop containers in containerd
        """
        super().__init__()
        self.host = host
        self.success = False

    @cached_property
    def ssh_client(self):
        """paramiko.SSHClient: an SSHClient connected to `self.host`

        Raises:
            SystemExit(1): if there is a failure to connect to `self.host`.
        """
        try:
            ssh_client = get_ssh_client()
            ssh_client.connect(self.host)
            return ssh_client
        except (socket.error, SSHException) as err:
            self._err_exit(f'Failed to connect to host {self.host}: {err}')

    def _run_remote_command(self, cmd, err_on_non_zero=True):
        """Run the given command on `self.host`.

        Args:
            cmd (str): The command to run on `self.host`.
            err_on_non_zero (bool): If True, error on non-zero exit status. If
                False, simply return the non-zero exit status.

        Returns:
            Tuple of:
                exit_status (int): The exit status of the command
                stdout (str): the stdout of the command decoded with utf-8
                stderr (str): the stderr of the command decoded with utf-8

        Raises:
            SystemExit(1): if the command failed to execute on the remote host.
        """
        try:
            _, stdout, stderr = self.ssh_client.exec_command(cmd)
        except (SSHException, socket.error) as err:
            self._err_exit(f'Failed to execute {cmd} on {self.host}: {err}')
        else:
            exit_status = stdout.channel.recv_exit_status()
            stdout_str = stdout.read().decode()
            stderr_str = stderr.read().decode()

            if exit_status and err_on_non_zero:
                self._err_exit(f'Command "{cmd}" on {self.host} exited with exit status {exit_status}. '
                               f'stdout: {stdout_str}, stderr: {stderr_str}')

            return exit_status, stdout_str, stderr_str

    def _err_exit(self, err_msg):
        """Log an error message, mark failure, and exit thread.

        Args:
            err_msg (str): The error message to log.

        Raises:
            SystemExit(1): unconditionally
        """
        LOGGER.error(err_msg)
        self.success = False
        raise SystemExit(1)

    def _success_exit(self, info_msg):
        """Log an info message, mark success, and exit thread.

        Args:
            info_msg (str): The info message to log.

        Raises:
            SystemExit(0): unconditionally
        """
        LOGGER.info(info_msg)
        self.success = True
        raise SystemExit(0)

    def _get_running_containers(self):
        """Get the list of running containers on `self.host`.

        Returns:
            A list of container IDs of running containers.

        Raises:
            SystemExit(1): if the "crictl ps -q" command fails
        """
        return self._run_remote_command('crictl ps -q')[1].splitlines()

    def run(self):
        """Attempt to stop containers in containerd on the host.

        If successful, the thread will exit with its `success` attribute set to
        True. If unsuccessful, the `success` attribute will be False.

        The following conditions are considered success:
            - containerd is already inactive and thus containers would not be running
            - No containers are found to be running before attempting to stop any
            - No containers found to be running after attempting to stop them even
              if the command to stop them encountered timeouts

        The following conditions are considered failures:
            - Failure to query the status of containerd
            - Failure to query for running containers
            - Running containers still exist after attempting to stop them, perhaps
              due to a timeout in the command that stops them.

        Raises:
            SystemExit: if the container stop operation fails, raises a SystemExit
                with code 1. If it's successful, raises a SystemExit with a code 0.
                This is used to stop the thread.
        """
        exit_status, stdout, stderr = self._run_remote_command('systemctl is-active containerd',
                                                               err_on_non_zero=False)
        if exit_status:
            if 'inactive' in stdout:
                self._success_exit(f'containerd is not active on {self.host} so '
                                   f'there are no containers to stop.')
            else:
                self._err_exit(f'Failed to query if containerd is active. '
                               f'stdout: {stdout}, stderr: {stderr}')

        running_containers = self._get_running_containers()

        if not running_containers:
            self._success_exit(f'No containers to stop on {self.host}.')

        LOGGER.debug('The following containers were running before the stop attempt '
                     'on %s: %s', self.host, running_containers)

        exit_status, stdout, stderr = self._run_remote_command(CONTAINER_STOP_SCRIPT,
                                                               err_on_non_zero=False)

        stopped_containers = stdout.splitlines()
        LOGGER.debug('The following containers were stopped successfully on %s: %s',
                     self.host, stopped_containers)

        if exit_status:
            # This is most likely a timeout but not necessarily an error if
            # containers have been stopped.
            LOGGER.warning(f'One or more "crictl stop" commands timed out on {self.host}')

        # Check and see if they've all been stopped.
        running_containers = self._get_running_containers()
        if running_containers:
            self._err_exit(f'Failed to stop {len(running_containers)} container(s) on {self.host}. '
                           f'Execute "crictl ps -q" on the host to view running containers.')
        else:
            self._success_exit(f'All containers stopped on {self.host}.')


def do_service_action_on_hosts(hosts, service, target_state,
                               timeout=SERVICE_ACTION_TIMEOUT, target_enabled=None):
    """Do a service start/stop and optionally enable/disable across hosts in parallel.

    Args:
        hosts (list of str): The list of hosts on which to operate.
        service (str): The name of the service on which to operate.
        target_state (str): The desired active/inactive state of the service
        timeout (int): The timeout of the service operation on each host.
        target_enabled (str or None): The desired enabled/disabled state of the
            service or None if not applicable.

    Returns:
        None

    Raises:
        FatalPlatformError: if the service action fails on any of the given hosts
    """
    service_action_waiters = [RemoteServiceWaiter(host, service, target_state=target_state,
                                                  timeout=timeout, target_enabled=target_enabled)
                              for host in hosts]
    for waiter in service_action_waiters:
        waiter.wait_for_completion_async()
    for waiter in service_action_waiters:
        waiter.wait_for_completion_await()

    if not all(waiter.completed for waiter in service_action_waiters):
        raise FatalPlatformError(f'Failed to ensure {service} is {target_state} '
                                 f'{f"and {target_enabled} " if target_enabled else ""}'
                                 f'on all hosts.')


def do_stop_containers(ncn_groups):
    """Stop containers in containerd and stop containerd itself on all K8s NCNs.

    Raises:
        FatalPlatformError: if any nodes fail to stop containerd
    """
    k8s_ncns = ncn_groups['kubernetes']
    stop_group = SerialGroup(*k8s_ncns)
    failed_ncns = set()

    try:
        is_active_results = stop_group.run('systemctl is-active containerd')
        active_hosts = [
            host for host, result in is_active_results.items()
            if result.exited == 0
        ]
        if not active_hosts:
            LOGGER.info('containerd is not active on any hosts; continuing.')
            return
        else:
            LOGGER.debug('containerd appears to be active on the following NCNs: %s', active_hosts)
    except GroupException as exc:
        for failed_ncn, result in exc.result.failed.items():
            LOGGER.warning('An error occurred while checking if containerd is active on node %s: %s',
                           failed_ncn, result.stderr.strip())
            failed_ncns.add(failed_ncn)

        active_hosts = list(exc.result.succeeded.keys())

    LOGGER.info('Stopping containers on the following NCNs: %s', active_hosts)
    stop_group = ThreadingGroup(active_hosts)
    try:
        stop_group.run(CONTAINER_STOP_SCRIPT)
    except GroupException as exc:
        for failed_ncn, result in exc.result.failed.items():
            LOGGER.warning('An error occurred while checking if containerd is active on node %s: %s',
                           failed_ncn, result.stderr.strip())
            failed_ncns.add(failed_ncn)

    if failed_ncns:
        raise NonFatalPlatformError('Failed to stop containers on the following NCNs: '
                                    f'{", ".join(failed_ncns)}')


def do_containerd_stop(ncn_groups):
    """Stop containerd on all K8s NCNs.

    Raises:
        FatalPlatformError: if any nodes fail to stop containerd
    """
    do_service_action_on_hosts(ncn_groups['kubernetes'], 'containerd', target_state='inactive')


def do_containerd_start(ncn_groups):
    """Start and enable containerd on all K8s NCNs.

    Raises:
        FatalPlatformError: if any nodes fail to start containerd
    """
    do_service_action_on_hosts(ncn_groups['kubernetes'], 'containerd',
                               target_state='active', target_enabled='enabled')


def do_kubelet_stop(ncn_groups):
    """Stop and disable kubelet on all K8s NCNs.

    Raises:
        FatalPlatformError: if any nodes fail to stop kubelet
    """
    do_service_action_on_hosts(ncn_groups['kubernetes'], 'kubelet',
                               target_state='inactive', target_enabled='disabled')


def do_kubelet_start(ncn_groups):
    """Start and enable kubelet on all K8s NCNs.

    Raises:
        FatalPlatformError: if any nodes fail to start kubelet.
    """
    do_service_action_on_hosts(ncn_groups['kubernetes'], 'kubelet',
                               target_state='active', target_enabled='enabled')


def do_recreate_cronjobs(_):
    """Recreate cronjobs that are not being scheduled on time."""
    try:
        batch_api = load_kube_api(api_cls=BatchV1Api)
        recreate_namespaced_stuck_cronjobs(batch_api, 'services')
    except ConfigException as err:
        LOGGER.warning('Could not load Kubernetes configuration: %s', err)


def do_ceph_freeze(ncn_groups):
    """Check ceph health and freeze if healthy.

    Raises:
        FatalPlatformError: if ceph is not healthy or if freezing ceph fails.
    """
    try:
        check_ceph_health()
    except CephHealthCheckError as err:
        raise FatalPlatformError(f'Ceph is not healthy. Please correct Ceph health and try again. Error: {err}')
    try:
        toggle_ceph_freeze_flags(freeze=True)
    except RuntimeError as err:
        raise FatalPlatformError(str(err))


def do_ceph_unfreeze(ncn_groups):
    """Start inactive Ceph services, unfreeze Ceph and wait for it to be healthy.

    Raises:
        FatalPlatformError: if ceph is not healthy or if unfreezing ceph fails.
    """
    storage_hosts = ncn_groups['storage']
    try:
        toggle_ceph_freeze_flags(freeze=False)
    except RuntimeError as err:
        raise FatalPlatformError(str(err))

    with BeginEndLogger('wait for ceph health'):
        ceph_timeout = get_config_value('bootsys.ceph_timeout')
        LOGGER.info(f'Waiting up to {ceph_timeout} seconds for Ceph to become healthy after unfreeze')
        ceph_waiter = CephHealthWaiter(ceph_timeout, storage_hosts, retries=1)
        if not ceph_waiter.wait_for_completion():
            raise FatalPlatformError(f'Ceph is not healthy. Please correct Ceph health and try again.')
        else:
            LOGGER.info('Ceph is healthy.')


def do_etcd_snapshot(ncn_groups):
    """Save an etcd snapshot on all manager NCNs.

    Raises:
        NonFatalPlatformError: if etcd is inactive on some managers and thus
            could not have a snapshot saved.
        FatalPlatformError: if etcd snapshot command fails for another reason
    """
    managers = ncn_groups['managers']
    # A dict mapping from failed hostnames to EtcdSnapshotFailure instances
    snapshot_errs = {}

    for manager in managers:
        try:
            save_etcd_snapshot_on_host(manager)
        except EtcdSnapshotFailure as err:
            snapshot_errs[manager] = err

    if snapshot_errs:
        for hostname, err in snapshot_errs.items():
            log_level = logging.WARNING if isinstance(err, EtcdInactiveFailure) else logging.ERROR
            LOGGER.log(log_level, f'Failed to create etcd snapshot on {hostname}: {err}')
        non_fatal = all(isinstance(err, EtcdInactiveFailure) for err in snapshot_errs.values())
        exc_cls = NonFatalPlatformError if non_fatal else FatalPlatformError
        raise exc_cls(f'Failed to create etcd snapshot on hosts: '
                      f'{", ".join(snapshot_errs.keys())}')


def do_etcd_stop(ncn_groups):
    """Stop etcd service on all manager NCNs."""
    do_service_action_on_hosts(ncn_groups['managers'], 'etcd', target_state='inactive')


def do_etcd_start(ncn_groups):
    """Ensure etcd service is started and enabled on all manager NCNs."""
    do_service_action_on_hosts(ncn_groups['managers'], 'etcd', target_state='active',
                               target_enabled='enabled')


# Each step has a description that is printed and an action that is called
# with the single argument being a dict mapping from NCN group names to hosts.
PlatformServicesStep = namedtuple('PlatformServicesStep', ('description', 'action'))
STEPS_BY_ACTION = {
    # The ordered steps to start platform services
    'start': [
        PlatformServicesStep('Ensure containerd is running and enabled on all Kubernetes NCNs.',
                             do_containerd_start),
        PlatformServicesStep('Ensure etcd is running and enabled on all Kubernetes manager NCNs.',
                             do_etcd_start),
        PlatformServicesStep('Start inactive Ceph services, unfreeze Ceph cluster and wait for Ceph health.',
                             do_ceph_unfreeze),
        PlatformServicesStep('Start and enable kubelet on all Kubernetes NCNs.', do_kubelet_start),
        PlatformServicesStep('Recreate cron jobs that have become stuck', do_recreate_cronjobs),
    ],
    # The ordered steps to stop platform services
    'stop': [
        PlatformServicesStep('Create etcd snapshot on all Kubernetes manager NCNs.', do_etcd_snapshot),
        PlatformServicesStep('Stop etcd on all Kubernetes manager NCNs.', do_etcd_stop),
        PlatformServicesStep('Stop and disable kubelet on all Kubernetes NCNs.', do_kubelet_stop),
        PlatformServicesStep('Stop containers running under containerd on all Kubernetes NCNs.',
                             do_stop_containers),
        PlatformServicesStep('Stop containerd on all Kubernetes NCNs.', do_containerd_stop),
        PlatformServicesStep('Check health of Ceph cluster and freeze state.', do_ceph_freeze)
    ]
}


def do_platform_action(args, action):
    """Do a platform action with the given ordered steps.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
        action (str): The action to take. Must be a key in STEPS_BY_ACTION.

    Returns:
        None

    Raises:
        SystemExit: if given an unknown action or the action encounters a fatal error.
    """
    try:
        steps = STEPS_BY_ACTION[action]
    except KeyError:
        LOGGER.error(f'Invalid action "{action}" to perform on platform services.')
        raise SystemExit(1)

    try:
        ncn_groups = get_and_verify_ncn_groups(args.excluded_ncns)
    except FatalBootsysError as err:
        LOGGER.error(f'Not proceeding with platform {action}: {err}')
        raise SystemExit(1)

    for step in steps:
        try:
            info_message = f'Executing step: {step.description}'
            LOGGER.info(info_message)
            step.action(ncn_groups)
        except NonFatalPlatformError as err:
            LOGGER.warning(f'Non-fatal error in step "{step.description}" of '
                           f'platform services {action}: {err}')
            answer = pester_choices(f'Continue with platform services {action}?', ('yes', 'no'))
            if answer == 'yes':
                LOGGER.info('Continuing.')
            else:
                LOGGER.info('Aborting.')
                raise SystemExit(1)
        except FatalPlatformError as err:
            LOGGER.error(f'Fatal error in step "{step.description}" of '
                         f'platform services {action}: {err}')
            raise SystemExit(1)


def do_platform_stop(args):
    """Stop services to shut down a Shasta system.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.

    Returns:
        None
    """
    if not args.disruptive:
        prompt_continue('stopping platform services')

    do_platform_action(args, 'stop')


def do_platform_start(args):
    """Start services to boot a Shasta system.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.

    Returns:
        None
    """
    do_platform_action(args, 'start')
