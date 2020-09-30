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

from collections import namedtuple
import inflect
import json
import logging
import re
import socket
import urllib3
import warnings

from kubernetes.client import CoreV1Api
from kubernetes.config import load_kube_config
from kubernetes.config.config_exception import ConfigException
from paramiko.client import SSHClient
from paramiko.ssh_exception import SSHException
from yaml import YAMLLoadWarning

from sat.apiclient import FabricControllerClient
from sat.cached_property import cached_property
from sat.cli.bootsys.ipmi_console import IPMIConsoleLogger
from sat.cli.bootsys.mgmt_hosts import do_disable_hosts_entries
from sat.cli.bootsys.power import IPMIPowerStateWaiter
from sat.cli.bootsys.state_recorder import PodStateRecorder, HSNStateRecorder, StateError
from sat.cli.bootsys.util import get_groups, get_ncns, RunningService, k8s_pods_to_status_dict, run_ansible_playbook
from sat.cli.bootsys.waiting import GroupWaiter, SimultaneousWaiter, Waiter
from sat.report import Report
from sat.session import SATSession
from sat.util import BeginEndLogger, get_username_and_password_interactively

LOGGER = logging.getLogger(__name__)

INF = inflect.engine()


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

    def __init__(self, timeout, poll_interval=10):
        """Initialize the Kubernetes waiter.

        See GroupWaiter documentation.
        """

        super().__init__(set(), timeout, poll_interval=poll_interval)

        # Load k8s configuration before trying to use API
        self.k8s_api = load_kube_api()

        self.new_pods = set()  # pods not present when shut down

        self.k8s_pod_status = {}
        self.update_k8s_pod_status()
        self.members = [(ns, name)
                        for ns, names in self.k8s_pod_status.items()
                        for name in names.keys()]

    def condition_name(self):
        return 'Kubernetes pods restored to state from previous shutdown'

    @cached_property
    def stored_k8s_pod_status(self):
        """The status of k8s pods that was stored to a file during the previous shutdown."""
        try:
            return PodStateRecorder().get_stored_state()
        except StateError as err:
            LOGGER.warning(f'Failed to get k8s pod state from prior to shutdown; '
                           f'will wait for all k8s pods to reach "Running" or "Completed" '
                           f'states: {err}')
            return {}

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

        elif ns not in self.stored_k8s_pod_status:
            LOGGER.warning('Namespace "%s" was not present at last shutdown; '
                           'waiting for "Succeeded" or "Running" phase for all constituents.',
                           ns)
            self.new_pods.add(member)
            return simple_answer

        elif name not in self.stored_k8s_pod_status[ns]:
            LOGGER.warning('Pod "%s" from namespace "%s" was not present at last shutdown; '
                           'waiting for "Succeeded" or "Running" phase.',
                           name, ns)
            self.new_pods.add(member)
            return simple_answer

        # By now, we've determined that this pod was present at the
        # last shutdown and had the same name. Thus we should be able
        # to tell if it's "completed" if it is in the same state as it
        # was at the last shutdown.
        return self.k8s_pod_status[ns][name] == self.stored_k8s_pod_status[ns][name]


