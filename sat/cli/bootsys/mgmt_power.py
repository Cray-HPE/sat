"""
Management cluster boot, shutdown, and IPMI power support.

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
from collections import defaultdict
import logging
import shlex
import socket
import subprocess
import sys

import inflect
from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from sat.cli.bootsys.ipmi_console import IPMIConsoleLogger, ConsoleLoggingError
from sat.cli.bootsys.util import get_and_verify_ncn_groups, get_ssh_client, FatalBootsysError
from sat.cli.bootsys.waiting import GroupWaiter, WaitingFailure
from sat.config import get_config_value
from sat.util import BeginEndLogger, get_username_and_password_interactively, prompt_continue

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
    out on a given host, an IPMI power off command is sent to hard
    power off the host.

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
        LOGGER.warning('Forcibly powering off nodes: %s', ', '.join(pending_hosts))

        # Confirm all nodes have actually turned off.
        failed_hosts = IPMIPowerStateWaiter(pending_hosts, 'off', ipmi_timeout, username, password,
                                            send_command=True).wait_for_completion()

        if failed_hosts:
            LOGGER.error('The following nodes failed to reach powered '
                         'off state: %s', ', '.join(failed_hosts))
            sys.exit(1)


def do_mgmt_shutdown_power(ssh_client, username, password, excluded_ncns, ncn_shutdown_timeout, ipmi_timeout):
    """Power off NCNs.

    Args:
        ssh_client (paramiko.SSHClient): a paramiko client object.
        username (str): IPMI username to use.
        password (str): IPMI password to use.
        excluded_ncns (set of str): The set of ncn hostnames to exclude, in
            addition to ncn-m001, which is always excluded.
        ncn_shutdown_timeout (int): timeout, in seconds, after which to hard
            power off.
        ipmi_timeout (int): timeout, in seconds, for nodes to reach desired
            power state after IPMI power off.
    """
    # Ensure we do not shut down the first master node yet, as it is the node
    # where "sat bootsys" commands are being run.
    # TODO: Is there a better way to get the hostname of the first master node?
    try:
        other_ncns_by_role = get_and_verify_ncn_groups(excluded_ncns.union({'ncn-m001'}))
    except FatalBootsysError as err:
        LOGGER.error(f'Not proceeding with NCN power off: {err}')
        raise SystemExit(1)

    other_ncns = list({ncn for role in ('managers', 'storage', 'workers')
                       for ncn in other_ncns_by_role[role]})

    try:
        with IPMIConsoleLogger(other_ncns, username, password):
            LOGGER.info(f'Sending shutdown command to other NCNs: {", ".join(other_ncns)}')
            start_shutdown(other_ncns, ssh_client)
            LOGGER.info(f'Waiting up to {ncn_shutdown_timeout} seconds for other NCNs to '
                        f'reach powered off state according to ipmitool: {", ".join(other_ncns)}.')
            finish_shutdown(other_ncns, username, password,
                            ncn_shutdown_timeout, ipmi_timeout)
            LOGGER.info('Shutdown and power off of all other NCNs complete.')
    except ConsoleLoggingError as err:
        LOGGER.error(f'Aborting shutdown of NCNs due failure to set up NCN console logging: {err}')
        raise SystemExit(1)


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
    ssh_client = get_ssh_client()

    with BeginEndLogger(action_msg):
        do_mgmt_shutdown_power(ssh_client, username, password, args.excluded_ncns,
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

    ordered_boot_groups = [included_ncn_groups[role] for role in ('managers', 'storage', 'workers')]
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
        except ConsoleLoggingError as err:
            LOGGER.error(f'Aborting boot of NCNs due failure to set up NCN console logging: {err}')
            raise SystemExit(1)

    LOGGER.info('Succeeded with {}.'.format(action_msg))
