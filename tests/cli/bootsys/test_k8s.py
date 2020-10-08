"""
Unit tests for the sat.cli.bootsys.k8s module.

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

from sat.cli.bootsys.k8s import KubernetesPodStatusWaiter


def generate_mock_pod(namespace, name, phase):
    """Generate a simple mock V1Pod object."""
    pod = MagicMock()
    pod.metadata.namespace = namespace
    pod.metadata.name = name
    pod.status.phase = phase
    return pod


class TestK8sPodWaiter(unittest.TestCase):
    def setUp(self):
        self.mock_k8s_api = patch('sat.cli.bootsys.k8s.CoreV1Api').start()
        self.mock_load_kube_config = patch('sat.cli.bootsys.k8s.load_kube_config').start()

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

        mock_recorder = patch('sat.cli.bootsys.k8s.PodStateRecorder').start()
        mock_recorder.get_state_data.return_value = self.mocked_pod_dump
        self.timeout = 1

    def tearDown(self):
        patch.stopall()

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
