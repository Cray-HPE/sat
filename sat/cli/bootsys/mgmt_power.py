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
import logging
import shlex
import socket
import subprocess
import sys

import inflect
from paramiko.client import SSHClient
from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from sat.cli.bootsys.ipmi_console import IPMIConsoleLogger
from sat.cli.bootsys.util import get_mgmt_ncn_hostnames, RunningService
from sat.cli.bootsys.waiting import GroupWaiter
from sat.config import get_config_value
from sat.util import BeginEndLogger, get_username_and_password_interactively, prompt_continue

LOGGER = logging.getLogger(__name__)
INF = inflect.engine()


class IPMIPowerStateWaiter(GroupWaiter):
    """Implementation of a waiter for IPMI power states.

    Waits for all members to reach the given IPMI power state."""

    def __init__(self, members, power_state, timeout, username, password,
                 send_command=False, poll_interval=1):
        """Constructor for an IPMIPowerStateWaiter object.

        Args:
            power_state (str): either 'on' or 'off', corresponds the desired
                IPMI power state.
            send_command (bool): if True, send a 'power on' or 'power off' command
                to each node before waiting.
            username (str): the username to use when running ipmitool commands
            password (str): the password to use when running ipmitool commands
        """
        self.power_state = power_state
        self.username = username
        self.password = password
        self.send_command = send_command

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
            # TODO (SAT-552): Improve handling of ipmitool errors
            LOGGER.error('Unable to find ipmitool: %s', err)
            return False

        if proc.returncode:
            # TODO (SAT-552): Improve handling of ipmitool errors
            LOGGER.error('ipmitool command failed with code %s: stderr: %s',
                         proc.returncode, proc.stderr)
            return False

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
        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()

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
        ssh_client (SSHClient): a paramiko client object.
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
    with RunningService('dhcpd', sleep_after_start=5):
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


def do_mgmt_shutdown_power(ssh_client, username, password, ncn_shutdown_timeout, ipmi_timeout):
    """Power off NCNs.

    Args:
        ssh_client (SSHClient): a paramiko client object.
        username (str): IPMI username to use.
        password (str): IPMI password to use.
        ncn_shutdown_timeout (int): timeout, in seconds, after which to hard
            power off.
        ipmi_timeout (int): timeout, in seconds, for nodes to reach desired
            power state after IPMI power off.    """
    LOGGER.info('Sending shutdown command to hosts.')

    # Ensure we do not shut down the first master node yet, as it is the node
    # where "sat bootsys" commands are being run.
    # TODO: Is there a better way to get the hostname of the first master node?
    other_ncns = get_mgmt_ncn_hostnames(['managers', 'storage', 'workers']) - {'ncn-m001'}
    with IPMIConsoleLogger(other_ncns):
        start_shutdown(other_ncns, ssh_client)

        finish_shutdown(other_ncns, username, password,
                        ncn_shutdown_timeout, ipmi_timeout)
        LOGGER.info('Shutdown complete.')


def do_power_off_ncns(args):
    """Power off NCNs.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """

    action_msg = 'shutdown of management NCNs'
    prompt_continue(action_msg)
    username, password = get_username_and_password_interactively(username_prompt='IPMI username',
                                                                 password_prompt='IPMI password')
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()

    with BeginEndLogger(action_msg):
        do_mgmt_shutdown_power(ssh_client, username, password,
                               get_config_value('bootsys.ncn_shutdown_timeout'),
                               get_config_value('bootsys.ipmi_timeout'))
    print('Succeeded with {}.'.format(action_msg))


def do_power_on_ncns(args):
    """Power on NCNs.

    This stage also enables/disables entries in the hosts file, starts/stops
    IPMI console logging, and starts/stops dhcpd on the worker node on which
    the stage is running.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    username, password = get_username_and_password_interactively(username_prompt='IPMI username',
                                                                 password_prompt='IPMI password')

    with RunningService('dhcpd', sleep_after_start=5):
        # First master node is already on as it is where "sat bootsys" runs.
        # TODO: Is there a better way to get the hostname of the first master node?
        master_nodes = get_mgmt_ncn_hostnames(['managers']) - {'ncn-m001'}
        storage_nodes = get_mgmt_ncn_hostnames(['storage'])
        worker_nodes = get_mgmt_ncn_hostnames(['workers'])
        ncn_groups = [master_nodes, storage_nodes, worker_nodes]
        # flatten lists of ncn groups
        non_bis_ncns = set(ncn for sublist in ncn_groups for ncn in sublist)
        with IPMIConsoleLogger(non_bis_ncns):
            for ncn_group in ncn_groups:
                print(f'Powering on NCNs: {", ".join(ncn_group)}')

                # TODO (SAT-555): Probably should not send a power on if it's already on.
                ipmi_waiter = IPMIPowerStateWaiter(ncn_group, 'on',
                                                   get_config_value('bootsys.ipmi_timeout'),
                                                   username, password, send_command=True)
                ipmi_waiter.wait_for_completion()

                ssh_waiter = SSHAvailableWaiter(ncn_group,
                                                get_config_value('bootsys.ncn_boot_timeout'))
                inaccessible_nodes = ssh_waiter.wait_for_completion()

                if inaccessible_nodes:
                    LOGGER.error('Unable to reach the following NCNs via SSH '
                                 'after powering them on: %s. Troubleshoot the '
                                 'issue and then try again.',
                                 ', '.join(inaccessible_nodes))
                    # Have to exit here because playbook will fail if nodes are
                    # not available for SSH.
                    raise SystemExit(1)
                else:
                    print(f'Powered on NCNs: {", ".join(ncn_group)}')
