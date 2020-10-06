"""
Waits for k8s API availability and for k8s pods to appear to be healthy.

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
import warnings

import inflect
from kubernetes.client import CoreV1Api
from kubernetes.config import load_kube_config, ConfigException
import urllib3
from yaml import YAMLLoadWarning

from sat.cached_property import cached_property
from sat.cli.bootsys.state_recorder import PodStateRecorder, StateError
from sat.cli.bootsys.util import k8s_pods_to_status_dict
from sat.cli.bootsys.waiting import GroupWaiter, Waiter
from sat.report import Report
from sat.util import BeginEndLogger

LOGGER = logging.getLogger(__name__)
INF = inflect.engine()


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


def do_k8s_check(args):
    """Wait for Kubernetes API and pods to appear healthy.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
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

    with BeginEndLogger('wait for k8s pods healthy'):
        k8s_waiter.wait_for_completion()

    if k8s_waiter.pending:
        pending_pods = [f'{" ".join(pod)}' for pod in k8s_waiter.pending]
        LOGGER.error(f'The following kubernetes {INF.plural("pod", len(pending_pods))} '
                     f'failed to reach their expected states: '
                     f'{", ".join(pending_pods)}')
        raise SystemExit(1)
