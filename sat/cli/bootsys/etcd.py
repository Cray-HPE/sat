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
Perform actions related to etcd on a Shasta system.
"""
import logging
import os
import socket

from sat.cli.bootsys.util import get_ssh_client

from paramiko import SSHException

LOGGER = logging.getLogger(__name__)

# This is where the snapshot will be saved for consistency with the location
# used by the old platform-shutdown.yml Ansible playbook
ETCD_SNAPSHOT_DIR = '/root/etcd_backup'

# This is the name of the snapshot file
ETCD_SNAPSHOT_FILE = 'backup.db'


class EtcdSnapshotFailure(Exception):
    """Failed to save a snapshot of etcd."""
    pass


class EtcdInactiveFailure(EtcdSnapshotFailure):
    """Failed to save a snapshot of etcd because etcd was inactive."""
    pass


def save_etcd_snapshot_on_host(hostname, host_keys=None):
    """Connect to the given host and save an etcd snapshot to a file.

    Args:
        hostname (str): the hostname to connect to
        host_keys (paramiko.HostKeys or None): the hostkeys to use when
            connecting over SSH

    Raises:
        EtcdInactiveFailure: if the etcd service is inactive, indicating that
            an attempt to save a snapshot would hang
        EtcdSnapshotFailure: if there is a failure to create the directory for
            the snapshot or a failure to create the snapshot
    """
    ssh_client = get_ssh_client(host_keys=host_keys)

    try:
        ssh_client.connect(hostname)
    except (SSHException, socket.error) as err:
        raise EtcdSnapshotFailure(f'Failed to connect to {hostname}: {err}')

    # If etcd is not active, attempting to create a snapshot will hang
    try:
        _, stdout, stderr = ssh_client.exec_command("systemctl is-active etcd")
    except SSHException as err:
        raise EtcdSnapshotFailure(f'Failed to determine if etcd is active on {hostname} '
                                  f'before attempting snapshot: {err}')

    exit_status = stdout.channel.recv_exit_status()
    if exit_status:
        raise EtcdInactiveFailure(f'The etcd service is not active on {hostname} '
                                  f'so a snapshot cannot be created.')

    mkdir_cmd = f'mkdir -p {ETCD_SNAPSHOT_DIR}'
    etcd_cmd = (f'ETCDCTL_API=3 '
                f'etcdctl --cacert /etc/kubernetes/pki/etcd/ca.crt '
                f'--cert /etc/kubernetes/pki/etcd/peer.crt '
                f'--key /etc/kubernetes/pki/etcd/peer.key '
                f'snapshot save {os.path.join(ETCD_SNAPSHOT_DIR, ETCD_SNAPSHOT_FILE)}')
    commands = [mkdir_cmd, etcd_cmd]

    for command in commands:
        try:
            _, stdout, stderr = ssh_client.exec_command(command)
        except SSHException as err:
            raise EtcdSnapshotFailure(f'Failed to execute "{command}" on {hostname}: {err}')

        exit_status = stdout.channel.recv_exit_status()
        if exit_status:
            raise EtcdSnapshotFailure(
                f'Command "{command}" on {hostname} exited with non-zero exit status: '
                f'{exit_status}, stderr: {stderr.read()}, stdout: {stdout.read()}'
            )
