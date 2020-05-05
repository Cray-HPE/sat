"""
The main entry point for the k8s subcommand.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.
"""

import logging
import sys
from collections import defaultdict, namedtuple

import kubernetes.client
import kubernetes.config
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException

from sat.config import get_config_value
from sat.report import Report


LOGGER = logging.getLogger(__name__)

ReplicaSet = namedtuple('ReplicaSet', ['namespace', 'name'])

def get_co_located_replicas():
    """Get pods within a replicaset that are running on the same node.

    Returns:
        A dict formatted like...
            {
                replicaset1: {
                    node1: [pod1, pod2],
                    node2: [pod3, pod4],
                },
                replicaset2: {
                    node1: [pod1, pod2]
                },
                ...
            }

        replicaset represents a ReplicaSet namedtuple, node represents
        the name of a node, and pod represents the name of a pod.

    Raises:
        kubernetes.client.rest.ApiException if the call failed.
        kubernetes.config.config_exception.ConfigException if there was trouble
            reading the config.
    """
    try:
        kubernetes.config.load_kube_config()
    except ConfigException as err:
        raise ConfigException('Reading kubernetes config: {}'.format(err))

    appsv1 = kubernetes.client.AppsV1Api()
    corev1 = kubernetes.client.CoreV1Api()

    try:
        replica_sets = appsv1.list_replica_set_for_all_namespaces().items
    except ApiException as err:
        raise ApiException('Could not retrieve list of replicasets: {}'.format(err))

    replica_counts = {}
    for replica_set in replica_sets:
        try:
            hash_ = replica_set.metadata.labels['pod-template-hash']
        except KeyError:
            LOGGER.warning(
                'Replicaset {} had no "pod-template-hash" field.'.format(
                    replica_set.metadata.name))
            continue

        ns = replica_set.metadata.namespace

        try:
            label = 'pod-template-hash={}'.format(hash_)
            pods = corev1.list_namespaced_pod(ns, label_selector=label).items
        except ApiException as err:
            LOGGER.warning(
                'Could not retrieve pods in namespace {} with label selector '
                '{}: {}'.format(ns, label, err))
            continue

        # count how many times a pod of a given replicaset is running
        # on the same node.
        node_pods = defaultdict(lambda: [])
        for pod in pods:
            if pod.status.phase == 'Running':
                node = pod.spec.node_name
                node_pods[node].append(pod.metadata.name)

        # Don't save entries that are of len 1.
        entry = {k: v for k, v in node_pods.items() if len(v) > 1}

        if entry:
            r = ReplicaSet(ns, replica_set.metadata.name)
            replica_counts[r] = entry

    return replica_counts


def create_report(dupes, args):
    """Create a report object from the output of get_co_located_replicas.

    Args:
        dupes: The return from get_co_located_replicas.

    Returns:
        A Report object.
    """
    headers = ['namespace', 'replicaset', 'node', 'pods']
    rows = [[r.namespace, r.name, n, '\n'.join(p)] for r, nodes in dupes.items() for n, p in nodes.items()]

    report = Report(
        headers, None,
        args.sort_by, args.reverse,
        get_config_value('format.no_headings'),
        get_config_value('format.no_borders'),
        filter_strs=args.filter_strs)

    report.add_rows(rows)
    return report


def do_k8s(args):
    """Run the k8s command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """
    LOGGER.debug('do_k8s received the following args: %s', args)

    try:
        dupes = get_co_located_replicas()
    except (ApiException, ConfigException) as err:
        LOGGER.error(err)
        sys.exit(1)

    if not args.co_located_replicas:
        print('Summary: There were {} replica-sets that had pods running on '
              'the same node.'.format(len(dupes)))
    else:
        report = create_report(dupes, args)
        if args.format == 'yaml':
            print(report.get_yaml())
        else:
            print(report)
