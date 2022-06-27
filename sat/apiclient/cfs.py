#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Client for querying the Configuration Framework Service (CFS) API
"""
from datetime import datetime
import fnmatch
from itertools import chain
import logging
import re
import uuid

from kubernetes.client import ApiException

from sat.apiclient.gateway import APIError, APIGatewayClient
from sat.util import get_val_by_path

LOGGER = logging.getLogger(__name__)


class CFSClient(APIGatewayClient):
    base_resource_path = 'cfs/v2/'

    MAX_SESSION_NAME_LENGTH = 45

    @staticmethod
    def get_valid_session_name(prefix='sat'):
        """Get a valid CFS session name.

        CFS session names are restricted by Kubernetes naming conventions, and
        they must be unique. This method gives an easy way to get a valid, unique
        name, with an optional prefix.

        Note that this uses uuid.uuid4 to generate a 36-character-long uuid and
        adds a hyphen after the prefix. Since CFS session names are limited to
        45 characters, the max prefix length is 45 - 36 - 1 = 8.

        No other validation of the prefix is performed.

        Args:
            prefix (str): the prefix to use for the CFS session name. This will
                be at the beginning of the session name followed by a hyphen.

        Returns:
            str: the session name
        """
        uuid_str = str(uuid.uuid4())

        # Subtract an additional 1 to account for "-" separating prefix from uuid
        prefix_max_len = CFSClient.MAX_SESSION_NAME_LENGTH - len(uuid_str) - 1
        if len(prefix) > prefix_max_len:
            LOGGER.warning(f'Given CFS session prefix is too long and will be '
                           f'truncated ({len(prefix)} > {prefix_max_len})')
            prefix = prefix[:prefix_max_len]

        return '-'.join([prefix, uuid_str])

    def get_configurations(self):
        """Get the CFS configurations

        Returns:
            The CFS configurations.

        Raises:
            APIError: if there is an issue getting configurations
        """
        try:
            return self.get('configurations').json()
        except APIError as err:
            raise APIError(f'Failed to get CFS configurations: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from CFS when getting '
                           f'CFS configurations: {err}')

    def get_configuration(self, name):
        """Get the CFS configuration

        Args:
            name (str): the name of the CFS configuration

        Returns:
            dict: the CFS configuration
        """
        try:
            return self.get('configurations', name).json()
        except APIError as err:
            raise APIError(f'Failed to get CFS configuration "{name}": {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from CFS when getting '
                           f'CFS configuration "{name}": {err}')

    def put_configuration(self, config_name, request_body):
        """Create a new configuration or update an existing configuration

        Args:
            config_name (str): the name of the configuration to create/update
            request_body (dict): the configuration data, which should have a
                'layers' key.
        """
        self.put('configurations', config_name, json=request_body)

    def get_session(self, name):
        """Get details for a session.

        Args:
            name (str): the name of the session to get

        Returns:
            dict: the details about the session
        """
        try:
            return self.get('sessions', name).json()
        except APIError as err:
            raise APIError(f'Failed to get CFS session {name}: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from CFS when getting '
                           f'CFS session {name}: {err}')

    def create_image_customization_session(self, config_name, image_id, target_groups, image_name):
        """Create a new image customization session.

        The session name will be generated with self.get_valid_session_name.

        Args:
            config_name (str): the name of the configuration to use
            image_id (str): the id of the IMS image to customize
            target_groups (list of str): the group names to target. Each group
                name specified here will be defined to point at the IMS image
                specified by `image_id`.
            image_name (str): the name of the image being created, used just
                for logging purposes

        Returns:
            CFSImageConfigurationSession: the created session
        """
        request_body = {
            'name': self.get_valid_session_name(),
            'configurationName': config_name,
            'target': {
                'definition': 'image',
                'groups': [
                    {'name': target_group, 'members': [image_id]}
                    for target_group in target_groups
                ]
            }
        }
        try:
            created_session = self.post('sessions', json=request_body).json()
        except APIError as err:
            raise APIError(f'Failed to create image customization session : {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from CFS when '
                           f'creating CFS session: {err}')

        return CFSImageConfigurationSession(created_session, self, image_name)


class CFSImageConfigurationSession:
    """A class representing an image customization CFS configuration session

    Attributes:
        data (dict): the data from the CFS API for this session
        cfs_client (sat.apiclient.cfs.CFSClient): the CFS API client used to
            create the session and to use to query the session status
        image_name (str): the name specified for the image in a bootprep input
            file. Currently only used for logging, but may be used when creating
            the session in the future if CASMCMS-7564 is resolved.
        pod (kubernetes.client.V1Pod): the pod associated with this session.
            It is set to None until the pod has been created and found by
            update_pod_status. It is updated by each call to update_pod_status.
        init_container_status_by_name (dict): a mapping from init container name
            to status
        container_status_by_name (dict): a mapping from container name to status
    """
    # Values reported by CFS in status.session.status
    COMPLETE_VALUE = 'complete'
    PENDING_VALUE = 'pending'
    # Value reported by CFS in status.session.succeeded when session has succeeded
    SUCCEEDED_VALUE = 'true'
    # Hardcode the namespace in which kuberenetes jobs are created since CFS
    # sessions do not record this information
    KUBE_NAMESPACE = 'services'

    # Hardcode the container status messages
    CONTAINER_RUNNING_VALUE = 'running'
    CONTAINER_WAITING_VALUE = 'waiting'
    CONTAINER_SUCCEEDED_VALUE = 'succeeded'
    CONTAINER_FAILED_VALUE = 'failed'

    def __init__(self, data, cfs_client, image_name):
        """Create a new CFSImageConfigurationSession

        Args:
            data (dict): the data from the CFS API for this session
            cfs_client (sat.apiclient.cfs.CFSClient): the CFS API client used to
                create the session and to use to query the session status
            image_name (str): the name specified for the image in a bootprep
                input file.
        """
        self.data = data
        self.cfs_client = cfs_client
        self.image_name = image_name

        self.logged_job_wait_msg = False
        self.logged_pod_wait_msg = False

        # This is set to the V1Pod for this CFS session by update_pod_status
        self.pod = None

        # We are assuming unique container names within the pod
        self.init_container_status_by_name = {}
        self.container_status_by_name = {}

    @property
    def name(self):
        """str: the name of the CFS session"""
        return self.data.get('name', '')

    @property
    def session_status(self):
        """str: the status of the session according to CFS

        This will be one of 'pending', 'running', or 'complete'
        """
        return get_val_by_path(self.data, 'status.session.status')

    @property
    def complete(self):
        """bool: True if the configuration session is complete, False otherwise"""
        return self.session_status == self.COMPLETE_VALUE

    @property
    def succeeded(self):
        """bool: True if the configuration session succeeded, False otherwise"""
        return get_val_by_path(self.data, 'status.session.succeeded') == self.SUCCEEDED_VALUE

    @property
    def kube_job(self):
        """str: the name of the kubernetes job created by this CFS session"""
        return get_val_by_path(self.data, 'status.session.job')

    @property
    def pod_name(self):
        """str: the name of the pod created by the K8s job for this CFS session"""
        # Handle access to this property before update_pod_status has found the pod
        if self.pod is None:
            return ''
        return self.pod.metadata.name

    @property
    def start_time(self):
        """datetime.datetime: the start time of this CFS session"""
        start_time_str = get_val_by_path(self.data, 'status.session.startTime')
        # Once we can rely on Python 3.7 or greater, can switch this to use fromisoformat
        return datetime.strptime(start_time_str, '%Y-%m-%dT%H:%M:%S')

    @property
    def time_since_start(self):
        """datetime.timedelta: the time that has elapsed since the start of the session"""
        return datetime.utcnow() - self.start_time

    @property
    def resultant_image_id(self):
        """str or None: the ID of the resultant IMS image created by this session or None"""
        artifact_list = get_val_by_path(self.data, 'status.artifacts', [])
        if not artifact_list:
            return None
        # A CFS image customization session can produce more than one resulting
        # image if given multiple target groups referring to different images,
        # but it is not a common use case, so it is not currently supported by
        # CFSClient.create_image_customization_session, so just assume there is
        # only one resultant image here.
        return artifact_list[0].get('result_id', None)

    @staticmethod
    def get_failed_containers(status_by_name):
        """Get the list of failed container names from the given status_by_name

        Args:
            status_by_name (dict): a dictionary mapping from container name to
                status string

        Returns:
            list of str: the container names that have failed
        """
        return [container_name for container_name, status in status_by_name.items()
                if status == 'failed']

    @property
    def failed_containers(self):
        """list of str: list of the failed containers in the pod for this CFS session"""
        return self.get_failed_containers(self.container_status_by_name)

    @property
    def failed_init_containers(self):
        """list of str: list of failed init container names in the pod for this CFS session"""
        return self.get_failed_containers(self.init_container_status_by_name)

    def get_suggested_debug_command(self):
        """Get the best guess at the command the admin should use to debug failure

        Generally if an init container failed, that is the one to debug first.

        Returns:
            str or None: the command that the admin should run to debug the failure,
                or None if no command is available or necessary.
        """
        container_execution_order = [
            'inventory',
            'ansible-*',
            'teardown'
        ]

        # This shouldn't happen but protect against it anyway
        if self.pod is None:
            return None

        kubectl_cmd = f'kubectl logs -n {self.KUBE_NAMESPACE} {self.pod.metadata.name}'
        if self.failed_init_containers:
            # If any init containers fail, none of the (non-init) containers
            # will be run. Kubernetes init containers are executed in-order, so
            # the following line works on the assumption that nothing is
            # modifying the ordering of the containers.
            failed_container = self.failed_init_containers[0]
        elif self.failed_containers:
            for container_name_pattern in container_execution_order:
                failed_containers = [name for name in self.failed_containers
                                     if fnmatch.fnmatch(name, container_name_pattern)]
                if failed_containers:
                    def extract_numeric_suffix(s):
                        match = re.search(r'([0-9]+)$', s)
                        if match is None:
                            return 0
                        return int(match.group(0))
                    failed_container = min(failed_containers, key=extract_numeric_suffix)
                    break
            else:
                # Some container failed that is not listed in the execution
                # order above.
                return None
        else:
            return None

        return f'{kubectl_cmd} -c {failed_container}'

    def update_cfs_status(self):
        """Query the CFS API to update the status of this CFS session

        Returns:
            None

        Raises:
            APIError: if there is a failure to get session status from the CFS API
        """
        fail_msg = f'Failed to get updated session status for session {self.name}'

        try:
            session_details = self.cfs_client.get_session(self.name)
        except APIError as err:
            raise APIError(f'{fail_msg}: {err}')

        try:
            self.data['status'] = session_details['status']
        except KeyError as err:
            raise APIError(f'{fail_msg}: {err} key was missing in response from CFS.')

    def get_container_status_description(self, container_status):
        """Get a string representation of the container status

        Args:
            container_status (kubernetes.client.V1ContainerStatus): the status
                of the container

        Returns:
            str: One of 'running', 'waiting', 'succeeded', or 'failed'
        """
        # The Python Kuberenetes client docs are misleading in that they
        # imply only one of these keys will be present, but in reality,
        # they are all present, and set to None if not the current state
        if container_status.state.running:
            return self.CONTAINER_RUNNING_VALUE
        elif container_status.state.terminated:
            if container_status.state.terminated.exit_code == 0:
                return self.CONTAINER_SUCCEEDED_VALUE
            else:
                return self.CONTAINER_FAILED_VALUE
        else:
            return self.CONTAINER_WAITING_VALUE

    def get_container_status_change_msg(self, container_name, new_status, old_status=None):
        """Get a nicely formatted container status change message.

        Args:
            container_name (str): the name of the container that changed state
            new_status (str): the new status of the container
            old_status (str): the old status of the container, if known

        Returns:
            str: the description of the container status change
        """
        container_name_width = max(
            len(container_status.name)
            for container_status in chain(
                self.pod.status.init_container_statuses,
                self.pod.status.container_statuses
            )
        )
        status_width = max(len(status) for status in [
                self.CONTAINER_RUNNING_VALUE,
                self.CONTAINER_WAITING_VALUE,
                self.CONTAINER_SUCCEEDED_VALUE,
                self.CONTAINER_FAILED_VALUE
            ]
        )

        msg = (
            f'Container {container_name: <{container_name_width}} '
            f'transitioned to {new_status: <{status_width}}'
        )

        if old_status:
            msg += f' from {old_status: <{status_width}}'

        return msg

    def _update_container_status(self):
        """Update init_container and container status mappings

        Updates `init_container_status_by_name` and `container_status_by_name`
        attributes with latest status from `self.pod`.

        Returns:
            None
        """
        state_log_msgs = []

        # This shouldn't happen since this is only called by update_pod_status
        # after the pod is successfully found.
        if self.pod is None:
            return

        # Update both init_container_status_by_name and container_status_by_name
        for prefix in ('init_', ''):
            status_by_name = getattr(self, f'{prefix}container_status_by_name')
            for container_status in getattr(self.pod.status, f'{prefix}container_statuses'):
                container_name = container_status.name

                status = self.get_container_status_description(container_status)

                old_status = status_by_name.get(container_status.name)

                # First time reporting status or status has changed
                if not old_status or (status != old_status):
                    state_log_msgs.append(self.get_container_status_change_msg(container_name,
                                                                               status, old_status))

                status_by_name[container_name] = status

        if state_log_msgs:
            LOGGER.info(f'CFS session: {self.name: <{CFSClient.MAX_SESSION_NAME_LENGTH}} '
                        f'Image: {self.image_name}:')
            for msg in state_log_msgs:
                LOGGER.info(f'    {msg}')

    def update_pod_status(self, kube_client):
        """Get the pod for the Kubernetes job.

        The CFS session starts a Kubernetes job which has the following spec:

            backoffLimit: 0
            completions: 1
            parallelism: 1

        As a result, it will only ever run one pod, regardless of whether it
        completes successfully or not.

        Args:
            kube_client (kubernetes.client.CoreV1Api): the Kubernetes API client

        Returns:
            None

        Raises:
            APIError: if there is a problem querying the Kubernetes API for
                status of the pod for the session.
        """
        try:
            pods = kube_client.list_namespaced_pod(self.KUBE_NAMESPACE,
                                                   label_selector=f'job-name={self.kube_job}')
        except ApiException as err:
            raise APIError(f'Failed to query Kubernetes for pod associated '
                           f'with CFS Kubernetes job {self.kube_job}: {err}')

        try:
            self.pod = pods.items[0]
        except IndexError:
            if not self.logged_pod_wait_msg:
                LOGGER.info(f'Waiting for creation of Kubernetes pod associated with session {self.name}.')
                self.logged_pod_wait_msg = True
        else:
            self._update_container_status()

    def update_status(self, kube_client):
        """Query the CFS and Kubernetes APIs to update the status of this CFS session

        Args:
            kube_client (kubernetes.client.CoreV1Api): the Kubernetes API client

        Returns:
            None. Updates the status stored in this object.
        """
        self.update_cfs_status()

        if self.session_status == self.PENDING_VALUE:
            if not self.logged_job_wait_msg:
                LOGGER.info(f'Waiting for CFS to create Kubernetes job associated with session {self.name}.')
                self.logged_job_wait_msg = True
        else:
            self.update_pod_status(kube_client)
