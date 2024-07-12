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
import functools
import json
import logging

from inflect import engine
from paramiko.ssh_exception import SSHException

from sat.util import prompt_continue
from sat.cli.bootsys.cron import CronJobError, modify_cron_job

LOGGER = logging.getLogger(__name__)


class FilesystemError(OSError):
    """Error detecting, mounting, or unmounting a filesystem."""
    pass


def convert_ssh_exception(func):

    @functools.wraps(func)
    def wrapper(*args, **kwargs):
        try:
            return func(*args, **kwargs)
        except SSHException as err:
            raise FilesystemError(
                f'Error executing command via SSH during {func.__name__}: {err}'
            ) from err

    return wrapper


@convert_ssh_exception
def modify_ensure_ceph_mounts_cron_job(ssh_client, hostname, enabled=False):
    """Enable or disable the cron job that ensures ceph and s3fs filesystems are mounted.

    There is a cronjob defined at `/etc/cron.d/ensure-ceph-mounts` that runs
    every minute and ensures all filesystems of type fuse.s3fs (and one specific
    ceph filesystem) are mounted. This function either enables or disables that
    cronjob by commenting or uncommenting the crontab entry in this file.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client connected to the host
            where commands should be executed
        hostname (str): the hostname associated with the ssh_client (for logging)
        enabled (bool): if True, then ensure the cron job is enabled. If False,
            then ensure the cron job is disabled.

    Raises:
        FilesystemError: if there is an error executing the command to disable
            the automatic filesystem mounting job
    """
    try:
        modify_cron_job(ssh_client, hostname, '/etc/cron.d/ensure-ceph-mounts', enabled=enabled)
    except CronJobError as err:
        err_msg = (
            f'Failed to {"enable" if enabled else "disable"} cron job that ensures '
            f'Ceph and s3fs filesystems are mounted on {hostname}: {err}'
        )
        raise FilesystemError(err_msg) from err


