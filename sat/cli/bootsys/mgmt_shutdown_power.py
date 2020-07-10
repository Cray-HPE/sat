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
import subprocess
import shlex
import socket
import time

from pyghmi.exceptions import IpmiException
from pyghmi.ipmi.command import Command as ipmiCommand
from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from sat.cli.bootsys.ansible_util import get_groups
from sat.cli.bootsys.util import set_dhcpd

LOGGER = logging.getLogger(__name__)
REMOTE_CMD = 'shutdown -h now'


# Failures are logged, but otherwise ignored. They may be considered "stalled shutdowns" and
# forcibly powered off as allowed for in the process.
def start_shutdown(ncns, ssh_client, dry_run=True):
    for host in ncns:
        LOGGER.info('Executing command on host "%s": `%s`', host, REMOTE_CMD)
        if dry_run:
            continue
        else:
            try:
                ssh_client.connect(host)
            except (BadHostKeyException, AuthenticationException,
                    SSHException, socket.error) as err:
                LOGGER.warning('Unable to connect to host "%s": %s', host, err)

            try:
                remote_streams = ssh_client.exec_command(REMOTE_CMD)
            except SSHException as err:
                LOGGER.warning('Remote execution failed for host "%s": %s', host, err)
            else:
                for channel in remote_streams:
                    channel.close()


def finish_shutdown(ncns, username, password, dry_run=True):
    ipmi_commands = {}
    ipmi_fail = False

    for host in ncns:
        try:
            ipmi_commands[host] = ipmiCommand(host+'-mgmt', username, password)
        except (IpmiException, socket.error) as err:
            LOGGER.error('Failed to initiate IPMI session with host "%s": %s', host, err)
            ipmi_fail = True

    if ipmi_fail:
        raise SystemExit(1)

    pending_hosts = set(ncns)

    if not dry_run:
        set_dhcpd(True)

    try:
        shutdown_timeout_secs = 10 * (1 if dry_run else 60)
        t_end = time.monotonic() + shutdown_timeout_secs

        while time.monotonic() < t_end and pending_hosts:
            for host in pending_hosts:
                try:
                    power_state = (False if dry_run
                                   else ipmi_commands[host].get_power()['powerstate'] == 'on')

                except IpmiException as err:
                    LOGGER.warning('Unable to power down host "%s" via IPMI: %s', host, err)
                    # Assume subsequent queries will also fail, to prevent log spam.
                    power_state = False

                if not power_state:
                    pending_hosts.remove(host)
                    break

            time.sleep(.2)

        for host in pending_hosts:
            LOGGER.warning(
                'Timed out waiting for "%s" to shutdown; attempting to power it down forcibly.', host)
            if not dry_run:
                try:
                    ipmi_commands[host].set_power('off')
                except IpmiException as err:
                    LOGGER.error('Unable to powerdown host "%S" via IPMI: %s', host, err)
                    ipmi_fail = True

        if ipmi_fail:
            raise SystemExit(1)

    finally:
        if not dry_run:
            set_dhcpd(False)


def do_mgmt_shutdown_power(ssh_client, username, password, dry_run=True):
    LOGGER.info('Sending shutdown command to NCNs.')

    nonworker_ncns = sorted(get_groups(['managers', 'storage', 'workers']) - get_groups(['bis']))
    start_shutdown(nonworker_ncns, ssh_client, dry_run)

    finish_shutdown(nonworker_ncns, username, password, dry_run)
    LOGGER.info('Shutdown complete.')
