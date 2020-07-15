"""
Tests for common bootsys code.

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
import unittest
from unittest.mock import MagicMock, patch

from paramiko.ssh_exception import SSHException, NoValidConnectionsError
from sat.cli.bootsys.power import IPMIPowerStateWaiter
from sat.cli.bootsys.mgmt_boot_power import SSHAvailableWaiter, KubernetesPodStatusWaiter

class WaiterTestCase(unittest.TestCase):
    def setUp(self):
        self.mock_time_monotonic = patch('sat.cli.bootsys.waiting.time.monotonic').start()
        self.mock_time_sleep = patch('sat.cli.bootsys.waiting.time.sleep').start()

        self.members = ['groucho', 'chico', 'harpo', 'zeppo']
        self.timeout = 10
        self.username = 'user'
        self.password = 'pass'

    def tearDown(self):
        patch.stopall()


class TestIPMIPowerStateWaiter(WaiterTestCase):
    def setUp(self):
        self.mock_subprocess_run = patch('sat.cli.bootsys.power.subprocess.run').start()
        self.mock_subprocess_run.return_value.stdout = 'Chassis power is on'
        self.mock_subprocess_run.return_value.returncode = 0

        super().setUp()

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
        self.assertTrue(waiter.member_has_completed('groucho'))


class TestSSHAvailableWaiter(WaiterTestCase):
    """Tests for the sat.cli.bootsys.mgmt_boot_power.SSHAvailableWaiter class"""
    def setUp(self):
        self.mock_ssh_client = patch('sat.cli.bootsys.mgmt_boot_power.SSHClient').start()

        super().setUp()

    def test_pre_wait_action_loads_keys(self):
        """Test the SSH waiter loads system host keys"""
        SSHAvailableWaiter(self.members, self.timeout).pre_wait_action()
        self.mock_ssh_client.return_value.load_system_host_keys.assert_called_once()

    def test_ssh_available(self):
        """Test the SSH waiter detects available nodes"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.assertTrue(waiter.member_has_completed('groucho'))

    def test_ssh_not_available(self):
        """Test the SSH waiter detects node isn't available due to SSHException"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.mock_ssh_client.return_value.connect.side_effect = SSHException("SSH doesn't work")
        self.assertFalse(waiter.member_has_completed('groucho'))

    def test_ssh_not_available_no_valid_connection(self):
        """Test the SSH waiter detects node isn't available due to no valid connection"""
        waiter = SSHAvailableWaiter(self.members, self.timeout)
        self.mock_ssh_client.return_value.connect.side_effect = NoValidConnectionsError({('127.0.0.1', '22'): 'Something happened'})
        self.assertFalse(waiter.member_has_completed('groucho'))


def generate_mock_pod(namespace, name, phase):
    """Generate a simple mock V1Pod object."""
    pod = MagicMock()
    pod.metadata.namespace = namespace
    pod.metadata.name = name
    pod.status.phase = phase
    return pod


class TestK8sPodWaiter(WaiterTestCase):
    def setUp(self):
        self.mock_k8s_api = patch('sat.cli.bootsys.mgmt_boot_power.CoreV1Api').start()
        self.mock_load_kube_config = patch('sat.cli.bootsys.mgmt_boot_power.load_kube_config').start()

        self.mocked_pod_dump = {
            'galaxies': {
                'm83': 'Succeeded',
                'milky_way': 'Pending'
            },
            'planets': {
                'jupiter': 'Succeeded',
                'earth': 'Failed'
            }
        }

        patch('builtins.open').start()
        patch('sat.cli.bootsys.mgmt_boot_power.json.load', return_value=self.mocked_pod_dump).start()

        super().setUp()

    def test_k8s_pod_waiter_completed(self):
        """Test if a k8s pod is considered completed if it is in its previous state"""
        self.mock_k8s_api.return_value.list_pod_for_all_namespaces.return_value.items = [
            generate_mock_pod('galaxies', 'm83', 'Succeeded')
        ]

        waiter = KubernetesPodStatusWaiter(self.timeout)
        self.assertTrue(waiter.member_has_completed(('galaxies', 'm83')))

    def test_k8s_pod_waiter_not_completed(self):
        """Test if a pod in different state from last shutdown is considered not completed"""
        self.mock_k8s_api.return_value.list_pod_for_all_namespaces.return_value.items = [
            generate_mock_pod('galaxies', 'm83', 'Pending')
        ]

        waiter = KubernetesPodStatusWaiter(self.timeout)
        self.assertFalse(waiter.member_has_completed(('galaxies', 'm83')))


    def test_k8s_pod_waiter_new_pod(self):
        """Test if a new pod is considered completed if it succeeded."""
        self.mock_k8s_api.return_value.list_pod_for_all_namespaces.return_value.items = [
            generate_mock_pod('galaxies', 'andromeda', 'Pending')
        ]

        waiter = KubernetesPodStatusWaiter(self.timeout)
        self.assertFalse(waiter.member_has_completed(('galaxies', 'andromeda')))
