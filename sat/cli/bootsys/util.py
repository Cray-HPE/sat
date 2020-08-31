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
    def __init__(self, service, dry_run=True, sleep_after_start=0):
        """
        Create a new context manager that starts a service in a context and
        stops it when leaving the context.

        Note that if a service was already running, it will be stopped after
        the context is exited. It does not leave the service in the state it
        was in before entering the context.

        Args:
            service (str): name of the service to start/stop
            dry_run (bool): if True, do not really start and stop the service.
            sleep_after_start (int): number of seconds to sleep after starting
                the service when entering the context.
        """
        self._service = service
        self._dry_run = dry_run
        self._sleep_after_start = sleep_after_start

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

        if self._sleep_after_start:
            LOGGER.info("Sleeping for %s seconds after starting service %s.",
                        self._sleep_after_start, self._service)
            time.sleep(self._sleep_after_start)

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
        a defaultdict in the above form

    """
    pods_dict = defaultdict(dict)
    for pod in v1_pod_list.items:
        pods_dict[pod.metadata.namespace][pod.metadata.name] = pod.status.phase

    return pods_dict


def run_ansible_playbook(playbook_file, opts='', exit_on_err=True):
    """Run the given ansible playbook. Log stderr, and optionally exit on failure

    Args:
        playbook_file (str): The path to the playbook file to run.
        opts (str): Additional options to use with ansible-playbook as a string.
        exit_on_err (bool): If True, exit on error. If False, just log the error.

    Raises:
        SystemExit if the ansible playbook fails and `exit_on_err` is True.

    Returns:
        The output of the ansible playbook or None if it fails and `exit_on_err`
        is False.
    """
    cmd = f'ansible-playbook {opts + " " if opts else ""}{playbook_file}'
    LOGGER.debug('Invoking Ansible: %s', cmd)

    try:
        proc = subprocess.run(shlex.split(cmd), stdout=subprocess.PIPE,
                              stderr=subprocess.PIPE, encoding='utf-8')
    except OSError as err:
        LOGGER.error("Failed to invoke '%s': %s", cmd, err)
        if exit_on_err:
            raise SystemExit(1)
        else:
            return

    if proc.returncode:
        LOGGER.error("Command '%s' failed. stderr: %s", cmd, proc.stderr)
        if exit_on_err:
            raise SystemExit(1)
        else:
            return
    else:
        LOGGER.info('Ansible playbook %s completed successfully.', playbook_file)
        return proc.stdout
