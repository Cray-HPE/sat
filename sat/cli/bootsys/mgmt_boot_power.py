"""
Management cluster boot up procedure.

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

import json
import logging
import socket
import subprocess
import urllib3
import warnings

from kubernetes.client import CoreV1Api
from kubernetes.config import load_kube_config
from kubernetes.config.config_exception import ConfigException
from paramiko.client import SSHClient
from paramiko.ssh_exception import SSHException
from yaml import YAMLLoadWarning

from sat.cli.bootsys.defaults import DEFAULT_PODSTATE_FILE
from sat.cli.bootsys.power import IPMIPowerStateWaiter
from sat.cli.bootsys.util import get_ncns, RunningService, k8s_pods_to_status_dict
from sat.cli.bootsys.waiting import GroupWaiter, Waiter
from sat.report import Report
from sat.util import get_username_and_password_interactively

LOGGER = logging.getLogger(__name__)


def load_kube_api():
    """Get a Kubernetes CoreV1Api object.

    This helper function loads the kube config and then instantiates
    an API object.

    Returns:
        CoreV1Api: the API object from the kubernetes library.

    Raises:
        kubernetes.config.config_exception.ConfigException: if failed to load
            kubernetes configuration.
    """
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=YAMLLoadWarning)
            load_kube_config()
    # Earlier versions: FileNotFoundError; later versions: ConfigException
    except (FileNotFoundError, ConfigException) as err:
        raise ConfigException(
            'Failed to load kubernetes config to get pod status: '
            '{}'.format(err)
        )

    return CoreV1Api()


class SSHAvailableWaiter(GroupWaiter):
    """A waiter which waits for all member nodes to be accessible via SSH.
    """

    def __init__(self, members, timeout, poll_interval=1):
        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()

        super().__init__(members, timeout, poll_interval=poll_interval)

    def condition_name(self):
        return 'Hosts accessible via SSH'

    def member_has_completed(self, member):
        """Check if a node is accessible by SSH.

        Args:
            member (str): a hostname to check

        Returns:
            True if SSH connecting succeeded, and
                False otherwise.
        """
        try:
            self.ssh_client.connect(member)
        except (SSHException, socket.error):
            return False
        else:
            return True


class KubernetesAPIAvailableWaiter(Waiter):
    """A waiter which waits for the Kubernetes API to become available.

    Polls the Kubernetes API endpoint until no network errors get
    thrown, at which point the API is considered to be "up".
    """
    def __init__(self, timeout, poll_interval=1):
        """See superclass documentation.

        Raises:
            kubernetes.config.config_exception.ConfigException: if failed to load
                kubernetes configuration.
        """
        super().__init__(timeout, poll_interval=poll_interval)

        self.k8s_api = load_kube_api()

    def condition_name(self):
        return 'Kubernetes API available'

    def has_completed(self):
        """Return True if the /apis endpoint can be queried successfully and
        False otherwise.
        """
        try:
            self.k8s_api.get_api_resources()
        except urllib3.exceptions.MaxRetryError:
            return False
        else:
            return True


class CephHealthWaiter(Waiter):
    """Waiter for the Ceph cluster health status."""

    def __init__(self, timeout, poll_interval=1):
        self.host = 'ncn-m001'

        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(self.host)

        super().__init__(timeout, poll_interval=poll_interval)

    def condition_name(self):
        return "Ceph cluster in healthy state"

    def has_completed(self):
        try:
            ceph_command = 'ceph -s --format=json'
            _, stdout, _ = self.ssh_client.exec_command(ceph_command)

        except SSHException:
            LOGGER.error('Failed to execute command "%s" on host "%s".', ceph_command, self.host)
            return False

        try:
            rsp_dict = json.load(stdout)

        except json.decoder.JSONDecodeError as jde:
            LOGGER.error('Received malformed response from Ceph: %s', jde)
            return False

        try:
            # TODO: If the Ceph health criteria are updated, this will
            # need to be changes. (See SAT-559 for further
            # information.)
            return rsp_dict['health']['status'] == 'HEALTH_OK'

        except KeyError:
            LOGGER.error('Ceph JSON response is well-formed, but has an unexpected schema.')

            if 'health' not in rsp_dict:
                LOGGER.error('Missing top-level "health" key in Ceph JSON response.')
            elif 'status' not in rsp_dict['health']:
                LOGGER.error('Missing "status" key under "health" key in Ceph JSON response.')

            return False


class KubernetesPodStatusWaiter(GroupWaiter):
    """A waiter which waits for pods to reach expected state.

    This waits for all pods to be in the same state they were in before the
    previous shutdown and for any new pods to be in the 'Running' or 'Complete'
    state.
    """

    def __init__(self, timeout, poll_interval=10,
                 podstate_path=DEFAULT_PODSTATE_FILE):
        """Initialize the Kubernetes waiter.

        See GroupWaiter documentation.

        Args:
            podstate_path (str): a path to the file containing the
                state of the pods from the previous shutdown.
        """

        super().__init__(set(), timeout, poll_interval=poll_interval)

        # Load k8s configuration before trying to use API
        self.k8s_api = load_kube_api()

        with open(podstate_path) as podstate:
            self.previous_boot_phase = json.load(podstate)

        self.new_pods = set()  # pods not present when shut down

        self.update_k8s_pod_status()
        self.members = [(ns, name)
                        for ns, names in self.k8s_pod_status.items()
                        for name in names.keys()]

    def condition_name(self):
        return 'Kubernetes pods restored to state from previous shutdown'

    def update_k8s_pod_status(self):
        """Helper function to grab the status of all pods.

        Updates the internal k8s_pod_status dict to be consistent with
        the status of the pods.

        Args: None.
        Returns: None.
        """
        all_pods = self.k8s_api.list_pod_for_all_namespaces()
        self.k8s_pod_status = k8s_pods_to_status_dict(all_pods)

    def on_check_action(self):
        """Update pod status before doing each check for completion."""
        self.update_k8s_pod_status()

    def post_wait_action(self):
        report = Report(['Namespace', 'Pod name'])
        report.add_rows(self.pending)
        print(str(report))

    def member_has_completed(self, member):
        """Check if a pod has "completed" its boot.

        A pod is considered to have "completed" if either a pod with
        its name was present at the previous shutdown, and the current
        pod has reached the same state as its counterpart, or if the
        pod was not present, and its state is either "Running" or
        "Succeeded".
        """
        ns, name = member
        simple_answer = self.k8s_pod_status[ns][name] in ('Succeeded', 'Running')

        if member in self.new_pods:
            return simple_answer

        elif ns not in self.previous_boot_phase:
            LOGGER.warning('Namespace "%s" was not present at last shutdown; '
                           'waiting for "Succeeded" or "Running" phase for all constituents.',
                           ns)
            self.new_pods.add(member)
            return simple_answer

        elif name not in self.previous_boot_phase[ns]:
            LOGGER.warning('Pod "%s" from namespace "%s" was not present at last shutdown; '
                           'waiting for "Succeeded" or "Running" phase.',
                           name, ns)
            self.new_pods.add(member)
            return simple_answer

        # By now, we've determined that this pod was present at the
        # last shutdown and had the same name. Thus we should be able
        # to tell if it's "completed" if it is in the same state as it
        # was at the last shutdown.
        return self.k8s_pod_status[ns][name] == self.previous_boot_phase[ns][name]


def do_mgmt_boot(args):
    """Run the bootup process for the management cluster.

    This will send IPMI power on commands to the NCNs, check if they
    can be accessed by SSH, run the platform-startup ansible playbook,
    and then wait until all Kubernetes pods have been restored to the
    same state as before the previous shutdown.

    Args:
        args (Namespace): the argparse.Namespace object passed from the
            argument parser.

    Raises:
        SystemExit if a fatal error is encountered.
    """
    username, password = get_username_and_password_interactively(username_prompt='IPMI username',
                                                                 password_prompt='IPMI password')

    with RunningService('dhcpd', dry_run=args.dry_run, sleep_after_start=5):
        non_bis_ncns = get_ncns(['managers', 'storage', 'workers'], exclude=['bis'])

        if not args.dry_run:
            # TODO (SAT-555): Probably should not send a power on if it's already on.
            ipmi_waiter = IPMIPowerStateWaiter(non_bis_ncns, 'on', args.ipmi_timeout,
                                               username, password, send_command=True)
            remaining_nodes = ipmi_waiter.wait_for_completion()

            ssh_waiter = SSHAvailableWaiter(non_bis_ncns - remaining_nodes, args.ssh_timeout)
            inaccessible_nodes = ssh_waiter.wait_for_completion()

            if inaccessible_nodes:
                LOGGER.error('Unable to reach the following NCNs via SSH '
                             'after powering them on: %s. Troubleshoot the '
                             'issue and then try again.',
                             ', '.join(inaccessible_nodes))
                # Have to exit here because playbook will fail if nodes are
                # not available for SSH.
                raise SystemExit(1)

    if not args.dry_run:
        try:
            subprocess.run(['ansible-playbook',
                            '/opt/cray/crayctl/ansible_framework/main/platform-startup.yml'],
                           check=True)
        except subprocess.CalledProcessError as err:
            LOGGER.error('Ansible playbook to start platform services failed. '
                         'Aborting boot attempt: %s', err)
            raise SystemExit(1)

    try:
        k8s_api_waiter = KubernetesAPIAvailableWaiter(60)
    except ConfigException as err:
        LOGGER.error("Failed to load kubernetes config while waiting for kubernetes "
                     "API to become available: %s", err)
        raise SystemExit(1)
    k8s_api_waiter.wait_for_completion()

    try:
        k8s_waiter = KubernetesPodStatusWaiter(args.k8s_timeout)
    except ConfigException as err:
        # Unlikely, given that we loaded the config earlier, but could happen
        LOGGER.error("Failed to load kubernetes config while waiting for pods "
                     "to reach expected states: %s", err)
        raise SystemExit(1)

    with k8s_waiter:
        ceph_waiter = CephHealthWaiter(args.ceph_timeout)
        ceph_waiter.wait_for_completion()

    if k8s_waiter.pending:
        LOGGER.error('The following kubernetes pods failed to reach their '
                     'expected states: %s', ', '.join(k8s_waiter.pending))
        raise SystemExit(1)
