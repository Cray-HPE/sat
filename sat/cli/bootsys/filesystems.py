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

from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from sat.cli.bootsys.hostkeys import FilteredHostKeys
from sat.cli.bootsys.util import get_and_verify_ncn_groups, get_ssh_client, FatalBootsysError
from sat.util import prompt_continue

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
    stdin, stdout, stderr = ssh_client.exec_command(rbd_list_cmd)
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
        stdin, stdout, stderr = ssh_client.exec_command(findmnt_cmd)
        exit_code = stdout.channel.recv_exit_status()

        rbd_mount_point = stdout.read()
        if exit_code or not rbd_mount_point:
            LOGGER.info(f'No mount of RBD device {device_path} found on {hostname}')
            continue

        LOGGER.info(f'Found mount of RBD device {device_path} at {rbd_mount_point} on {hostname}')
        mounted_rbd_devices.append(RBDDeviceMount(device_path, rbd_mount_point))

    return mounted_rbd_devices


def find_ceph_and_s3fs_mounts(ssh_client, hostname):
    """Find Ceph and s3fs mounts.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client to use to connect to the host
        hostname (str): the hostname to connect to

    Raises:
        FilesystemError: if there is a problem finding ceph or s3fs mount points

    Returns:
        list of str: the list of mount points of ceph and s3fs filesystems
    """
    ssh_client.connect(hostname)

    # Finds filesystems of type ceph or fuse.s3fs and only outputs the TARGET with no headers
    findmnt_cmd = 'findmnt --types ceph,fuse.s3fs --output TARGET -n'
    stdin, stdout, stderr = ssh_client.exec_command(findmnt_cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code:
        raise FilesystemError(
            f'Command "{findmnt_cmd}" failed to list mounted ceph or s3fs '
            f'filesystems on {hostname}: {stderr.read()}'
        )

    return stdout.read().decode().splitlines()


def prepare_umount(ssh_client, hostname, mount_points):
    """Check whether mounts are active or not.

    For each given mount point on the given hostname, check whether the mount
    point is currently in use, and if so, give the user an opportunity to stop
    any processes using the mount point.

        ssh_client (paramiko.SSHClient): the SSH client to use to connect to the host
        hostname (str): the hostname to connect to
        mount_points (list of str): the list of mount points to check for activity

    Raises:
        FilesystemError: if there is a problem listing RBD devices or mount points

    Returns:
        list of RBDDeviceMount: the list of mounted RBD devices with their path
            and mount point
    """
    ssh_client.connect(hostname)

    while True:
        mount_points_in_use = False
        for mount_point in mount_points:

            lsof_cmd = f'lsof {mount_point}'

            LOGGER.info(f'Checking whether mount point {mount_point} is in use.')

            stdin, stdout, stderr = ssh_client.exec_command(lsof_cmd)
            exit_code = stdout.channel.recv_exit_status()

            # lsof exits with non-zero exit status when mount point is not in use
            if exit_code:
                LOGGER.info(f'Mount point {mount_point} is not in use.')
                continue

            # lsof exits with zero exit status when mount point is in use
            mount_points_in_use = True
            LOGGER.info(f'Mount point {mount_point} is in use by the following processes:')
            LOGGER.info(f'{stdout.read()}')

        if mount_points_in_use:
            prompt_continue(
                'umount of filesystems',
                'Some filesystems to be unmounted remain in use. '
                'Please address this before continuing.'
            )
        elif mount_points:
            LOGGER.info('All mount points are ready to be unmounted.')
            break
        else:
            LOGGER.debug('No mount points to unmount.')
            break