class BGPSpineStatusWaiter(Waiter):
    """Waits for the BGP peers to become established."""

    def condition_name(self):
        return "Spine BGP routes established"

    @staticmethod
    def all_established(stdout):
        """Very simple check to ensure all peers are established.

        This parses the peer states using a basic regular expression
        which matches the state/peer pairs, and then checks if they
        are all "ESTABLISHED".

        Args:
            stdout (str): The stdout of the 'spine-bgp-status.yml'
                ansible playbook

        Returns:
            True if it is believed that all peers have been established,
                or False otherwise.
        """
        status_pair_re = r'(ESTABLISHED|ACTIVE|OPENSENT|OPENCONFIRM|IDLE)/[0-9]+'
        return stdout and all(status == 'ESTABLISHED' for status in
                              re.findall(status_pair_re, stdout))

    @staticmethod
    def get_spine_status():
        """Simple helper function to get spine BGP status.

        Runs run_ansible_playbook() with the spine-bgp-status.yml playbook.

        Args: None.
        Returns: The stdout resulting when running the spine-bgp-status.yml
            playbook or None if it fails.
        """
        return run_ansible_playbook('/opt/cray/crayctl/ansible_framework/main/spine-bgp-status.yml',
                                    exit_on_err=False)

    def pre_wait_action(self):
        # Do one quick check for establishment prior to waiting, and
        # reset the BGP routes if need be.
        spine_bgp_status = BGPSpineStatusWaiter.get_spine_status()
        self.completed = BGPSpineStatusWaiter.all_established(spine_bgp_status)
        if not self.completed:
            LOGGER.info('Screen scrape indicated BGP peers are idle. Resetting.')
            run_ansible_playbook('/opt/cray/crayctl/ansible_framework/main/metallb-bgp-reset.yml',
                                 exit_on_err=False)

    def has_completed(self):
        spine_status_output = BGPSpineStatusWaiter.get_spine_status()
        if spine_status_output is None:
            LOGGER.error('Failed to run spine-bgp-status.yml playbook.')
            return False
        return BGPSpineStatusWaiter.all_established(spine_status_output)


# A representation of a port in a port set.
HSNPort = namedtuple('HSNPort', ('port_set', 'port_xname'))


class HSNBringupWaiter(GroupWaiter):
    """Run the HSN bringup script and wait for it to be brought up."""

    def __init__(self, timeout, poll_interval=1):
        """Create a new HSNBringupWaiter."""
        super().__init__(set(), timeout, poll_interval)
        self.fabric_client = FabricControllerClient(SATSession())
        self.hsn_state_recorder = HSNStateRecorder()
        # dict mapping from port set name to dict mapping from port xname to enabled status
        self.current_hsn_state = {}

    def condition_name(self):
        return "HSN bringup"

    def pre_wait_action(self):
        run_ansible_playbook('/opt/cray/crayctl/ansible_framework/main/ncmp_hsn_bringup.yaml',
                             exit_on_err=False)

        # Populate members with known members from fabric controller API
        self.members = {HSNPort(port_set, port_xname)
                        for port_set, port_xnames in self.fabric_client.get_fabric_edge_ports().items()
                        for port_xname in port_xnames}

    def on_check_action(self):
        """Get the latest HSN state from the fabric controller API."""
        self.current_hsn_state = self.fabric_client.get_fabric_edge_ports_enabled_status()

    @cached_property
    def stored_hsn_state(self):
        """dict: HSN state from the file where it was saved prior to shutdown

        Will be a dict mapping from the port set names ('fabric-ports', 'edge-ports')
        to a dict mapping from port xnames (str) to port enabled status (bool). Will
        be the empty dict if there is a failure to load the saved state.
        """
        try:
            return self.hsn_state_recorder.get_stored_state()
        except StateError as err:
            LOGGER.warning(f'Failed to get HSN state from prior to shutdown; '
                           f'will wait for all links to come up: {err}')
            return {}

    def member_has_completed(self, member):
        """Get whether the given member has completed.

        Args:
            member (HSNPort): the port to check for completion.

        Returns:
            True if the port status is enabled or if the port was disabled
            before the shutdown. False otherwise.
        """
        try:
            expected_state = self.stored_hsn_state[member.port_set][member.port_xname]
        except KeyError:
            # If the port was not known before shutdown, assume it should be enabled.
            # E.g., this could happen if a switch or cable was added while the system
            # was shut down.
            expected_state = True

        try:
            current_state = self.current_hsn_state[member.port_set][member.port_xname]
        except KeyError:
            # If no state is reported for this port, then it is not healthy
            return False

        # if expected state is true, then current state must be true
        return current_state or not expected_state


