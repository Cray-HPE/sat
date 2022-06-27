#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
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
The parser for the k8s subcommand.
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