@convert_ssh_exception
def find_rbd_device_mounts(ssh_client, hostname):
    """Find mount points for RBD devices on the system.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client connected to the host
            where commands should be executed
        hostname (str): the hostname associated with the ssh_client (for logging)

    Raises:
        FilesystemError: if there is a problem listing RBD devices or mount points

    Returns:
        list of str: the list of mount points where RBD devices are mounted
    """
    rbd_list_cmd = 'rbd device list --format json'
    _, stdout, stderr = ssh_client.exec_command(rbd_list_cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code:
        raise FilesystemError(
            f'Command "{rbd_list_cmd}" failed to list mapped RBD devices on '
            f'{hostname}: {stderr.read().decode()}'
        )

    mounted_rbd_devices = []

    rbd_device_list = json.loads(stdout.read().decode())
    for rbd_device in rbd_device_list:
        device_path = rbd_device.get('device')
        if not device_path:
            LOGGER.warning(f'Unable to determine device path for RBD device {rbd_device}, skipping')
            continue

        LOGGER.info(f'Checking for mounts of RBD device {device_path} on {hostname}')

        findmnt_cmd = f'findmnt --source {device_path} --output TARGET -n'
        _, stdout, stderr = ssh_client.exec_command(findmnt_cmd)
        exit_code = stdout.channel.recv_exit_status()

        rbd_mount_point = stdout.read().decode().strip()
        if exit_code or not rbd_mount_point:
            LOGGER.info(f'No mount of RBD device {device_path} found on {hostname}')
            continue

        LOGGER.info(f'Found mount of RBD device {device_path} at {rbd_mount_point} on {hostname}')
        mounted_rbd_devices.append(rbd_mount_point)

    return mounted_rbd_devices


@convert_ssh_exception
def find_ceph_and_s3fs_mounts(ssh_client, hostname):
    """Find Ceph and s3fs mounts.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client connected to the host
            where commands should be executed
        hostname (str): the hostname associated with the ssh_client (for logging)

    Raises:
        FilesystemError: if there is a problem finding ceph or s3fs mount points

    Returns:
        list of str: the list of mount points of ceph and s3fs filesystems
    """
    # Finds filesystems of type ceph or fuse.s3fs and only outputs the TARGET with no headers
    findmnt_cmd = 'findmnt --types ceph,fuse.s3fs --output TARGET -n'
    _, stdout, stderr = ssh_client.exec_command(findmnt_cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code:
        raise FilesystemError(
            f'Command "{findmnt_cmd}" failed to list mounted Ceph or s3fs '
            f'filesystems on {hostname}: {stderr.read()}'
        )

    return stdout.read().decode().splitlines()


@convert_ssh_exception
def check_mount_activity(ssh_client, hostname, mount_points):
    """Check whether mounts are active or not.

    For each given mount point on the given hostname, check whether the mount
    point is currently in use, and if so, give the user an opportunity to stop
    any processes using the mount point. Keep looping until all given mount
    points are no longer in use.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client connected to the host
            where commands should be executed
        hostname (str): the hostname associated with the ssh_client (for logging)
        mount_points (list of str): the list of mount points to check for activity

    Raises:
        FilesystemError: if there is a problem listing RBD devices or mount points
        SystemExit: if the admin decides not to continue with unmounts
    """
    while True:
        mount_points_in_use = False
        for mount_point in mount_points:
            lsof_cmd = f'lsof {mount_point}'

            LOGGER.info(f'Checking whether mount point {mount_point} is in use on {hostname}')

            _, stdout, _ = ssh_client.exec_command(lsof_cmd)
            exit_code = stdout.channel.recv_exit_status()

            # lsof exits with non-zero exit status when mount point is not in use
            if exit_code:
                LOGGER.info(f'Mount point {mount_point} is not in use on {hostname}')
                continue

            # lsof exits with zero exit status when mount point is in use
            mount_points_in_use = True
            LOGGER.info(f'Mount point {mount_point} is in use by the following processes on {hostname}:')
            LOGGER.info(f'{stdout.read().decode()}')

        if mount_points_in_use:
            prompt_continue(
                'unmount of filesystems',
                'Some filesystems to be unmounted remain in use. '
                'Please address this before continuing.'
            )
        elif mount_points:
            LOGGER.info('All mount points are not in use and ready to be unmounted')
            break
        else:
            LOGGER.debug('No mount points to be checked')
            break


@convert_ssh_exception
def unmount_filesystems(ssh_client, hostname, mount_points):
    """Unmount filesystems mounted at given mount points.

    All given mount points are assumed not to be currently in use by running
    processes. Unmounting will fail if filesystems are currently in use.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client connected to the host
            where commands should be executed
        hostname (str): the hostname associated with the ssh_client (for logging)
        mount_points (list of str): the list of mount points to be unmounted

    Raises:
        FilesystemError: if there is an error unmounting any filesystems
    """
    failed_unmounts = []

    for mount_point in mount_points:
        LOGGER.info(f'Unmounting {mount_point} on {hostname}')
        umount_cmd = f'umount {mount_point}'
        _, stdout, stderr = ssh_client.exec_command(umount_cmd)
        exit_code = stdout.channel.recv_exit_status()

        if exit_code:
            LOGGER.error(f'"{umount_cmd}" failed with exit code {exit_code}: {stderr.read().decode()}')
            failed_unmounts.append(mount_point)
            continue

        LOGGER.info(f'Successfully unmounted {mount_point} on {hostname}')

    if failed_unmounts:
        raise FilesystemError(f'Failed to unmount {len(failed_unmounts)}/{len(mount_points)} filesystems.')


@convert_ssh_exception
def unmap_rbd_devices(ssh_client, hostname):
    """Unmap all RBD devices on the given host.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client connected to the host
            where commands should be executed
        hostname (str): the hostname associated with the ssh_client (for logging)

    Raises:
        FilesystemError: if there is a failure to unmap RBD devices
    """
    rbdmap_cmd = 'rbdmap unmap-all'
    _, stdout, stderr = ssh_client.exec_command(rbdmap_cmd)
    exit_status = stdout.channel.recv_exit_status()
    if exit_status != 0:
        raise FilesystemError(
            f'Failed to unmap all RBD devices on {hostname}. Command '
            f'"{rbdmap_cmd}" exited with exit code {exit_status}: {stderr.read().decode()}'
        )


def do_ceph_unmounts(ssh_client, hostname):
    """Find all filesystems provided by Ceph and unmount them on the given host.

    Find all filesystems which are backed by Ceph storage (filesystems of type
    ceph or fuse.s3fs or filesystems on RBD devices), check whether the mounts
    are in use, and then unmount the filesystems when the admin has stopped any
    processes using the mount points.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client to use to connect to ncn-m001
        hostname (str): the hostname to connect to

    Raises:
        FilesystemError: if there is an error finding and unmounting filesystems.
    """
    inflector = engine()

    try:
        ssh_client.connect(hostname)
    except SSHException as err:
        raise FilesystemError(f'Failed to connect to {hostname} via SSH: {err}')

    fs_descriptor = 'mounted RBD device'
    LOGGER.info(f'Finding {inflector.plural(fs_descriptor)} on {hostname}')
    rbd_device_mounts = find_rbd_device_mounts(ssh_client, hostname)
    LOGGER.info(f'Found {inflector.no(fs_descriptor, len(rbd_device_mounts))} on {hostname}')

    fs_descriptor = 'mounted Ceph or s3fs filesystem'
    LOGGER.info(f'Finding {inflector.plural(fs_descriptor)} on {hostname}')
    ceph_s3fs_mounts = find_ceph_and_s3fs_mounts(ssh_client, hostname)
    LOGGER.info(f'Found {inflector.no(fs_descriptor, len(ceph_s3fs_mounts))} on {hostname}')

    if not(rbd_device_mounts or ceph_s3fs_mounts):
        return

    LOGGER.info(f'Checking whether mounts are in use on {hostname}')
    mount_points = ceph_s3fs_mounts + rbd_device_mounts
    check_mount_activity(ssh_client, hostname, mount_points)

    LOGGER.info(f'Disabling cron job that ensures Ceph and s3fs filesystems are mounted on {hostname}')
    modify_ensure_ceph_mounts_cron_job(ssh_client, hostname, enabled=False)
    LOGGER.info(f'Successfully disabled cron job on {hostname}')

    fs_descriptor = f'{inflector.no("filesystem", len(mount_points))} on {hostname}'
    LOGGER.info(f'Unmounting {fs_descriptor}')
    unmount_filesystems(ssh_client, hostname, mount_points)
    LOGGER.info(f'Successfully unmounted {fs_descriptor}')

    LOGGER.info(f'Unmapping all RBD devices on {hostname}')
    unmap_rbd_devices(ssh_client, hostname)
    LOGGER.info(f'Successfully unmapped all RBD devices on {hostname}')
