#
# MIT License
#
# (C) Copyright 2020-2021, 2024-2025 Hewlett Packard Enterprise Development LP
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
Tests for the sat.cli.bootsys.mgmt_power module.
"""
import logging
from argparse import Namespace
import unittest
from unittest.mock import MagicMock, patch, call
from unittest import mock

from paramiko.ssh_exception import SSHException, NoValidConnectionsError

from sat.cli.bootsys.mgmt_power import (
    do_power_off_ncns,
    SSHAvailableWaiter,
    IPMIPowerStateWaiter,
    do_mgmt_shutdown_power,
    FatalBootsysError,
    set_next_boot_device_to_disk
)
from sat.waiting import WaitingFailure
from sat.cli.bootsys.platform import do_ceph_freeze, FatalPlatformError


class TestSSHAvailableWaiter(unittest.TestCase):
    """Tests for the sat.cli.bootsys.mgmt_power.SSHAvailableWaiter class"""
    def setUp(self):
        self.mock_filtered_host_keys = patch('sat.cli.bootsys.mgmt_power.FilteredHostKeys').start()
        self.mock_get_ssh_client = patch('sat.cli.bootsys.mgmt_power.get_ssh_client').start()
        self.mock_ssh_client = self.mock_get_ssh_client.return_value
        self.members = ['ncn-w002', 'ncn-s001']
        self.timeout = 1

    def tearDown(self):
        patch.stopall()

    def test_pre_wait_action_loads_keys(self):
        """Test the SSH waiter loads system host keys through get_ssh_client."""
        SSHAvailableWaiter(self.members, self.timeout).pre_wait_action()
        self.mock_get_ssh_client.assert_called_once_with(
            host_keys=self.mock_filtered_host_keys.return_value
        )

    def test_ssh_available(self):
        """Test the SSH waiter detects available nodes"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.assertTrue(waiter.member_has_completed(self.members[0]))

    def test_ssh_not_available(self):
        """Test the SSH waiter detects node isn't available due to SSHException"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.mock_ssh_client.connect.side_effect = SSHException("SSH doesn't work")
        self.assertFalse(waiter.member_has_completed(self.members[0]))

    def test_ssh_not_available_no_valid_connection(self):
        """Test the SSH waiter detects node isn't available due to no valid connection"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.mock_ssh_client.connect.side_effect = NoValidConnectionsError(
            {('127.0.0.1', '22'): 'Something happened'})
        self.assertFalse(waiter.member_has_completed(self.members[0]))


class TestIPMIPowerStateWaiter(unittest.TestCase):
    def setUp(self):
        self.mock_subprocess_run = patch('sat.cli.bootsys.mgmt_power.subprocess.run').start()
        self.mock_subprocess_run.return_value.stdout = 'Chassis power is on'
        self.mock_subprocess_run.return_value.returncode = 0
        self.members = ['ncn-w002', 'ncn-s003', 'ncn-m001']
        self.timeout = 1
        self.username = 'root'
        self.password = 'pass'
        self.threshold = 3

    def tearDown(self):
        patch.stopall()

    def test_sending_ipmi_commands(self):
        """Test that the waiter sends IPMI commands if desired"""
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password,
                                      send_command=True)

        waiter.pre_wait_action()
        self.mock_subprocess_run.assert_called()

    def test_not_sending_ipmi_commands(self):
        """Test that the waiter does not sends IPMI commands if not desired"""
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password,
                                      send_command=False)
        waiter.pre_wait_action()
        self.mock_subprocess_run.assert_not_called()

    def test_ipmi_is_completed(self):
        """Test that IPMI command is complete in the desired state"""
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password)
        for member in self.members:
            self.assertTrue(waiter.member_has_completed(member))

    def test_ipmi_is_not_completed(self):
        """Test that IPMI command is incomplete when not in the desired state"""
        waiter = IPMIPowerStateWaiter(self.members, 'off', self.timeout, self.username, self.password)
        for member in self.members:
            self.assertFalse(waiter.member_has_completed(member))

    def test_ipmi_command_fails_logs_once(self):
        """Test that a failing ipmitool command only logs one message"""
        self.mock_subprocess_run.return_value.returncode = 1
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password,
                                      failure_threshold=self.threshold)
        with self.assertLogs(level='WARNING') as cm:
            for _ in range(self.threshold - 1):
                waiter.member_has_completed(self.members[0])

        self.assertEqual(len(cm.output), 1)

    def test_ipmi_command_fails_then_succeeds(self):
        """Test that an impitool command can fail a few times without stopping waiting"""
        self.mock_subprocess_run.side_effect = [MagicMock(returncode=1) for _ in range(self.threshold - 1)] + \
                                               [MagicMock(returncode=0)]
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password,
                                      failure_threshold=self.threshold)
        for _ in range(self.threshold):
            try:
                waiter.member_has_completed(self.members[0])
            except WaitingFailure:
                self.fail('WaitingFailure should not have been raised')

    def test_ipmi_command_repeat_fails(self):
        """Test that we skip future checks on repeatedly failing nodes."""
        self.mock_subprocess_run.return_value.returncode = 1
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password,
                                      failure_threshold=self.threshold)
        with self.assertRaises(WaitingFailure):
            for _ in range(self.threshold):
                waiter.member_has_completed(self.members[0])