def restart_ceph_services():
    """Restart ceph services on the storage nodes.

    This uses the ansible inventory to get the list of nodes designated as
    'storage' nodes.

    It iterates first over the nodes on which to restart the services,
    and then over the services to restart, restarting all the services for
    one node before proceeding to the next node.  This is different from the
    documented Shasta 1.3 procedure, on which this function is based.  The
    documented procedure restarts one service across all the nodes before
    proceeding to the next service.

    Raises:
        SystemExit: if connecting to one of the hosts failed, or if restarting
            one of the services failed
    """
    storage_nodes = get_groups(['storage'])
    ceph_services = ['ceph-mon.target', 'ceph-mgr.target', 'ceph-mds.target']
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()

    for storage_node in storage_nodes:
        try:
            ssh_client.connect(storage_node)
        except (SSHException, socket.error) as err:
            LOGGER.error(f'Connecting to {storage_node} failed.  Error: {err}')
            raise SystemExit(1)

        for ceph_service in ceph_services:
            command = f'systemctl restart {ceph_service}'
            try:
                _, stdout, stderr = ssh_client.exec_command(f'systemctl restart {ceph_service}')
            except SSHException as err:
                LOGGER.error(f'Command "{command}" failed.  Host: {storage_node}.  Error: {err}')
                raise SystemExit(1)

            # Command may run successfully but still return nonzero, which is an error.
            # Checking return status also blocks until the command completes.
            if stdout.channel.recv_exit_status():
                LOGGER.error(f'Command "{command}" failed.  Host: {storage_node}.  Stderr: {stderr.read()}')
                raise SystemExit(1)


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
            with IPMIConsoleLogger(non_bis_ncns):
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

    LOGGER.info('Disabling entries in /etc/hosts to prepare for starting DNS.')
    do_disable_hosts_entries()

    if not args.dry_run:
        with BeginEndLogger('platform-startup.yml ansible playbook'):
            run_ansible_playbook('/opt/cray/crayctl/ansible_framework/main/platform-startup.yml')
        with BeginEndLogger('restart ceph services on storage nodes'):
            restart_ceph_services()

    try:
        k8s_api_waiter = KubernetesAPIAvailableWaiter(60)
    except ConfigException as err:
        LOGGER.error("Failed to load kubernetes config while waiting for kubernetes "
                     "API to become available: %s", err)
        raise SystemExit(1)
    with BeginEndLogger('wait for k8s API available'):
        k8s_api_waiter.wait_for_completion()

    try:
        k8s_waiter = KubernetesPodStatusWaiter(args.k8s_timeout)
    except ConfigException as err:
        # Unlikely, given that we loaded the config earlier, but could happen
        LOGGER.error("Failed to load kubernetes config while waiting for pods "
                     "to reach expected states: %s", err)
        raise SystemExit(1)

    with BeginEndLogger('wait for k8s pods healthy'), k8s_waiter:
        ceph_bgp_waiter = SimultaneousWaiter([CephHealthWaiter, BGPSpineStatusWaiter],
                                             max(args.ceph_timeout, args.bgp_timeout))
        with BeginEndLogger('wait for ceph healthy and BGP peering sessions established'):
            ceph_bgp_waiter.wait_for_completion()

    if k8s_waiter.pending:
        pending_pods = [f'{" ".join(pod)}' for pod in k8s_waiter.pending]
        LOGGER.error(f'The following kubernetes {INF.plural("pod", len(pending_pods))} '
                     f'failed to reach their expected states: '
                     f'{", ".join(pending_pods)}')
        raise SystemExit(1)

    hsn_waiter = HSNBringupWaiter(args.hsn_timeout)
    with BeginEndLogger('bring up HSN and wait for healthy'):
        hsn_waiter.wait_for_completion()

    num_pending = len(hsn_waiter.pending)
    if hsn_waiter.pending:
        LOGGER.error(f'The following HSN {INF.plural("port", num_pending)} '
                     f'{INF.plural_verb("is", num_pending)} not enabled: '
                     f'{", ".join(port.port_xname for port in hsn_waiter.pending)}')
