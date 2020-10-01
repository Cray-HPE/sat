"""
Management cluster shutdown, IPMI power support.

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

import logging
import socket

from paramiko.client import SSHClient
from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from sat.cli.bootsys.ipmi_console import IPMIConsoleLogger
from sat.cli.bootsys.mgmt_hosts import do_enable_hosts_entries
from sat.cli.bootsys.power import IPMIPowerStateWaiter
from sat.cli.bootsys.util import get_ncns, RunningService
from sat.util import BeginEndLogger, get_username_and_password_interactively, prompt_continue

LOGGER = logging.getLogger(__name__)


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


def finish_shutdown(hosts, username, password, timeout):
    """Ensure each host is powered off.

    After start_shutdown is called, this checks that all the hosts
    have reached an IPMI "off" power state. If the shutdown has timed
    out on a given host, an IPMI power off command is sent to hard
    power off the host.

    Args:
        hosts ([str]): a list of hostnames to power off.
        username (str): IPMI username to use.
        password (str): IPMI password to use.
        timeout (int): timeout, in seconds, after which to hard power off.
    """
    with RunningService('dhcpd', sleep_after_start=5):
        ipmi_waiter = IPMIPowerStateWaiter(hosts, 'off', timeout, username, password)
        pending_hosts = ipmi_waiter.wait_for_completion()

        if pending_hosts:
            LOGGER.warning('Forcibly powering off nodes: %s', ', '.join(pending_hosts))

            # Confirm all nodes have actually turned off.
            failed_hosts = IPMIPowerStateWaiter(pending_hosts, 'off', timeout, username, password,
                                                send_command=True).wait_for_completion()

            if failed_hosts:
                LOGGER.error('The following nodes failed to reach powered '
                             'off state: %s', ', '.join(failed_hosts))


def do_mgmt_shutdown_power(ssh_client, username, password, timeout):
    """Power off NCNs.

    Args:
        ssh_client (SSHClient): a paramiko client object.
        username (str): IPMI username to use.
        password (str): IPMI password to use.
        timeout (int): timeout, in seconds, after which to hard power off.
    """
    LOGGER.info('Sending shutdown command to hosts.')

    non_bis_hosts = get_ncns(['managers', 'storage', 'workers'], exclude=['bis'])
    with IPMIConsoleLogger(non_bis_hosts):
        start_shutdown(non_bis_hosts, ssh_client)

        finish_shutdown(non_bis_hosts, username, password, timeout)
        LOGGER.info('Shutdown complete.')


def do_power_off_ncns(args):
    """Power off NCNs.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    print('Enabling required entries in /etc/hosts for NCN mgmt interfaces.')
    do_enable_hosts_entries()

    action_msg = 'shutdown of management NCNs'
    prompt_continue(action_msg)
    username, password = get_username_and_password_interactively(username_prompt='IPMI username',
                                                                 password_prompt='IPMI password')
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()

    with BeginEndLogger(action_msg):
        do_mgmt_shutdown_power(ssh_client, username, password, args.ipmi_timeout)
    print('Succeeded with {}.'.format(action_msg))