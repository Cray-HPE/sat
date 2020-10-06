"""
Restarts ceph services and waits for ceph to be healthy.

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
import json
import logging
import socket
import sys

from paramiko import SSHClient, SSHException

from sat.cli.bootsys.util import get_groups
from sat.cli.bootsys.waiting import Waiter
from sat.util import BeginEndLogger

LOGGER = logging.getLogger(__name__)


class CephHealthWaiter(Waiter):
    """Waiter for the Ceph cluster health status."""

    def __init__(self, timeout, poll_interval=1):
        self.host = 'ncn-m001'

        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(self.host)

        super().__init__(timeout, poll_interval=poll_interval)

    def condition_name(self):
        return "Ceph cluster in healthy state"

    def has_completed(self):
        try:
            ceph_command = 'ceph -s --format=json'
            _, stdout, _ = self.ssh_client.exec_command(ceph_command)

        except SSHException:
            LOGGER.error('Failed to execute command "%s" on host "%s".', ceph_command, self.host)
            return False

        try:
            rsp_dict = json.load(stdout)

        except json.decoder.JSONDecodeError as jde:
            LOGGER.error('Received malformed response from Ceph: %s', jde)
            return False

        try:
            # TODO: If the Ceph health criteria are updated, this will
            # need to be changes. (See SAT-559 for further
            # information.)
            return rsp_dict['health']['status'] == 'HEALTH_OK'

        except KeyError:
            LOGGER.error('Ceph JSON response is well-formed, but has an unexpected schema.')

            if 'health' not in rsp_dict:
                LOGGER.error('Missing top-level "health" key in Ceph JSON response.')
            elif 'status' not in rsp_dict['health']:
                LOGGER.error('Missing "status" key under "health" key in Ceph JSON response.')

            return False


def restart_ceph_services():
    """Restart ceph services on the storage nodes.

    This uses the ansible inventory to get the list of nodes designated as
    'storage' nodes.

    It iterates first over the nodes on which to restart the services,
    and then over the services to restart, restarting all the services for
    one node before proceeding to the next node.  This is different from the
    documented Shasta 1.3 procedure, on which this function is based.  The
    documented procedure restarts one service across all the nodes before
    proceeding to the next service.

    Raises:
        SystemExit: if connecting to one of the hosts failed, or if restarting
            one of the services failed
    """
    storage_nodes = get_groups(['storage'])
    ceph_services = ['ceph-mon.target', 'ceph-mgr.target', 'ceph-mds.target']
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()

    for storage_node in storage_nodes:
        try:
            ssh_client.connect(storage_node)
        except (SSHException, socket.error) as err:
            LOGGER.error(f'Connecting to {storage_node} failed.  Error: {err}')
            raise SystemExit(1)

        for ceph_service in ceph_services:
            command = f'systemctl restart {ceph_service}'
            try:
                _, stdout, stderr = ssh_client.exec_command(f'systemctl restart {ceph_service}')
            except SSHException as err:
                LOGGER.error(f'Command "{command}" failed.  Host: {storage_node}.  Error: {err}')
                raise SystemExit(1)

            # Command may run successfully but still return nonzero, which is an error.
            # Checking return status also blocks until the command completes.
            if stdout.channel.recv_exit_status():
                LOGGER.error(f'Command "{command}" failed.  Host: {storage_node}.  Stderr: {stderr.read()}')
                raise SystemExit(1)


def do_ceph_check(args):
    """Restart Ceph services and wait for Ceph health.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    with BeginEndLogger('restart ceph services on storage nodes'):
        restart_ceph_services()

    with BeginEndLogger('wait for ceph health'):
        ceph_waiter = CephHealthWaiter(args.ceph_timeout)
        if not ceph_waiter.wait_for_completion():
            sys.exit(1)
