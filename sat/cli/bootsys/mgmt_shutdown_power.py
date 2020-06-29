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

from sat.cli.bootsys.mgmt_shutdown_config import LIVE, REMOTE_CMD
from sat.cli.bootsys.ansible_util import get_groups

LOGGER = logging.getLogger(__name__)


# skip worker one
OTHER_NCNS = sorted(get_groups(['managers', 'storage', 'workers']) - get_groups(['bis']))

if LIVE:
    SHUTDOWN_TIMEOUT_SECS = 10 * 60
else:
    SHUTDOWN_TIMEOUT_SECS = 10

    SEED = 42
    from random import Random
    host_mask = Random(SEED).getrandbits(len(OTHER_NCNS))


# Failures are logged, but otherwise ignored. They may be considered "stalled shutdowns" and
# forcibly powered off as allowed for in the process.
def query_powerstate(command):
    if not LIVE:
        n = OTHER_NCNS.index(command.bmc[:-5])
        return bool(host_mask & (1 << n))
    else:
        # True if on, False if off, or raises pyghmi.exceptions.ImpiException
        return command.get_power()['powerstate'] == 'on'


def set_powerstate(command):
    if not LIVE:
        LOGGER.info('Only a test; not powering down host "%s".', command.bmc[:-5])
    else:
        # may raise IpmiException
        command.set_power('off')


# Failures are logged, but otherwise ignored. They may be considered "stalled shutdowns" and
# forcibly powered off as allowed for in the process.
def start_shutdown(ssh_client):
    for host in OTHER_NCNS:
        try:
            ssh_client.connect(host)
        except (BadHostKeyException, AuthenticationException, SSHException, socket.error) as err:
            LOGGER.warning('Unable to connect to host "%s": %s', host, err)

        try:
            remote_streams = ssh_client.exec_command(REMOTE_CMD)
        except SSHException as err:
            LOGGER.warning('Remote execution failed for host "%s": %s', host, err)
        else:
            for channel in remote_streams:
                channel.close()


def set_dhcpd(state):
    if LIVE:
        cmd = 'systemctl {} dhcpd'.format('start' if state else 'stop')
        pc = subprocess.run(shlex.split(cmd))

        if pc.returncode:
            LOGGER.warning('"%s" exited with non-zero status: %s', cmd, pc.returncode)


def finish_shutdown(username, password):
    ipmi_commands = {}
    ipmi_fail = False

    for host in OTHER_NCNS:
        try:
            ipmi_commands[host] = ipmiCommand(host+'-mgmt', username, password)
        except (IpmiException, socket.error) as err:
            LOGGER.error('Failed to initiate IPMI session with host "%s": %s', host, err)
            ipmi_fail = True

    if ipmi_fail:
        raise SystemExit(1)

    pending_hosts = set(OTHER_NCNS)

    set_dhcpd(True)

    try:
        t_end = time.time() + SHUTDOWN_TIMEOUT_SECS

        while time.time() < t_end and pending_hosts:
            for host in pending_hosts:
                try:
                    power_state = query_powerstate(ipmi_commands[host])
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
                'Timed out waiting for "%s" to shutdown; powering it down not-gently.', host)
            try:
                set_powerstate(ipmi_commands[host])
            except IpmiException as err:
                LOGGER.error('Unable to powerdown host "%S" via IPMI: %s', host, err)
                ipmi_fail = True

        if ipmi_fail:
            raise SystemExit(1)

    finally:
        set_dhcpd(False)


def do_mgmt_shutdown_power(ssh_client, username, password):
    LOGGER.info('Sending shutdown command to NCNs.')
    start_shutdown(ssh_client)

    if not LIVE:
        LOGGER.info('Simulated stalled-shutdown hosts: %s',
                    ','.join([host for i, host in enumerate(OTHER_NCNS) if host_mask & (1 << i)]))

    finish_shutdown(username, password)
    LOGGER.info('Shutdown complete.')
