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
    return sorted(all_groups - excluded)


def wait_for_nodes_powerstate(nodes, state, timeout):
    """Wait for nodes to reach the given power state.

    If not all nodes in the given state after `timeout` seconds, then
    a set is returned containing the nodes that did not reach the
    given state.

    Args:
        nodes ([(hostname, Command)]): a list of 2-tuples with
            the hostname in the first position and a corresponding
            pyghmi.ipmi.Command object.
        state (str): a power state (either 'on' or 'off')
        timeout (int): a timeout, in seconds, for the given nodes
            to reach the desired state.

    Return:
        a set of nodes that haven't reached the given state (if
        successful, this is the empty set.)

    """
    start_time = time.monotonic()
    completed_nodes = set()

    while True:
        remaining_nodes = set()
        for node, cmd in nodes:
            if node in completed_nodes:
                continue

            if cmd.get_power()['powerstate'] == state:
                completed_nodes.add(node)
            else:
                remaining_nodes.add(node)

        LOGGER.debug('Remaining polled nodes: %s', remaining_nodes)

        if not remaining_nodes:
            return remaining_nodes

        elif time.monotonic() - start_time > timeout:
            LOGGER.error("Reaching power state '%s' on nodes timed out after %d seconds: %s",
                         state, timeout, ", ".join(remaining_nodes))
            return remaining_nodes

        else:
            time.sleep(1)