class TestDoPowerOffNcns(unittest.TestCase):
    """Tests for the do_power_off_ncns() function"""
    def setUp(self):
        self.mock_get_user_pass = patch('sat.cli.bootsys.mgmt_power.get_username_and_password_interactively').start()
        self.mock_get_user_pass.return_value = ('user', 'pass')

        self.mock_get_ssh_client = patch('sat.cli.bootsys.mgmt_power.get_ssh_client').start()
        self.mock_prompt_continue = patch('sat.cli.bootsys.mgmt_power.prompt_continue').start()
        self.mock_do_mgmt_shutdown_power = patch('sat.cli.bootsys.mgmt_power.do_mgmt_shutdown_power').start()

        self.args = Namespace(disruptive=False, excluded_ncns=set())

    def tearDown(self):
        patch.stopall()

    def test_mgmt_ncns_power_off(self):
        """Test the user is prompted to power off management NCNs."""
        do_power_off_ncns(self.args)
        self.mock_prompt_continue.assert_called_once()
        self.mock_do_mgmt_shutdown_power.assert_called_once()

    def test_mgmt_ncns_skip_prompt_power_off(self):
        """Test that the user prompt to power off management NCNs can be skipped."""
        self.args.disruptive = True
        do_power_off_ncns(self.args)
        self.mock_prompt_continue.assert_not_called()
        self.mock_do_mgmt_shutdown_power.assert_called_once()


