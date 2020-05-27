"""
Unit tests for sat.cli.k8s logic.

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
from argparse import Namespace
from unittest import mock

import kubernetes
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException

from sat.cli.k8s.replicaset import ReplicaSet


class FakeReplicaSet(kubernetes.client.models.v1_replica_set.V1ReplicaSet):
    def __init__(self, name, namespace, hash_):
        self.metadata = Namespace()
        self.metadata.name = name
        self.metadata.namespace = namespace
        self.metadata.labels = {'pod-template-hash': hash_}


class FakeReplicaSets:
    """Mocks the return from list_replica_set_for_all_namespaces.
    """
    def __init__(self):
        self.items = [
            FakeReplicaSet('replica-set1', 'namespace', 'dupes-hash'),
        ]


class FakePod:
    def __init__(self, name, node_name, status):
        self.metadata = Namespace()
        self.metadata.name = name

        self.spec = Namespace()
        self.spec.node_name = node_name

        self.status = Namespace()
        self.status.phase = status

    def __str__(self):
        print(self.metadata.name, self.spec.node_name)


class FakePods:
    def __init__(self):
        self.items = [
            FakePod('replica1-dupes-hash-1', 'w001', 'Running'),
            FakePod('replica1-dupes-hash-2', 'w001', 'Running'),
            FakePod('replica1-dupes-hash-3', 'w002', 'Running'),
            FakePod('replica1-dupes-hash-4', 'w001', 'Terminated'),
            FakePod('replica1-other-hash-1', 'w001', 'Terminated'),
        ]


class TestReplicaset(unittest.TestCase):
    """Test cases for functions in sat k8s.
    """
    def tearDown(self):
        mock.patch.stopall()

    def test_get_all_replica_sets_config_exception(self):
        """It should re-raise the same exception as load_kube_config.
        """
        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.config.load_kube_config',
            side_effect=ConfigException).start()

        with self.assertRaises(ConfigException):
            rs = ReplicaSet().get_all_replica_sets()

    def test_get_all_replica_sets_config_exception(self):
        """It should re-raise a ConfigException by load_kube_config.
        """
        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.config.load_kube_config',
            side_effect=ConfigException).start()

        with self.assertRaises(ConfigException):
            rs = ReplicaSet().get_all_replica_sets()

    def test_get_all_replica_sets_file_not_found_exception(self):
        """It should re-raise a FileNotFoundError by load_kube_config.

        kubernetes.config.kube_config.open can raise FileNotFoundError.

        TODO: Update this test as part of either SAT-468 or SAT-460.
        """
        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.config.load_kube_config',
            side_effect=FileNotFoundError).start()

        with self.assertRaises(FileNotFoundError):
            rs = ReplicaSet().get_all_replica_sets()

    def test_pods(self):
        """The pods property should return all pods with matching hash.
        """
        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.client.AppsV1Api.list_replica_set_for_all_namespaces',
            return_value=FakeReplicaSets()).start()

        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.client.CoreV1Api.list_namespaced_pod',
            return_value=FakePods()).start()

        expected = FakePods().items
        actual = ReplicaSet.get_all_replica_sets()[0].pods[0:4]

        for e, a in zip(expected, actual):
            self.assertEqual(e.metadata.name, a.metadata.name)

    def test_running_pods(self):
        """It should return all pods with status of "Running".
        """
        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.client.AppsV1Api.list_replica_set_for_all_namespaces',
            return_value=FakeReplicaSets()).start()

        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.client.CoreV1Api.list_namespaced_pod',
            return_value=FakePods()).start()

        expected = FakePods().items[0:3]
        actual = ReplicaSet.get_all_replica_sets()[0].running_pods

        for e, a in zip(expected, actual):
            self.assertEqual(e.metadata.name, a.metadata.name)

    def test_co_located_replicas(self):
        """Positive test-case for co_located_replicas.

        Replicas 'Running' on the same node should be returned.
        """
        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.client.AppsV1Api.list_replica_set_for_all_namespaces',
            return_value=FakeReplicaSets()).start()

        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.client.CoreV1Api.list_namespaced_pod',
            return_value=FakePods()).start()

        expected = FakePods().items[0:2]
        actual = ReplicaSet.get_all_replica_sets()[0].co_located_replicas

        self.assertIn('w001', actual)

        self.assertEqual(2, len(actual['w001']))
        for e, a in zip(expected, actual['w001']):
            self.assertEqual(e.metadata.name, a)

    def test_get_all_replica_sets_api_exception(self):
        """It should re-raise an ApiException.

        ApiException can be raised by the call to
        'list_replica_set_for_all_namespaces'.
        """
        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.k8s.replicaset.kubernetes.client.AppsV1Api.list_replica_set_for_all_namespaces',
            side_effect=ApiException).start()

        with self.assertRaises(ApiException):
            rs = ReplicaSet().get_all_replica_sets()


if __name__ == '__main__':
    unittest.main()
