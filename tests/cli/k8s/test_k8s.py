"""
Unit tests for sat.cli.k8s logic.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.
"""

import unittest
from argparse import Namespace
from unittest import mock

from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException

import sat.cli.k8s.main
from sat.cli.k8s.main import ReplicaSet


class FakeReplicaSet:
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
    def __init__(self, name, node_name):
        self.metadata = Namespace()
        self.metadata.name = name

        self.spec = Namespace()
        self.spec.node_name = node_name

        self.status = Namespace()
        self.status.phase = 'Running'

    def __str__(self):
        print(self.metadata.name, self.spec.node_name)


class FakePods:
    def __init__(self):
        self.items = [
            FakePod('replica1-dupes-hash-1', 'w001'),
            FakePod('replica1-dupes-hash-2', 'w001'),
            FakePod('replica1-dupes-hash-3', 'w001'),
        ]


class TestK8s(unittest.TestCase):
    """Test cases for functions in sat k8s.
    """
    def tearDown(self):
        mock.patch.stopall()

    def test_get_co_located_replicas(self):
        """Positive test case for get_co_located_replicas.
        """
        mock.patch(
            'sat.cli.k8s.main.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.k8s.main.kubernetes.client.AppsV1Api.list_replica_set_for_all_namespaces',
            return_value=FakeReplicaSets()).start()

        mock.patch(
            'sat.cli.k8s.main.kubernetes.client.CoreV1Api.list_namespaced_pod',
            return_value=FakePods()).start()

        replicas = sat.cli.k8s.main.get_co_located_replicas()

        expected = ReplicaSet('namespace', 'replica-set1')
        self.assertIn(expected, replicas)
        self.assertEqual(3, len(replicas[expected]['w001']))

        fake_pods = FakePods()
        for e, a in zip(fake_pods.items, replicas[expected]['w001']):
            self.assertEqual(e.metadata.name, a)

    def test_get_co_located_replicas_api_exception_config(self):
        """It should re-raise the same exception as load_kube_config.
        """
        mock.patch(
            'sat.cli.k8s.main.kubernetes.config.load_kube_config',
            side_effect=ConfigException).start()

        with self.assertRaises(ConfigException):
            sat.cli.k8s.main.get_co_located_replicas()

    def test_get_co_located_replicas_api_exception_list_replicas(self):
        """get_co_located_replicas should re-raise an ApiException.

        ApiException can be raised by the call to
        'list_replica_set_for_all_namespaces'.
        """
        mock.patch(
            'sat.cli.k8s.main.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.k8s.main.kubernetes.client.AppsV1Api.list_replica_set_for_all_namespaces',
            side_effect=ApiException).start()

        with self.assertRaises(ApiException):
            sat.cli.k8s.main.get_co_located_replicas()


if __name__ == '__main__':
    unittest.main()
