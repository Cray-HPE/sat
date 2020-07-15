"""
Generic common utilities for the bootsys subcommand.

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

from collections import defaultdict
import logging
import re
import shlex
import subprocess
import time

LOGGER = logging.getLogger(__name__)


class RunningService:
    def __init__(self, service, dry_run=True):
        self._service = service
        self._dry_run = dry_run

    def _systemctl_start_stop(self, state):
        """Start or stop the given service.

        Args:
            state (bool): If True, start the service. If False, stop it.

        Returns:
            None.
        """
        cmd = 'systemctl {} {}'.format('start' if state else 'stop',
                                       self._service)
        LOGGER.info('Running `%s`', cmd)
        if not self._dry_run:
            subprocess.check_call(shlex.split(cmd))

    def __enter__(self):
        self._systemctl_start_stop(True)
        # TODO: Make sleep time a constructor arg
        LOGGER.info("Sleeping for 5 seconds after starting service %s", self._service)
        time.sleep(5)

    def __exit__(self, exc_type, exc_value, exc_traceback):
        self._systemctl_start_stop(False)


def get_groups(groups):
    """Get a set of hosts in a given group.

    Args:
        groups ([str]): a list of groups to retrieve hosts from.

    Returns: a set of all hosts in the given groups.
    """
    if not groups:
        return set()

    host_regex = re.compile(r'\s+\"([\w-]+)\",?$')

    spec = '+'.join(['groups["{}"]'.format(g) for g in groups])
    cmd = 'ansible localhost -m debug -a \'var={}\''.format(spec)
    pc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE, encoding='utf-8')

    group = set()

    for line in pc.stdout.splitlines():
        m = host_regex.match(line)
        if m:
            group.add(m.group(1))

    return group


def get_ncns(groups, exclude=None):
    """Get a set of nodes from the specified groups.

    Args:
        groups ([str]): groups to get nodes from.
        exclude ([str]): groups which should be excluded.

    Returns:
        iterator containing all nodes from groups minus the
        ones from exclude in alphabetical order.
    """
    all_groups = get_groups(groups)
    excluded = get_groups(exclude or [])
    return all_groups - excluded


def k8s_pods_to_status_dict(v1_pod_list):
    """Helper function to convert a V1PodList to a dict.

    It is used for recording the pod phase for every pod in the system.

    The dict has the following schema:
    {
        namespace (str): {
            name_in_namespace (str): pod_phase (str)
        }
    }

    Args:
        v1_pod_list: a V1PodList object from the kubernetes library

    Returns:
        a dict in the above form.

    """
    pods_dict = defaultdict(dict)
    for pod in v1_pod_list.items:
        pods_dict[pod.metadata.namespace][pod.metadata.name] = pod.status.phase

    return pods_dict
