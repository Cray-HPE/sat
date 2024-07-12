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
Tests for filesystem discovery, activity checking, and mounting in filesystems module.
"""
import json
import unittest
from unittest.mock import MagicMock, patch

from sat.cli.bootsys.filesystems import (
    FilesystemError,
    check_mount_activity,
    do_ceph_unmounts,
    find_rbd_device_mounts,
    find_ceph_and_s3fs_mounts,
    modify_ensure_ceph_mounts_cron_job,
    unmap_rbd_devices,
    unmount_filesystems,
)


class TestModifyEnsureCephMountsCronJob(unittest.TestCase):

    def setUp(self):
        self.mock_ssh_client = MagicMock()
        self.hostname = 'ncn-m001'
        self.cron_job_file = '/etc/cron.d/ensure-ceph-mounts'

    def test_modify_ensure_ceph_mounts_cron_job_enable(self):
        """Test that the function enables the cron job."""
        with patch('sat.cli.bootsys.filesystems.modify_cron_job') as mock_modify_cron_job:
            modify_ensure_ceph_mounts_cron_job(self.mock_ssh_client, self.hostname, enabled=True)
        mock_modify_cron_job.assert_called_once_with(self.mock_ssh_client, self.hostname,
                                                     self.cron_job_file, enabled=True)

    def test_modify_ensure_ceph_mounts_cron_job_disable(self):
        """Test that the function disables the cron job."""
        with patch('sat.cli.bootsys.filesystems.modify_cron_job') as mock_modify_cron_job:
            modify_ensure_ceph_mounts_cron_job(self.mock_ssh_client, self.hostname, enabled=False)
        mock_modify_cron_job.assert_called_once_with(self.mock_ssh_client, self.hostname,
                                                     self.cron_job_file, enabled=False)


class TestFindRbdDeviceMounts(unittest.TestCase):

    def setUp(self):
        """Create a temporary file containing fake mount entries."""
        self.fake_rbd_devices = [
            {
                'id': 0,
                'pool': 'kube',
                'namespace': '',
                'name': 'admin',
                'snap': '-',
                'device': '/dev/rbd0'
            },
            {
                'id': 1,
                'pool': 'kube',
                'namespace': '',
                'name': 'developer',
                'snap': '-',
                'device': '/dev/rbd1'
            }
        ]

        self.rbd_device_list_exit_status = 0
        self.findmnt_exit_status = 0
        self.rbd_devices_mounted = True

        def fake_ssh_exec_command(command):
            """Fake execution of a command via SSH by executing it locally."""
            output = ''
            exit_status = 0
            if 'rbd device list' in command:
                output = json.dumps(self.fake_rbd_devices)
                exit_status = self.rbd_device_list_exit_status
            elif 'findmnt' in command:
                if self.rbd_devices_mounted:
                    for device in self.fake_rbd_devices:
                        if device['device'] in command:
                            output = f'/mnt/{device["name"]}'
                            break
                exit_status = self.findmnt_exit_status

            stdin = MagicMock()
            stderr = MagicMock()
            stdout = MagicMock()
            stdout.channel.recv_exit_status.return_value = exit_status
            stdout.read.return_value = output.encode()
            return stdin, stdout, stderr

        self.mock_ssh_client = MagicMock()
        self.mock_ssh_client.exec_command.side_effect = fake_ssh_exec_command
        self.hostname = 'ncn-m001'

    def test_find_rbd_device_mounts(self):
        """Test that the function returns the expected RBD device mounts."""
        rbd_device_mounts = find_rbd_device_mounts(self.mock_ssh_client, self.hostname)
        self.assertEqual(rbd_device_mounts,
                         ['/mnt/admin', '/mnt/developer'])

    def test_find_rbd_device_mounts_no_rbd_devices(self):
        """Test that the function returns an empty list when there are no RBD devices."""
        self.fake_rbd_devices = []
        rbd_device_mounts = find_rbd_device_mounts(self.mock_ssh_client, self.hostname)
        self.assertEqual(rbd_device_mounts, [])

    def test_find_rbd_device_mounts_no_mounts(self):
        """Test that the function returns an empty list when there are no mounts."""
        self.rbd_devices_mounted = False
        rbd_device_mounts = find_rbd_device_mounts(self.mock_ssh_client, self.hostname)
        self.assertEqual(rbd_device_mounts, [])

    def test_find_rbd_device_mounts_rbd_device_list_error(self):
        """Test that the function returns an empty list when 'rbd device list' exits with an error."""
        self.rbd_device_list_exit_status = 1
        with self.assertRaisesRegex(FilesystemError, 'failed to list mapped RBD devices'):
            find_rbd_device_mounts(self.mock_ssh_client, self.hostname)

    def test_find_rbd_device_mounts_findmnt_error(self):
        """Test that the function returns an empty list when 'findmnt' exits with an error."""
        self.findmnt_exit_status = 1
        with self.assertLogs(level='INFO') as logs_cm:
            rbd_device_mounts = find_rbd_device_mounts(self.mock_ssh_client, self.hostname)
        self.assertEqual(rbd_device_mounts, [])
        self.assertEqual(4, len(logs_cm.records))
        self.assertEqual(f'No mount of RBD device /dev/rbd0 found on {self.hostname}',
                         logs_cm.records[1].message)
        self.assertEqual(f'No mount of RBD device /dev/rbd1 found on {self.hostname}',
                         logs_cm.records[3].message)

    def test_find_rbd_device_mounts_missing_device_key(self):
        """Test that the function logs a warning and skips any RBD devices missing the 'device' key."""
        self.fake_rbd_devices.append(
            # Add an RBD device where the 'device' key is missing
            {
                'id': 2,
                'pool': 'kube',
                'namespace': '',
                'name': 'missing',
                'snap': '-'
            }
        )
        with self.assertLogs(level='WARNING') as logs_cm:
            rbd_device_mounts = find_rbd_device_mounts(self.mock_ssh_client, self.hostname)
        self.assertEqual(rbd_device_mounts, ['/mnt/admin', '/mnt/developer'])
        self.assertEqual(1, len(logs_cm.records))
        self.assertRegex(logs_cm.records[0].message,
                         r'Unable to determine device path for RBD device .* skipping')


class TestFindCephAndS3fsMounts(unittest.TestCase):

    def setUp(self):
        """Set up fake mount entries."""
        self.fake_ceph_mount_points = [
            '/etc/cray/upgrade/csm'
        ]
        self.fake_s3fs_mount_points = [
            '/var/opt/cray/sdu/collection-mount',
            '/var/opt/cray/config-data'
        ]
        self.mount_points = self.fake_ceph_mount_points + self.fake_s3fs_mount_points
        self.find_mnt_exit_code = 0

        def fake_ssh_exec_command(command):
            """Fake execution of a command via SSH by executing it locally."""
            stdin = MagicMock()
            stderr = MagicMock()
            stdout = MagicMock()
            if 'findmnt' in command:
                stdout.channel.recv_exit_status.return_value = self.find_mnt_exit_code
                stdout.read.return_value = '\n'.join(self.mount_points).encode()
            else:
                # Only 'findmnt' is expected to be called
                stdout.channel.recv_exit_status.return_value = 1
                stderr.read.return_value = 'command not found'.encode()
            return stdin, stdout, stderr

        self.mock_ssh_client = MagicMock()
        self.mock_ssh_client.exec_command.side_effect = fake_ssh_exec_command
        self.hostname = 'ncn-m001'

    def test_find_ceph_and_s3fs_mounts(self):
        """Test that the function returns the expected Ceph and S3FS mount points."""
        mount_points = find_ceph_and_s3fs_mounts(self.mock_ssh_client, self.hostname)
        self.assertEqual(self.mount_points, mount_points)

    def test_find_ceph_and_s3fs_mounts_no_mounts(self):
        """Test that the function returns an empty list when there are no mounts."""
        self.mount_points = []
        mount_points = find_ceph_and_s3fs_mounts(self.mock_ssh_client, self.hostname)
        self.assertEqual(mount_points, [])

    def test_find_ceph_and_s3fs_mounts_findmnt_error(self):
        """Test that the function returns an empty list when 'findmnt' exits with an error."""
        self.find_mnt_exit_code = 1
        self.mount_points = []
        with self.assertRaisesRegex(FilesystemError, 'failed to list mounted Ceph or s3fs filesystems'):
            find_ceph_and_s3fs_mounts(self.mock_ssh_client, self.hostname)


class TestCheckMountActivity(unittest.TestCase):

    def setUp(self):
        self.hostname = 'ncn-m001'
        # This dictionary maps from a mount point name to a boolean indicating
        # whether the mount point is in use
        self.mount_points_to_status = {
            '/mnt/admin': False,
            '/mnt/developer': False
        }
        self.lsof_output = '\n'.join([
            'COMMAND     PID USER   FD   TYPE DEVICE SIZE/OFF NODE NAME',
            'bash       1234 root  cwd    DIR  253,0     4096    2 {mount_point}'
        ])

        def fake_ssh_exec_command(command):
            """Fake execution of the lsof command via SSH"""
            stdin = MagicMock()
            stderr = MagicMock()
            stdout = MagicMock()
            if 'lsof' in command:
                # Begin by assuming mount point not recognized
                stdout.channel.recv_exit_status.return_value = 1
                for mount_point, in_use in self.mount_points_to_status.items():
                    if mount_point in command and in_use:
                        stdout.channel.recv_exit_status.return_value = 0
                        stdout.read.return_value = self.lsof_output.format(mount_point=mount_point).encode()
            else:
                # Only 'lsof' is expected to be called
                stdout.channel.recv_exit_status.return_value = 1
                stderr.read.return_value = 'command not found'.encode()
            return stdin, stdout, stderr

        self.mock_ssh_client = MagicMock()
        self.mock_ssh_client.exec_command.side_effect = fake_ssh_exec_command

    def test_check_mount_activity_one_mount_in_use(self):
        """Test that the function prompts the user to continue when one mount point is in use."""
        # Set one of the mount points to be in use
        mount_point_in_use = '/mnt/admin'
        mount_point_not_in_use = '/mnt/developer'
        self.mount_points_to_status[mount_point_in_use] = True

        # Mock prompt_continue to simulate admin stopping processes currently
        # using the mount point and then continuing
        def fake_prompt_continue(*args, **kwargs):
            for mount_point in self.mount_points_to_status.keys():
                self.mount_points_to_status[mount_point] = False
            return True

        with patch('sat.cli.bootsys.filesystems.prompt_continue', side_effect=fake_prompt_continue):
            with self.assertLogs(level='INFO') as logs_cm:
                check_mount_activity(self.mock_ssh_client, self.hostname,
                                     self.mount_points_to_status.keys())

        info_log_messages = [record.message for record in logs_cm.records if record.levelname == 'INFO']
        self.assertEqual(10, len(info_log_messages))
        self.assertEqual(
            [
                f'Checking whether mount point {mount_point_in_use} is in use on {self.hostname}',
                f'Mount point {mount_point_in_use} is in use by the following processes on {self.hostname}:',
                self.lsof_output.format(mount_point=mount_point_in_use),
                f'Checking whether mount point {mount_point_not_in_use} is in use on {self.hostname}',
                f'Mount point {mount_point_not_in_use} is not in use on {self.hostname}',
                f'Checking whether mount point {mount_point_in_use} is in use on {self.hostname}',
                f'Mount point {mount_point_in_use} is not in use on {self.hostname}',
                f'Checking whether mount point {mount_point_not_in_use} is in use on {self.hostname}',
                f'Mount point {mount_point_not_in_use} is not in use on {self.hostname}',
                'All mount points are not in use and ready to be unmounted'
            ],
            info_log_messages
        )

    def test_check_mount_activity_all_mounts_in_use(self):
        """Test that the function prompts the user to continue when all mount points are in use."""
        # Set all mount points to be in use
        mount_points = list(self.mount_points_to_status.keys())
        for mount_point in mount_points:
            self.mount_points_to_status[mount_point] = True

        # Mock prompt_continue to simulate admin stopping processes currently
        # using the mount point and then continuing
        def fake_prompt_continue(*args, **kwargs):
            for mp in mount_points:
                self.mount_points_to_status[mp] = False
            return True

        with patch('sat.cli.bootsys.filesystems.prompt_continue', side_effect=fake_prompt_continue):
            with self.assertLogs(level='INFO') as logs_cm:
                check_mount_activity(self.mock_ssh_client, self.hostname,
                                     mount_points)

        info_log_messages = [record.message for record in logs_cm.records if record.levelname == 'INFO']
        self.assertEqual(11, len(info_log_messages))
        self.assertEqual(
            [
                f'Checking whether mount point {mount_points[0]} is in use on {self.hostname}',
                f'Mount point {mount_points[0]} is in use by the following processes on {self.hostname}:',
                self.lsof_output.format(mount_point=mount_points[0]),
                f'Checking whether mount point {mount_points[1]} is in use on {self.hostname}',
                f'Mount point {mount_points[1]} is in use by the following processes on {self.hostname}:',
                self.lsof_output.format(mount_point=mount_points[1]),
                f'Checking whether mount point {mount_points[0]} is in use on {self.hostname}',
                f'Mount point {mount_points[0]} is not in use on {self.hostname}',
                f'Checking whether mount point {mount_points[1]} is in use on {self.hostname}',
                f'Mount point {mount_points[1]} is not in use on {self.hostname}',
                'All mount points are not in use and ready to be unmounted'
            ],
            info_log_messages
        )

    def test_check_mount_activity_no_mounts_in_use(self):
        """Test that the function does not prompt the user to continue when no mount points are in use."""
        # Set all mount points to be not in use (already default from setUp)
        for mount_point in self.mount_points_to_status.keys():
            self.mount_points_to_status[mount_point] = False

        with self.assertLogs(level='INFO') as logs_cm:
            check_mount_activity(self.mock_ssh_client, self.hostname,
                                 self.mount_points_to_status.keys())

        info_log_messages = [record.message for record in logs_cm.records if record.levelname == 'INFO']
        self.assertEqual(5, len(info_log_messages))
        self.assertEqual(
            [
                f'Checking whether mount point /mnt/admin is in use on {self.hostname}',
                f'Mount point /mnt/admin is not in use on {self.hostname}',
                f'Checking whether mount point /mnt/developer is in use on {self.hostname}',
                f'Mount point /mnt/developer is not in use on {self.hostname}',
                'All mount points are not in use and ready to be unmounted'
            ],
            info_log_messages
        )

    def test_check_mount_activity_no_mounts(self):
        """Test that the function does not prompt the user to continue when no mount points are provided."""
        with self.assertLogs(level='DEBUG') as logs_cm:
            check_mount_activity(self.mock_ssh_client, self.hostname, [])

        debug_log_messages = [record.message for record in logs_cm.records if record.levelname == 'DEBUG']
        self.assertEqual(1, len(debug_log_messages))
        self.assertEqual(
            [
                'No mount points to be checked'
            ],
            debug_log_messages
        )


class TestUnmountFilesystems(unittest.TestCase):

    def setUp(self):
        self.hostname = 'ncn-m001'
        self.umount_success_by_mount_point = {
            '/mnt/admin': True,
            '/mnt/developer': True
        }
        self.mount_points = list(self.umount_success_by_mount_point.keys())

        def fake_ssh_exec_command(command):
            """Fake execution of the umount command via SSH"""
            stdin = MagicMock()
            stderr = MagicMock()
            stdout = MagicMock()
            if 'umount' in command:
                # if the mount point is unknown, we will fail
                stdout.channel.recv_exit_status.return_value = 1
                for mount_point, success in self.umount_success_by_mount_point.items():
                    if mount_point in command:
                        if success:
                            stdout.channel.recv_exit_status.return_value = 0
                        else:
                            stdout.channel.recv_exit_status.return_value = 1
                            stderr.read.return_value = f'mount point busy'.encode()
            else:
                # Only 'umount' is expected to be called
                stdout.channel.recv_exit_status.return_value = 1
                stderr.read.return_value = 'command not found'.encode()
            return stdin, stdout, stderr

        self.mock_ssh_client = MagicMock()
        self.mock_ssh_client.exec_command.side_effect = fake_ssh_exec_command

    def test_unmount_filesystems(self):
        """Test that the function successfully unmounts the filesystems."""
        with self.assertLogs(level='INFO') as logs_cm:
            unmount_filesystems(self.mock_ssh_client, self.hostname, self.mount_points)

        info_log_messages = [record.message for record in logs_cm.records if record.levelname == 'INFO']
        self.assertEqual(4, len(info_log_messages))
        self.assertEqual(
            [
                f'Unmounting {self.mount_points[0]} on {self.hostname}',
                f'Successfully unmounted {self.mount_points[0]} on {self.hostname}',
                f'Unmounting {self.mount_points[1]} on {self.hostname}',
                f'Successfully unmounted {self.mount_points[1]} on {self.hostname}'
            ],
            info_log_messages
        )

    def test_unmount_filesystems_one_failure(self):
        """Test that the function logs an error when unmounting one mount point fails."""
        self.umount_success_by_mount_point[self.mount_points[0]] = False
        with self.assertRaisesRegex(FilesystemError, 'Failed to unmount 1/2 filesystems'):
            with self.assertLogs(level='ERROR') as logs_cm:
                unmount_filesystems(self.mock_ssh_client, self.hostname, self.mount_points)

        error_log_messages = [record.message for record in logs_cm.records if record.levelname == 'ERROR']
        self.assertEqual(1, len(error_log_messages))
        self.assertEqual(
            f'"umount {self.mount_points[0]}" failed with exit code 1: mount point busy',
            error_log_messages[0]
        )

    def test_unmount_filesystems_both_fail(self):
        """Test that the function logs an error when unmounting both mount points fails."""
        for mount_point in self.mount_points:
            self.umount_success_by_mount_point[mount_point] = False

        with self.assertRaisesRegex(FilesystemError, 'Failed to unmount 2/2 filesystems'):
            with self.assertLogs(level='ERROR') as logs_cm:
                unmount_filesystems(self.mock_ssh_client, self.hostname, self.mount_points)

        error_log_messages = [record.message for record in logs_cm.records if record.levelname == 'ERROR']
        self.assertEqual(2, len(error_log_messages))
        self.assertEqual(
            [
                f'"umount {self.mount_points[0]}" failed with exit code 1: mount point busy',
                f'"umount {self.mount_points[1]}" failed with exit code 1: mount point busy'
            ],
            error_log_messages
        )

    def test_unmount_filesystems_no_mount_points(self):
        """Test that the function does nothing no mount points are provided."""
        unmount_filesystems(self.mock_ssh_client, self.hostname, [])
        self.mock_ssh_client.exec_command.assert_not_called()


class TestUnmapRbdDevices(unittest.TestCase):

    def setUp(self):
        self.hostname = 'ncn-m001'
        self.rbd_unmap_all_exit_status = 0

        def fake_ssh_exec_command(command):
            """Fake execution of the "rbd unmap-all" command via SSH"""
            stdin = MagicMock()
            stderr = MagicMock()
            stdout = MagicMock()
            if 'rbdmap unmap-all' in command:
                stdout.channel.recv_exit_status.return_value = self.rbd_unmap_all_exit_status
            else:
                # Only 'rbdmap unmap-all' is expected to be called
                stdout.channel.recv_exit_status.return_value = 1
                stderr.read.return_value = 'command not found'.encode()
            return stdin, stdout, stderr

        self.mock_ssh_client = MagicMock()
        self.mock_ssh_client.exec_command.side_effect = fake_ssh_exec_command

    def test_unmap_rbd_devices(self):
        """Test that the function successfully unmaps the RBD devices."""
        unmap_rbd_devices(self.mock_ssh_client, self.hostname)
        self.mock_ssh_client.exec_command.assert_called_once_with('rbdmap unmap-all')

    def test_unmap_rbd_devices_error(self):
        """Test that the function raises an exception when unmap-all fails."""
        self.rbd_unmap_all_exit_status = 1
        with self.assertRaisesRegex(FilesystemError, 'Failed to unmap all RBD devices'):
            unmap_rbd_devices(self.mock_ssh_client, self.hostname)


class TestDoCephUnmounts(unittest.TestCase):

    def setUp(self):
        # create a mock ssh_client that does nothing
        self.mock_ssh_client = MagicMock()
        self.hostname = 'ncn-m001'
        self.rbd_mounts = [
            '/mnt/admin',
            '/mnt/developer'
        ]
        self.ceph_and_s3fs_mounts = [
            '/etc/cray/upgrade/csm',
            '/var/opt/cray/sdu/collection-mount',
            '/var/opt/cray/config-data'
        ]
        # Mock functions called by do_ceph_unmounts
        self.mock_find_rbd_device_mounts = patch('sat.cli.bootsys.filesystems.find_rbd_device_mounts').start()
        self.mock_find_rbd_device_mounts.return_value = self.rbd_mounts
        self.mock_find_ceph_and_s3fs_mounts = patch('sat.cli.bootsys.filesystems.find_ceph_and_s3fs_mounts').start()
        self.mock_find_ceph_and_s3fs_mounts.return_value = self.ceph_and_s3fs_mounts
        self.mock_check_mount_activity = patch('sat.cli.bootsys.filesystems.check_mount_activity').start()
        self.mock_modify_ensure_ceph_mounts_cron_job = patch(
            'sat.cli.bootsys.filesystems.modify_ensure_ceph_mounts_cron_job').start()
        self.mock_unmount_filesystems = patch('sat.cli.bootsys.filesystems.unmount_filesystems').start()
        self.mock_unmap_rbd_devices = patch('sat.cli.bootsys.filesystems.unmap_rbd_devices').start()

    def tearDown(self):
        patch.stopall()

    def test_do_ceph_unmounts(self):
        """Test that the function successfully unmounts Ceph/s3fs filesystems and unmaps RBD devices"""
        with self.assertLogs(level='INFO') as logs_cm:
            do_ceph_unmounts(self.mock_ssh_client, self.hostname)

        info_log_messages = [record.message for record in logs_cm.records if record.levelname == 'INFO']
        self.assertEqual(11, len(logs_cm.records))
        self.assertEqual(
            [
                f'Finding mounted RBD devices on {self.hostname}',
                f'Found {len(self.rbd_mounts)} mounted RBD devices on {self.hostname}',
                f'Finding mounted Ceph or s3fs filesystems on {self.hostname}',
                f'Found {len(self.ceph_and_s3fs_mounts)} mounted Ceph or s3fs filesystems on {self.hostname}',
                f'Checking whether mounts are in use on {self.hostname}',
                f'Disabling cron job that ensures Ceph and s3fs filesystems are mounted on {self.hostname}',
                f'Successfully disabled cron job on {self.hostname}',
                f'Unmounting {len(self.rbd_mounts) + len(self.ceph_and_s3fs_mounts)} filesystems on {self.hostname}',
                (
                    f'Successfully unmounted {len(self.rbd_mounts) + len(self.ceph_and_s3fs_mounts)} '
                    f'filesystems on {self.hostname}'
                ),
                f'Unmapping all RBD devices on {self.hostname}',
                f'Successfully unmapped all RBD devices on {self.hostname}'
            ],
            info_log_messages
        )

    def test_do_ceph_unmounts_no_mounts(self):
        """Test that the function does nothing when there are no mounted RBD devices or Ceph/s3fs filesystems."""
        self.mock_find_rbd_device_mounts.return_value = []
        self.mock_find_ceph_and_s3fs_mounts.return_value = []
        do_ceph_unmounts(self.mock_ssh_client, self.hostname)
        self.mock_check_mount_activity.assert_not_called()
        self.mock_modify_ensure_ceph_mounts_cron_job.assert_not_called()
        self.mock_unmount_filesystems.assert_not_called()
        self.mock_unmap_rbd_devices.assert_not_called()

    def test_do_ceph_unmounts_check_mount_activity_exit(self):
        """Test that the function raises a FilesystemError when check_mount_activity raises SystemExit."""
        self.mock_check_mount_activity.side_effect = SystemExit(1)

        with self.assertRaises(SystemExit) as err_cm:
            do_ceph_unmounts(self.mock_ssh_client, self.hostname)

        self.assertEqual(1, err_cm.exception.code)
        # assert all functions after check_mount_activity are not called
        self.mock_modify_ensure_ceph_mounts_cron_job.assert_not_called()
        self.mock_unmount_filesystems.assert_not_called()
        self.mock_unmap_rbd_devices.assert_not_called()
