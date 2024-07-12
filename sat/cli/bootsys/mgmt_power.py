#
# MIT License
#
# (C) Copyright 2020-2021, 2023-2024 Hewlett Packard Enterprise Development LP
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
Management cluster boot, shutdown, and IPMI power support.
"""
from collections import defaultdict
import itertools
import logging
import shlex
import socket
import subprocess
import sys

import inflect
from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from sat.cli.bootsys.filesystems import FilesystemError, do_ceph_unmounts, modify_ensure_ceph_mounts_cron_job
from sat.cli.bootsys.hostkeys import FilteredHostKeys
from sat.cli.bootsys.ipmi_console import IPMIConsoleLogger, ConsoleLoggingError
from sat.cli.bootsys.util import get_and_verify_ncn_groups, get_ssh_client, FatalBootsysError
from sat.cli.bootsys.platform import do_ceph_freeze, do_ceph_unfreeze, FatalPlatformError
from sat.waiting import GroupWaiter, WaitingFailure
from sat.config import get_config_value
from sat.util import BeginEndLogger, get_username_and_password_interactively, pester_choices, prompt_continue

LOGGER = logging.getLogger(__name__)
INF = inflect.engine()


class IPMIPowerStateWaiter(GroupWaiter):
    """Implementation of a waiter for IPMI power states.

    Waits for all members to reach the given IPMI power state."""

    def __init__(self, members, power_state, timeout, username, password,
                 send_command=False, poll_interval=1, failure_threshold=3):
        """Constructor for an IPMIPowerStateWaiter object.

        Args:
            power_state (str): either 'on' or 'off', corresponds the desired
                IPMI power state.
            send_command (bool): if True, send a 'power on' or 'power off' command
                to each node before waiting.
            username (str): the username to use when running ipmitool commands
            password (str): the password to use when running ipmitool commands
            failure_threshold (int): if a call to ipmitool gives a nonzero
                return code this many times in a row for a given member, then
                that member will be marked as failed.
        """
        self.power_state = power_state
        self.username = username
        self.password = password
        self.send_command = send_command

        self.failure_threshold = failure_threshold
        self.consecutive_failures = defaultdict(int)

        super().__init__(members, timeout, poll_interval=poll_interval)

    def condition_name(self):
        return 'IPMI power ' + self.power_state

    def get_ipmi_command(self, member, command):
        """Get the full command-line for an ipmitool command.

        Args:
            member (str): the host to query
            command (str): the ipmitool command to run, e.g. `chassis power status`

        Returns:
            The command to run, split into a list of args by shlex.split.
        """
        return shlex.split(
            'ipmitool -I lanplus -U {} -P {} -H {}-mgmt {}'.format(
                self.username, self.password, member, command
            )
        )

    def member_has_completed(self, member):
        """Check if a host is in the desired state.

        Return:
            If the powerstate of the host matches that which was given
            in the constructor, return True. Otherwise, return False.
        """
        ipmi_command = self.get_ipmi_command(member, 'chassis power status')
        try:
            proc = subprocess.run(ipmi_command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, encoding='utf-8')
        except OSError as err:
            raise WaitingFailure(f'Unable to find ipmitool: {err}')

        if proc.returncode:
            if not self.consecutive_failures[member]:
                LOGGER.warning("impitool command failed with code %d: %s",
                               proc.returncode, proc.stderr)

            self.consecutive_failures[member] += 1
            if self.consecutive_failures[member] >= self.failure_threshold:
                raise WaitingFailure(f'ipmitool command failed {self.consecutive_failures[member]} time(s) '
                                     f'with code {proc.returncode}; stderr: {proc.stderr}')
            return False
        elif self.consecutive_failures[member]:
            self.consecutive_failures[member] = 0

        return self.power_state in proc.stdout

    def pre_wait_action(self):
        """Send IPMI power commands to given hosts.

        This will issue IPMI power commands to put the given hosts in the power
        state given by `self.power_state`.

        Returns:
            None
        """
        LOGGER.debug("Entered pre_wait_action with self.send_command: %s.", self.send_command)
        if self.send_command:
            for member in self.members:
                LOGGER.info('Sending IPMI power %s command to host %s', self.power_state, member)
                ipmi_command = self.get_ipmi_command(member,
                                                     'chassis power {}'.format(self.power_state))
                try:
                    proc = subprocess.run(ipmi_command, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, encoding='utf-8')
                except OSError as err:
                    # TODO (SAT-552): Improve handling of ipmitool errors
                    LOGGER.error('Unable to find ipmitool: %s', err)
                    return

                if proc.returncode:
                    # TODO (SAT-552): Improve handling of ipmitool errors
                    LOGGER.error('ipmitool command failed with code %s: stderr: %s',
                                 proc.returncode, proc.stderr)
                    return


class SSHAvailableWaiter(GroupWaiter):
    """A waiter which waits for all member nodes to be accessible via SSH.
    """

    def __init__(self, members, timeout, poll_interval=1):
        self.ssh_client = get_ssh_client()

        super().__init__(members, timeout, poll_interval=poll_interval)

    def condition_name(self):
        return 'Hosts accessible via SSH'

    def member_has_completed(self, member):
        """Check if a node is accessible by SSH.

        Args:
            member (str): a hostname to check

        Returns:
            True if SSH connecting succeeded, and
                False otherwise.
        """
        try:
            self.ssh_client.connect(member)
        except (SSHException, socket.error):
            return False
        else:
            return True


# Failures are logged, but otherwise ignored. They may be considered "stalled shutdowns" and
# forcibly powered off as allowed for in the process.
def start_shutdown(hosts, ssh_client):
    """Start shutdown by sending a shutdown command to each host.

    Args:
        hosts ([str]): a list of hostnames to shut down.
        ssh_client (paramiko.SSHClient): a paramiko client object.
    """

    REMOTE_CMD = 'shutdown -h now'

    for host in hosts:
        LOGGER.info('Executing command on host "%s": `%s`', host, REMOTE_CMD)
        try:
            ssh_client.connect(host)
        except (BadHostKeyException, AuthenticationException,
                SSHException, socket.error) as err:
            LOGGER.warning('Unable to connect to host "%s": %s', host, err)
            continue

        try:
            remote_streams = ssh_client.exec_command(REMOTE_CMD)
        except SSHException as err:
            LOGGER.warning('Remote execution failed for host "%s": %s', host, err)
        else:
            for channel in remote_streams:
                channel.close()


def finish_shutdown(hosts, username, password, ncn_shutdown_timeout, ipmi_timeout):
    """Ensure each host is powered off.

    After start_shutdown is called, this checks that all the hosts
    have reached an IPMI "off" power state. If the shutdown has timed
    out on a given host, a prompt is shown to the user to decide whether
    to proceed with hard power off.

    Args:
        hosts ([str]): a list of hostnames to power off.
        username (str): IPMI username to use.
        password (str): IPMI password to use.
        ncn_shutdown_timeout (int): timeout, in seconds, after which to hard
            power off.
        ipmi_timeout (int): timeout, in seconds, for nodes to reach desired
            power state after IPMI power off.

    Raises:
        SystemExit: if any of the `hosts` failed to reach powered off state
    """
    ipmi_waiter = IPMIPowerStateWaiter(hosts, 'off', ncn_shutdown_timeout, username, password)
    pending_hosts = ipmi_waiter.wait_for_completion()

    if pending_hosts:
        LOGGER.warning('The following nodes did not complete a graceful '
                       'shutdown within the timeout: %s', ', '.join(pending_hosts))

        # Confirm all nodes have actually turned off.
        prompt_message = 'Do you want to forcibly power off the nodes that timedout?'
        if pester_choices(prompt_message, ('yes', 'no')) == 'yes':
            LOGGER.info('Proceeding with hard power off.')

            failed_hosts = IPMIPowerStateWaiter(pending_hosts, 'off', ipmi_timeout, username, password,
                                                send_command=True).wait_for_completion()

            if failed_hosts:
                LOGGER.error('The following nodes failed to reach powered '
                             'off state: %s', ', '.join(failed_hosts))
                sys.exit(1)
        else:
            LOGGER.info('User opted not to proceed with hard power off. Exiting.')
            sys.exit(0)


def do_mgmt_shutdown_power(username, password, excluded_ncns, ncn_shutdown_timeout, ipmi_timeout):
    """Power off NCNs.

    Args:
        username (str): IPMI username to use.
        password (str): IPMI password to use.
        excluded_ncns (set of str): The set of NCN hostnames to exclude.
        ncn_shutdown_timeout (int): Timeout, in seconds, after which to hard power off.
        ipmi_timeout (int): Timeout, in seconds, for nodes to reach desired power state after IPMI power off.
    """
    try:
        other_ncns_by_role = get_and_verify_ncn_groups(excluded_ncns.union({'ncn-m001'}))
    except FatalBootsysError as err:
        LOGGER.error(f'Not proceeding with NCN power off: {err}')
        raise SystemExit(1)

    all_ncn_hostnames = list(itertools.chain(*other_ncns_by_role.values()))
    host_keys = FilteredHostKeys(hostnames=all_ncn_hostnames)
    ssh_client = get_ssh_client(host_keys=host_keys)

    # Shutdown workers
    worker_ncns = other_ncns_by_role.get('workers', [])
    if worker_ncns:
        try:
            with IPMIConsoleLogger(worker_ncns, username, password):
                LOGGER.info(f'Shutting down worker NCNs: {", ".join(worker_ncns)}')
                start_shutdown(worker_ncns, ssh_client)
                LOGGER.info(f'Waiting up to {ncn_shutdown_timeout} seconds for worker NCNs to shut down...')
                finish_shutdown(worker_ncns, username, password, ncn_shutdown_timeout, ipmi_timeout)
        except ConsoleLoggingError as err:
            LOGGER.error(f'Aborting shutdown of worker NCNs due to failure to '
                         f'set up NCN console logging: {err}')
            ssh_client.close()
            raise SystemExit(1)
    else:
        LOGGER.info('No worker NCNs to shutdown.')

    # Shutdown managers (except ncn-m001)
    manager_ncns = other_ncns_by_role.get('managers', [])
    if manager_ncns:
        try:
            with IPMIConsoleLogger(manager_ncns, username, password):
                LOGGER.info(f'Shutting down manager NCNs: {", ".join(manager_ncns)}')
                start_shutdown(manager_ncns, ssh_client)
                LOGGER.info(f'Waiting up to {ncn_shutdown_timeout} seconds for manager NCNs to shut down...')
                finish_shutdown(manager_ncns, username, password, ncn_shutdown_timeout, ipmi_timeout)
        except ConsoleLoggingError as err:
            LOGGER.error(f'Aborting shutdown of manager NCNs due to failure to '
                         f'set up NCN console logging: {err}')
            ssh_client.close()
            raise SystemExit(1)
    else:
        LOGGER.info('No Manager NCNs to shutdown.')

    try:
        do_ceph_unmounts(ssh_client, 'ncn-m001')
    except FilesystemError as err:
        LOGGER.error(f'Failed to unmount Ceph filesystems on ncn-m001: {err}')
        ssh_client.close()
        raise SystemExit(1)

    # Freeze Ceph on storage nodes and then shutdown
    storage_ncns = other_ncns_by_role.get('storage', [])
    if storage_ncns:
        LOGGER.info(f'Freezing Ceph and shutting down storage NCNs: {", ".join(storage_ncns)}')
        try:
            do_ceph_freeze()
        except FatalPlatformError as err:
            LOGGER.error(f'Failed to freeze Ceph on storage NCNs: {err}')
            ssh_client.close()
            raise SystemExit(1)
        LOGGER.info('Ceph freeze completed successfully on storage NCNs.')
        try:
            with IPMIConsoleLogger(storage_ncns, username, password):
                start_shutdown(storage_ncns, ssh_client)
                LOGGER.info(f'Waiting up to {ncn_shutdown_timeout} seconds for storage NCNs to shut down...')
                finish_shutdown(storage_ncns, username, password, ncn_shutdown_timeout, ipmi_timeout)
                LOGGER.info(f'Shutdown and power off of storage NCNs: {", ".join(storage_ncns)}')
        except ConsoleLoggingError as err:
            LOGGER.error(f'Aborting shutdown of storage NCNs due to failure to '
                         f'set up NCN console logging: {err}')
            ssh_client.close()
            raise SystemExit(1)
    else:
        LOGGER.info('No storage NCNs to shutdown.')

    ssh_client.close()
    LOGGER.info('Shutdown and power off of all management NCNs complete.')


def do_power_off_ncns(args):
    """Power off NCNs while monitoring consoles with ipmitool.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    action_msg = 'shutdown of other management NCNs'
    if not args.disruptive:
        prompt_continue(action_msg)
    username, password = get_username_and_password_interactively(username_prompt='IPMI username',
                                                                 password_prompt='IPMI password')
    with BeginEndLogger(action_msg):
        do_mgmt_shutdown_power(username, password, args.excluded_ncns,
                               get_config_value('bootsys.ncn_shutdown_timeout'),
                               get_config_value('bootsys.ipmi_timeout'))
    LOGGER.info('Succeeded with {}.'.format(action_msg))


