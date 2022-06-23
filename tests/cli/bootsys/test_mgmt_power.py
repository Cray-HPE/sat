#
# MIT License
#
# (C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
from argparse import Namespace
import unittest
from unittest.mock import MagicMock, patch

from paramiko.ssh_exception import SSHException, NoValidConnectionsError

from sat.cli.bootsys.mgmt_power import (
    do_power_off_ncns,
    SSHAvailableWaiter,
    IPMIPowerStateWaiter,
)
from sat.waiting import WaitingFailure


class TestSSHAvailableWaiter(unittest.TestCase):
    """Tests for the sat.cli.bootsys.mgmt_power.SSHAvailableWaiter class"""
    def setUp(self):
        self.mock_get_ssh_client = patch('sat.cli.bootsys.mgmt_power.get_ssh_client').start()
        self.mock_ssh_client = self.mock_get_ssh_client.return_value
        self.members = ['ncn-w002', 'ncn-s001']
        self.timeout = 1

    def tearDown(self):
        patch.stopall()

    def test_pre_wait_action_loads_keys(self):
        """Test the SSH waiter loads system host keys through get_ssh_client."""
        SSHAvailableWaiter(self.members, self.timeout).pre_wait_action()
        self.mock_get_ssh_client.assert_called_once_with()

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
