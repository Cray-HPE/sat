#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
Manage the mounting and unmounting of filesystems during shutdown and boot.
"""
from collections import namedtuple
import json
import logging
import shlex

from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from sat.cli.bootsys.hostkeys import FilteredHostKeys
from sat.cli.bootsys.util import get_and_verify_ncn_groups, get_ssh_client, FatalBootsysError

LOGGER = logging.getLogger(__name__)


class FilesystemError(OSError):
    """Error detecting, mounting, or unmounting a filesystem."""
    pass


RBDDeviceMount = namedtuple('RBDDeviceMount', ['rbd_device_path', 'mount_point'])


def find_rbd_device_mounts(ssh_client, hostname):
    """Find mount points for RBD devices on the system.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client to use to connect to the host
        hostname (str): the hostname to connect to

    Raises:
        FilesystemError: if there is a problem listing RBD devices or mount points

    Returns:
        list of RBDDeviceMount: the list of mounted RBD devices with their path
            and mount point
    """
    ssh_client.connect(hostname)

    rbd_list_cmd = 'rbd device list --format json'
    stdin, stdout, stderr = ssh_client.exec_command(shlex.split(rbd_list_cmd))
    exit_code = stdout.channel.recv_exit_status()
    if exit_code:
        raise FilesystemError(
            f'Command "{rbd_list_cmd}" failed to list mapped RBD devices on '
            f'{hostname}: {stderr.read()}'
        )

    mounted_rbd_devices = []

    rbd_device_list = json.loads(stdout.read())
    for rbd_device in rbd_device_list:
        device_path = rbd_device.get('device')
        if not device_path:
            LOGGER.warning(f'Unable to determine device path for RBD device, skipping: {rbd_device}')
            continue

        LOGGER.info(f'Checking for mounts of RBD device {device_path} on {hostname}')

        findmnt_cmd = f'findmnt --source {device_path} --output TARGET -n'
        stdin, stdout, stderr = ssh_client.exec_command(shlex.split(findmnt_cmd))
        exit_code = stdout.channel.recv_exit_status()

        rbd_mount_point = stdout.read()
        if exit_code or not rbd_mount_point:
            LOGGER.info(f'No mount of RBD device {device_path} found on {hostname}')
            continue

        LOGGER.info(f'Found mount of RBD device {device_path} at {rbd_mount_point} on {hostname}')
        mounted_rbd_devices.append(RBDDeviceMount(device_path, rbd_mount_point))

    return mounted_rbd_devices


