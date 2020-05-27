"""
ReplicaSet class

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

import logging
from collections import defaultdict

import kubernetes.client
import kubernetes.config
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException

from sat.cached_property import cached_property


LOGGER = logging.getLogger(__name__)


class ReplicaSet(kubernetes.client.models.v1_replica_set.V1ReplicaSet):

    @cached_property
    def pods(self):
        """Get all pods owned by this replicaset.

        Returns:
            All pods associated with this ReplicaSet in a list.

        Raises:
            ApiException: If the call to get all pods failed.
        """
        try:
            hash_ = self.metadata.labels['pod-template-hash']
        except KeyError:
            LOGGER.warning(
                'Replicaset {} had no "pod-template-hash" field.'.format(
                    self.metadata.name))
            return []

        ns = self.metadata.namespace

        label = 'pod-template-hash={}'.format(hash_)
        try:
            corev1 = kubernetes.client.CoreV1Api()
            return corev1.list_namespaced_pod(ns, label_selector=label).items
        except ApiException as err:
            LOGGER.warning(
                'Could not retrieve pods in namespace {} with label selector '
                '{}: {}'.format(ns, label, err))
            return []

    @cached_property
    def running_pods(self):
        """Return all pods with a status of 'Running'.

        Returns:
            All pods with a status of 'Running' as a list.
        """
        return [x for x in self.pods if x.status.phase == 'Running']

    @cached_property
    def co_located_replicas(self):
        """Get pods within a replicaset that are running on the same node.

        Returns:
            A list of replicasets that had multiple pods running on the
            same nodes. Keys are the name of the node, values are
            the names of the pods.
        """
        # count how many times a pod of a given replicaset is running
        # on the same node.
        node_pods = defaultdict(lambda: [])

        for pod in self.running_pods:
            node = pod.spec.node_name
            node_pods[node].append(pod.metadata.name)

        # Don't save entries that are of len 1.
        entry = {k: v for k, v in node_pods.items() if len(v) > 1}

        return entry

    @classmethod
    def get_all_replica_sets(cls):
        """Returns a list of all available replica sets.

        This method also maps each replica set to Pod objects returned by
        the Kubernetes API.

        Returns:
            A list of replica sets.

        Raises:
            ApiException: An error occured while retrieving data.
            ConfigException: An error occured while reading the K8s config.
            FileNotFoundError: The config didn't exist.
        """
        try:
            kubernetes.config.load_kube_config()
        except ConfigException as err:
            raise ConfigException('Error reading kubernetes config: {}'.format(err))

        appsv1 = kubernetes.client.AppsV1Api()

        try:
            replica_sets = appsv1.list_replica_set_for_all_namespaces().items
        except ApiException as err:
            raise ApiException('Could not retrieve list of replicasets: {}'.format(err))
        except FileNotFoundError as err:
            raise FileNotFoundError('Could not retrieve list of replicasets: {}'.format(err))

        for rs in replica_sets:
            rs.__class__ = ReplicaSet

        return replica_sets