class TestDoMgmtShutdownPower(unittest.TestCase):
    """Tests for the do_mgmt_shutdown_power function."""

    def setUp(self):
        """Set up mocks."""
        self.username = 'admin'
        self.password = 'password'

        self.ncn_shutdown_timeout = 1200
        self.ipmi_timeout = 60

        self.mock_get_and_verify_ncn_groups = mock.patch(
            'sat.cli.bootsys.mgmt_power.get_and_verify_ncn_groups').start()
        self.mock_filtered_host_keys = mock.patch(
            'sat.cli.bootsys.mgmt_power.FilteredHostKeys').start()
        self.mock_get_ssh_client = mock.patch(
            'sat.cli.bootsys.mgmt_power.get_ssh_client').start()
        self.mock_set_next_boot_device_to_disk = mock.patch(
            'sat.cli.bootsys.mgmt_power.set_next_boot_device_to_disk').start()
        self.mock_start_shutdown = mock.patch(
            'sat.cli.bootsys.mgmt_power.start_shutdown').start()
        self.mock_finish_shutdown = mock.patch(
            'sat.cli.bootsys.mgmt_power.finish_shutdown').start()
        self.mock_do_ceph_freeze = mock.patch(
            'sat.cli.bootsys.mgmt_power.do_ceph_freeze').start()
        self.mock_do_ceph_unmounts = mock.patch(
            'sat.cli.bootsys.mgmt_power.do_ceph_unmounts').start()
        self.mock_IPMIConsoleLogger = mock.patch(
            'sat.cli.bootsys.mgmt_power.IPMIConsoleLogger').start()
        self.mock_unmount_volumes = patch(
            'sat.cli.bootsys.mgmt_power.unmount_volumes').start()

        self.mock_ssh_client = mock.Mock()
        self.mock_get_ssh_client.return_value = self.mock_ssh_client

        self.mock_other_ncns_by_role = {
            'workers': ['ncn-w001', 'ncn-w002'],
            'managers': ['ncn-m002', 'ncn-m003'],
            'storage': ['ncn-s001', 'ncn-s002']
        }
        self.mock_get_and_verify_ncn_groups.return_value = self.mock_other_ncns_by_role

    def tearDown(self):
        mock.patch.stopall()

    def test_failed_ncn_verification(self):
        """Test do_mgmt_shutdown_power when NCN verification fails."""
        bad_ncn_msg = 'Failed to identify members of the following NCN subrole(s): ...'
        self.mock_get_and_verify_ncn_groups.side_effect = FatalBootsysError(bad_ncn_msg)
        with self.assertRaises(SystemExit):
            with self.assertLogs(level=logging.ERROR) as cm:
                do_mgmt_shutdown_power(self.username, self.password, set(),
                                       self.ncn_shutdown_timeout, self.ipmi_timeout)

        expected_err = f'Not proceeding with NCN power off: {bad_ncn_msg}'
        self.assertEqual(cm.records[0].message, expected_err)

    def test_do_mgmt_shutdown_power_success(self):
        """Test do_mgmt_shutdown_power when all steps are successful."""
        with self.assertLogs(level=logging.INFO) as cm:
            do_mgmt_shutdown_power(self.username, self.password, set(),
                                   self.ncn_shutdown_timeout, self.ipmi_timeout)

        # Assert calls for worker NCNs
        self.mock_unmount_volumes.assert_any_call(self.mock_ssh_client, ['ncn-w001', 'ncn-w002'])
        self.mock_set_next_boot_device_to_disk.assert_any_call(self.mock_ssh_client, ['ncn-w001', 'ncn-w002'])
        self.mock_start_shutdown.assert_any_call(['ncn-w001', 'ncn-w002'], self.mock_ssh_client)
        self.mock_finish_shutdown.assert_any_call(['ncn-w001', 'ncn-w002'], self.username, self.password,
                                                  self.ncn_shutdown_timeout, self.ipmi_timeout)

        # Assert calls for manager NCNs
        self.mock_set_next_boot_device_to_disk.assert_any_call(self.mock_ssh_client, ['ncn-m002', 'ncn-m003'])
        self.mock_start_shutdown.assert_any_call(['ncn-m002', 'ncn-m003'], self.mock_ssh_client)
        self.mock_finish_shutdown.assert_any_call(['ncn-m002', 'ncn-m003'], self.username, self.password,
                                                  self.ncn_shutdown_timeout, self.ipmi_timeout)

        # Assert calls for storage NCNs
        self.mock_set_next_boot_device_to_disk.assert_any_call(self.mock_ssh_client, ['ncn-s001', 'ncn-s002'])
        self.mock_do_ceph_freeze.assert_called_once()
        self.mock_start_shutdown.assert_any_call(['ncn-s001', 'ncn-s002'], self.mock_ssh_client)
        self.mock_finish_shutdown.assert_any_call(['ncn-s001', 'ncn-s002'], self.username, self.password,
                                                  self.ncn_shutdown_timeout, self.ipmi_timeout)

        # Assert call for Ceph unmount on ncn-m001
        self.mock_do_ceph_unmounts.assert_called_once_with(self.mock_ssh_client, 'ncn-m001')

        expected_messages = [
            'Shutting down worker NCNs: ncn-w001, ncn-w002',
            'Waiting up to 1200 seconds for worker NCNs to shut down...',
            'Shutting down manager NCNs: ncn-m002, ncn-m003',
            'Waiting up to 1200 seconds for manager NCNs to shut down...',
            'Freezing Ceph and shutting down storage NCNs: ncn-s001, ncn-s002',
            'Ceph freeze completed successfully on storage NCNs.',
            'Waiting up to 1200 seconds for storage NCNs to shut down...',
            'Shutdown and power off of storage NCNs: ncn-s001, ncn-s002',
            'Shutdown and power off of all management NCNs complete.'
        ]
        self.assertEqual(expected_messages, [record.message for record in cm.records])

    def test_do_mgmt_shutdown_power_with_fatal_error(self):
        """Test do_mgmt_shutdown_power when a fatal error occurs."""
        self.mock_do_ceph_freeze.side_effect = FatalPlatformError('Ceph freeze failed')
        with self.assertLogs(level=logging.ERROR) as cm:
            with self.assertRaises(SystemExit):
                do_mgmt_shutdown_power(self.username, self.password, set(),
                                       self.ncn_shutdown_timeout, self.ipmi_timeout)

        self.mock_get_and_verify_ncn_groups.assert_called_once_with({'ncn-m001'})
        self.assertEqual(cm.records[-1].message, 'Failed to freeze Ceph on storage NCNs: Ceph freeze failed')

    def test_set_next_boot_device_to_disk_success(self):
        """Test that the function sets the boot device to disk successfully"""
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"Boot0001* UEFI OS\nBoot0002* Other OS"

        self.mock_ssh_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

        with self.assertLogs(level=logging.INFO) as cm:
            ncns = ['ncn-w001', 'ncn-s001']
            set_next_boot_device_to_disk(self.mock_ssh_client, ncns)

        expected_connect_calls = [call('ncn-w001'), call('ncn-s001')]
        self.mock_ssh_client.connect.assert_has_calls(expected_connect_calls, any_order=True)

        expected_exec_calls = [
            call('efibootmgr'),
            call('efibootmgr -n 0001'),
            call('efibootmgr'),
            call('efibootmgr -n 0001')
        ]
        self.mock_ssh_client.exec_command.assert_has_calls(expected_exec_calls, any_order=True)

        self.assertEqual(cm.records[0].message, 'Successfully set next boot device to disk (Boot0001) for ncn-w001')
        self.assertEqual(cm.records[1].message, 'Successfully set next boot device to disk (Boot0001) for ncn-s001')

    def test_set_next_boot_device_to_disk_ssh_fail(self):
        """Test that the function handles SSH connection failures and continues"""
        mock_ssh_client = MagicMock()
        mock_stdout = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout.channel.recv_exit_status.return_value = 0
        mock_stdout.read.return_value = b"Boot0001* UEFI OS\nBoot0002* Other OS"

        # Set up the SSH connection side effects to simulate different scenarios
        mock_ssh_client.connect.side_effect = [None, SSHException('ssh failed'), None]
        mock_ssh_client.exec_command.return_value = (None, mock_stdout, mock_stderr)

        with patch('sat.cli.bootsys.mgmt_power.LOGGER') as mock_logger:
            # Test handling of SSH failure and continuation for all NCNs
            ncns = ['ncn-w001', 'ncn-w002', 'ncn-w003']
            set_next_boot_device_to_disk(mock_ssh_client, ncns)

            # Check log messages and method calls
            expected_connect_calls = [call('ncn-w001'), call('ncn-w002'), call('ncn-w003')]
            mock_ssh_client.connect.assert_has_calls(expected_connect_calls)

            expected_exec_calls = [
                call('efibootmgr'),
                call('efibootmgr -n 0001'),
                call('efibootmgr'),
                call('efibootmgr -n 0001')
            ]
            mock_ssh_client.exec_command.assert_has_calls(expected_exec_calls, any_order=True)

            # Verify the log messages for successful and failed connections
            mock_logger.info.assert_any_call('Successfully set next boot device to disk (Boot0001) for ncn-w001')
            mock_logger.warning.assert_called_with('Unable to connect to node ncn-w002: ssh failed')
            mock_logger.info.assert_any_call('Successfully set next boot device to disk (Boot0001) for ncn-w003')

    def test_set_next_boot_device_to_disk_list_command_fails(self):
        """Test that the function handles command execution failures and continues"""
        # Mock successful connection for all NCNs
        self.mock_ssh_client.connect.side_effect = [None, None, None]

        # Mock command execution failure for the first NCN and success for the rest
        mock_stdout_1 = MagicMock()
        mock_stdout_2 = MagicMock()
        mock_stdout_3 = MagicMock()
        mock_stderr = MagicMock()
        mock_stdout_1.channel.recv_exit_status.return_value = 1
        mock_stdout_1.read.return_value = b""
        mock_stdout_2.channel.recv_exit_status.return_value = 0
        mock_stdout_2.read.return_value = b"Boot0001* UEFI OS\nBoot0002* Other OS"
        mock_stdout_3.channel.recv_exit_status.return_value = 0
        mock_stdout_3.read.return_value = b"BootNext: 0001"

        self.mock_ssh_client.exec_command.side_effect = [
            (None, mock_stdout_1, mock_stderr),
            (None, mock_stdout_2, mock_stderr),
            (None, mock_stdout_3, mock_stderr),
            (None, mock_stdout_2, mock_stderr),
            (None, mock_stdout_3, mock_stderr),
        ]

        with patch('sat.cli.bootsys.mgmt_power.LOGGER') as mock_logger:
            ncns = ['ncn-w001', 'ncn-w002', 'ncn-w003']
            set_next_boot_device_to_disk(self.mock_ssh_client, ncns)

            expected_connect_calls = [call('ncn-w001'), call('ncn-w002'), call('ncn-w003')]
            self.mock_ssh_client.connect.assert_has_calls(expected_connect_calls)

            expected_exec_calls = [
                call('efibootmgr'),
                call('efibootmgr'),
                call('efibootmgr -n 0001'),
                call('efibootmgr'),
                call('efibootmgr -n 0001')
            ]
            self.mock_ssh_client.exec_command.assert_has_calls(expected_exec_calls, any_order=True)

            mock_logger.warning.assert_called_with(
                'Unable to determine boot order of ncn-w001, efibootmgr exited with exit code 1')
            mock_logger.info.assert_any_call('Successfully set next boot device to disk (Boot0001) for ncn-w002')
            mock_logger.info.assert_any_call('Successfully set next boot device to disk (Boot0001) for ncn-w003')

    def test_set_next_boot_device_to_disk_set_command_fails(self):
        """Test that the function handles a failure when setting the next boot device for a node"""
        mock_ssh_client = MagicMock()
        mock_stdout_list = MagicMock()
        mock_stdout_set = MagicMock()
        mock_stderr = MagicMock()
        # Simulate successful listing of boot entries
        mock_stdout_list.channel.recv_exit_status.return_value = 0
        mock_stdout_list.read.side_effect = [
            b"Boot0001* UEFI OS\nBoot0002* Other OS",  # Output for ncn-w001
            b"Boot0003* UEFI OS\nBoot0004* Other OS",  # Output for ncn-w002
            b"Boot0005* UEFI OS\nBoot0006* Other OS"  # Output for ncn-w003
        ]
        # Simulate failure when setting the next boot device for ncn-w002
        mock_stdout_set.channel.recv_exit_status.side_effect = [0, 1, 0]
        mock_stdout_set.read.return_value = b"BootNext: 0001"
        mock_ssh_client.exec_command.side_effect = [
            (None, mock_stdout_list, mock_stderr),  # Call to efibootmgr for ncn-w001
            (None, mock_stdout_set, mock_stderr),  # Call to efibootmgr -n 0001 for ncn-w001
            (None, mock_stdout_list, mock_stderr),  # Call to efibootmgr for ncn-w002
            (None, mock_stdout_set, mock_stderr),  # Call to efibootmgr -n 0001 for ncn-w002
            (None, mock_stdout_list, mock_stderr),  # Call to efibootmgr for ncn-w003
            (None, mock_stdout_set, mock_stderr)  # Call to efibootmgr -n 0001 for ncn-w003
        ]
        with patch('sat.cli.bootsys.mgmt_power.LOGGER') as mock_logger:
            ncns = ['ncn-w001', 'ncn-w002', 'ncn-w003']
            set_next_boot_device_to_disk(mock_ssh_client, ncns)
            expected_exec_calls = [
                call('efibootmgr'),
                call('efibootmgr -n 0001'),
                call('efibootmgr'),
                call('efibootmgr -n 0003'),
                call('efibootmgr'),
                call('efibootmgr -n 0005')
            ]
            mock_ssh_client.exec_command.assert_has_calls(expected_exec_calls)
            mock_logger.info.assert_any_call('Successfully set next boot device to disk (Boot0001) for ncn-w001')
            mock_logger.warning.assert_called_with(
                'Failed to set next boot device for ncn-w002, efibootmgr -n 0003 exited with exit code 1'
            )
            mock_logger.info.assert_any_call('Successfully set next boot device to disk (Boot0005) for ncn-w003')
