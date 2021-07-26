"""
Tests for the sat.cli.bootsys.mgmt_power module.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
import unittest
from unittest.mock import patch

from paramiko.ssh_exception import SSHException, NoValidConnectionsError

from sat.cli.bootsys.mgmt_power import SSHAvailableWaiter, IPMIPowerStateWaiter


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

    def test_ipmi_command_fails(self):
        """Test that we skip future checks on failing nodes."""
        self.mock_subprocess_run.return_value.returncode = 1
        waiter = IPMIPowerStateWaiter(self.members, 'on', self.timeout, self.username, self.password)
        self.assertFalse(waiter.member_has_completed(self.members[0]))
