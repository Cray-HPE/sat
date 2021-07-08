"""
The main entry point for the k8s subcommand.

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
import sys
from collections import defaultdict

from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException

from sat.config import get_config_value
from sat.report import Report
from sat.cli.k8s.replicaset import ReplicaSet


LOGGER = logging.getLogger(__name__)


def get_co_located_replicas():
    """Get each replicaset that had pods sharing nodes.

    Returns:
        A list of replicasets that had multiple pods running on the
        same nodes.

    Raises:
        kubernetes.client.rest.ApiException if the call failed.
        kubernetes.config.config_exception.ConfigException if there was trouble
            reading the config.
    """
    # This call can raise
    replica_sets = ReplicaSet.get_all_replica_sets()

    return [x for x in replica_sets if x.co_located_replicas]


def create_report(dupes, args):
    """Create a report object from the output of get_co_located_replicas.

    Args:
        dupes: The return from get_co_located_replicas.

    Returns:
        A Report object.
    """
    headers = ['namespace', 'replicaset', 'node', 'ratio', 'pods']
    rows = [
            [
                r.metadata.namespace,
                r.metadata.name,
                n,
                '{}/{}'.format(len(p), len(r.running_pods)),
                '\n'.join(p),
            ] for r in dupes for n, p in r.co_located_replicas.items()]

    return headers, rows


def do_k8s(args):
    """Run the k8s command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """
    LOGGER.debug('do_k8s received the following args: %s', args)

    try:
        dupes = get_co_located_replicas()
    except (ApiException, ConfigException, FileNotFoundError) as err:
        LOGGER.error(err)
        sys.exit(1)

    if not args.co_located_replicas:
        print('Summary: There were {} replica-sets that had pods running on '
              'the same node.'.format(len(dupes)))
    else:
        headers, rows = create_report(dupes, args)

        report = Report(
            headers, None,
            args.sort_by, args.reverse,
            get_config_value('format.no_headings'),
            get_config_value('format.no_borders'),
            filter_strs=args.filter_strs,
            display_headings=args.fields)

        report.add_rows(rows)

        if args.format == 'yaml':
            print(report.get_yaml())
        elif args.format == 'json':
            print(report.get_json())
        else:
            print(report)