def do_power_on_ncns(args):
    """Power on NCNs while monitoring consoles with ipmitool.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    action_msg = 'boot of other management NCNs'
    username, password = get_username_and_password_interactively(username_prompt='IPMI username',
                                                                 password_prompt='IPMI password')

    # First master node is already on as it is where "sat bootsys" runs.
    # TODO: Is there a better way to get the hostname of the first master node?
    try:
        included_ncn_groups = get_and_verify_ncn_groups(args.excluded_ncns.union({'ncn-m001'}))
    except FatalBootsysError as err:
        LOGGER.error(f'Not proceeding with NCN power on: {err}')
        raise SystemExit(1)

    ordered_boot_groups = [included_ncn_groups[role] for role in ('storage', 'managers', 'workers')]
    # flatten lists of ncn groups
    affected_ncns = list({ncn for sublist in ordered_boot_groups for ncn in sublist})

    with BeginEndLogger(action_msg):
        try:
            with IPMIConsoleLogger(affected_ncns, username, password):
                for ncn_group in ordered_boot_groups:
                    ncn_boot_timeout = get_config_value('bootsys.ncn_boot_timeout')
                    LOGGER.info(f'Powering on NCNs and waiting up to {ncn_boot_timeout} seconds '
                                f'for them to be reachable via SSH: {", ".join(ncn_group)}')

                    # TODO (SAT-555): Probably should not send a power on if it's already on.
                    ipmi_waiter = IPMIPowerStateWaiter(ncn_group, 'on',
                                                       get_config_value('bootsys.ipmi_timeout'),
                                                       username, password, send_command=True)
                    ipmi_waiter.wait_for_completion()

                    ssh_waiter = SSHAvailableWaiter(ncn_group, ncn_boot_timeout)
                    inaccessible_nodes = ssh_waiter.wait_for_completion()

                    if inaccessible_nodes:
                        LOGGER.error('Unable to reach the following NCNs via SSH '
                                     'after powering them on: %s. Troubleshoot the '
                                     'issue and then try again.',
                                     ', '.join(inaccessible_nodes))
                        raise SystemExit(1)
                    else:
                        LOGGER.info(f'Powered on NCNs: {", ".join(ncn_group)}')
                    # Unfreeze Ceph and wait for Ceph health after powering on the storage nodes
                    if ncn_group == included_ncn_groups['storage']:
                        try:
                            do_ceph_unfreeze(included_ncn_groups)
                        except FatalPlatformError as err:
                            LOGGER.error(f'Failed to unfreeze Ceph on storage NCNs: {err}')
                            sys.exit(1)
                        LOGGER.info('Ceph unfreeze completed successfully on storage NCNs.')

                        # Mount Ceph and S3FS filesystems on ncn-m001
                        try:
                            ssh_client = get_ssh_client()
                            mount_filesystems_on_ncn(ssh_client, 'ncn-m001')
                        except MountError as err:
                            LOGGER.error(f'Failed to mount filesystems on ncn-m001: {err}')
                            sys.exit(1)

        except ConsoleLoggingError as err:
            LOGGER.error(f'Aborting boot of NCNs due failure to set up NCN console logging: {err}')
            raise SystemExit(1)

    LOGGER.info('Succeeded with {}.'.format(action_msg))


def mount_filesystems_on_ncn(ssh_client, ncn):
    """Mount Ceph and S3FS filesystems on a given NCN via SSH.

    Args:
        ssh_client (paramiko.SSHClient): a paramiko client object.
        ncn: The hostname of the NCN where the filesystems will be mounted.

    Raises:
        MountError: If mounting any filesystem fails.
    """
    filesystems = {
        "ceph": "awk '{ if ($3 == \"ceph\") { print $2; }}' /etc/fstab",
        "fuse.s3fs": "awk '{ if ($3 == \"fuse.s3fs\") { print $2; }}' /etc/fstab"
    }

    try:
        # Establish SSH connection
        ssh_client.connect(ncn)

        for fs_type, awk_command in filesystems.items():
            # Execute awk command to get mount points
            stdin, stdout, stderr = ssh_client.exec_command(awk_command)
            mount_points = stdout.read().decode().splitlines()

            for mount_point in mount_points:
                LOGGER.info(f'Checking whether {fs_type} filesystem is mounted on {mount_point}.')

                # Check if the mount point is already mounted
                stdin, stdout, stderr = ssh_client.exec_command(f"mountpoint {mount_point}")
                if stdout.channel.recv_exit_status() != 0:  # If not a mountpoint, try to mount it
                    LOGGER.info(f'Mounting {fs_type} filesystem on {mount_point}.')
                    stdin, stdout, stderr = ssh_client.exec_command(f"mount {mount_point}")
                    if stdout.channel.recv_exit_status() != 0:
                        error_msg = stderr.read().decode()
                        raise MountError(f"Failed to mount {fs_type} filesystem on {ncn}: {error_msg}")
                    LOGGER.info(f'Successfully mounted {fs_type} filesystem on {mount_point}.')
                else:
                    LOGGER.info(f'{fs_type} filesystem is already mounted on {mount_point}.')

        try:
            modify_ensure_ceph_mounts_cron_job(ssh_client, ncn, enabled=True)
        except FilesystemError as err:
            raise MountError(str(err)) from err

    except SSHException as e:
        raise MountError(f"SSH connection failed: {str(e)}")

    # Ensure the ssh_client is closed
    finally:
        ssh_client.close()


class MountError(Exception):
    """Custom exception for mount errors."""
    pass
