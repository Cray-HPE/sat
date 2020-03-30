"""
The parser for the k8s subcommand.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.
"""

import sat.parsergroups


def add_k8s_subparser(subparsers):
    """Add the k8s subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.
    """
    format_opts = sat.parsergroups.create_format_options()
    filter_opts = sat.parsergroups.create_filter_options()

    k8s_parser = subparsers.add_parser(
        'k8s',
        help='Report on the status of Kubernetes.',
        description=(
            'The principal function is to report on any pods within a '
            'replicaset that are co-located on the same node.'),
        parents=[format_opts, filter_opts])

    k8s_parser.add_argument(
        '--co-located-replicas',
        help='Display any pods within a replicaset that are co-located on the '
             'same node, which may reduce resiliency in the event that the '
             'node fails.',
        default=None, action='store_true')
