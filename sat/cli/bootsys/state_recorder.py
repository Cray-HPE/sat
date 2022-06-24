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
Handles capturing state (e.g. k8s pod state) before a shutdown operation.
"""
from abc import ABC, abstractmethod
import json
import logging
import os
import sys
from urllib3.exceptions import InsecureRequestWarning
import warnings
from datetime import datetime

from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError, ClientError
from kubernetes.client import CoreV1Api
from kubernetes.config import load_kube_config, ConfigException
from yaml import YAMLLoadWarning

from sat.apiclient import FabricControllerClient
from sat.session import SATSession
from sat.cli.bootsys.defaults import (
    DEFAULT_LOCAL_STATE_DIR,
    POD_STATE_DIR, POD_STATE_FILE_PREFIX,
    HSN_STATE_DIR, HSN_STATE_FILE_PREFIX
)
from sat.cli.bootsys.util import k8s_pods_to_status_dict
from sat.config import get_config_value
from sat.util import BeginEndLogger, get_s3_resource


LOGGER = logging.getLogger(__name__)


class StateError(Exception):
    """Failed to capture state information or load captured state information."""
    pass


class PodStateError(StateError):
    """Failed to capture or load pod state."""
    pass


class StateRecorder(ABC):
    """
    Records some state information to a time-stamped file and stores it in the
    configured S3 bucket.

    The data is stored in JSON and loaded as JSON.
    """

    def __init__(self, description, dir_path, file_prefix, num_to_keep, s3, bucket_name, file_suffix='.json'):
        """
        Create a new StateRecorder object to record and load state information.

        Args:
            description (str): A description of the state recorded by this object.
            dir_path (str): The path to the directory containing the files.
            file_prefix (str): The prefix of files to count and remove extras.
            num_to_keep (int): The number of files to keep.
            s3 (ServiceResource): A boto3.resources.factory.s3.ServiceResource object.
            bucket_name (str): The name of the S3 bucket to use.
            file_suffix (str): The suffix of the files to remove.
        """
        self.description = description
        self.dir_path = dir_path
        self.file_prefix = file_prefix
        self.num_to_keep = num_to_keep
        self.file_suffix = file_suffix
        self.s3 = s3
        self.bucket_name = bucket_name

    def _get_s3_state_files(self):
        """Get a list of state files the configured S3 bucket.

        File names will be sorted by last-modified time, from oldest to most recent.
        """
        try:
            s3_bucket = self.s3.Bucket(self.bucket_name)
            state_files = [
                f.key for f in
                sorted(s3_bucket.objects.filter(Prefix=self.dir_path), key=lambda x: x.last_modified)
                if os.path.basename(f.key).startswith(self.file_prefix) and f.key.endswith(self.file_suffix)
            ]
            return state_files
        except (BotoCoreError, ClientError, Boto3Error) as err:
            raise StateError(f'Unable to list files in S3 Bucket {self.bucket_name}: {err}')

    def _remove_old_files(self):
        """Remove old files within the given S3 bucket that match the given prefix.

        File names will be sorted by last-modified time and all but the last `self.num_to_keep` files will be removed.
        """
        candidates_for_removal = self._get_s3_state_files()
        LOGGER.debug('Current state files: %s', candidates_for_removal)

        num_to_remove = len(candidates_for_removal) - self.num_to_keep
        if num_to_remove > 0:
            for file_to_remove in candidates_for_removal[:num_to_remove]:
                LOGGER.debug('Removing %s from S3', file_to_remove)
                try:
                    self.s3.Object(self.bucket_name, file_to_remove).delete()
                except (BotoCoreError, ClientError, Boto3Error) as err:
                    LOGGER.warning(f'Failed to remove old file {file_to_remove} from S3: {err}')

        LOGGER.debug('Files left in bucket: %s', self._get_s3_state_files())

    def _create_new_file(self):
        """Create a new file in the given directory.

        The new file name will be of the form `file_prefix`.TIMESTAMP`file_suffix`.

        Returns:
            str: The name of the newly created file.

        Raises:
            StateError: if the new file cannot be created.
        """
        timestamp_str = datetime.utcnow().strftime('%Y-%m-%dT%H:%M:%S')
        new_file = os.path.join(self.dir_path,
                                f'{self.file_prefix}.{timestamp_str}{self.file_suffix}')
        local_new_file_path = os.path.join(DEFAULT_LOCAL_STATE_DIR, new_file)

        try:
            with open(local_new_file_path, 'w') as f:
                f.write('')
        except OSError as err:
            raise StateError(f'Failed to create new file {local_new_file_path}: {err}') from err

        return new_file

    def _ensure_local_dir_path_exists(self):
        """Ensure that DEFAULT_LOCAL_STATE_DIR/self.dir_path exists"""
        local_dir_path = os.path.join(DEFAULT_LOCAL_STATE_DIR, self.dir_path)
        try:
            os.makedirs(local_dir_path, exist_ok=True)
        except (FileExistsError, NotADirectoryError) as err:
            raise StateError(
                f'Cannot create state file because one of the leading components '
                f'of the path {local_dir_path} is not a directory.'
            ) from err
        except OSError as err:
            raise StateError(f'Failed to ensure state directory {local_dir_path} exists: {err}')

    @abstractmethod
    def get_state_data(self):
        """Gets the state data that should be written to the file.

        Returns:
            The data representing the state. This will be encoded as JSON and
            dumped to a file by `dump_state`.

        Raises:
            StateError: if there is a failure to get the state.
        """
        raise NotImplementedError("'get_state_data' is not implemented on abstract "
                                  "base class StateRecorder.")

    def dump_state(self):
        """Dump state information to a file in `self.dir_path`.

        Ensures that the `self.dir_path` exists and then creates a new file for
        the current state info, dumps state info to that file.  Then removes
        existing files from the S3 bucket if necessary to maintain the maximum
        number of state files to keep based on `self.num_to_keep`.

        Raises:
            StateError: if we failed to capture the pod state and save it to the
                given file path
        """
        # This can raise a StateError
        state_data = self.get_state_data()

        self._ensure_local_dir_path_exists()
        new_file_name = self._create_new_file()
        local_new_file_name = os.path.join(DEFAULT_LOCAL_STATE_DIR, new_file_name)

        try:
            with open(local_new_file_name, 'w') as f:
                json.dump(state_data, f)
        except OSError as err:
            raise StateError(f'Failed to write state to file {local_new_file_name}: {err}') from err
        try:
            LOGGER.debug('Uploading %s to S3', new_file_name)
            # TODO(SAT-926): Start verifying HTTPS requests
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=InsecureRequestWarning)
                self.s3.Object(self.bucket_name, new_file_name).upload_file(local_new_file_name)
        except (ClientError, BotoCoreError, Boto3Error) as err:
            raise PodStateError(f'Failed to dump state to S3: {err}')
        finally:
            os.remove(local_new_file_name)

        self._remove_old_files()

    def get_stored_state(self):
        """Get the state information most recently stored to a file.

        This assumes the information in the file is in JSON format and parses it
        with JSON.

        Returns:
            The latest state information loaded from the given file and parsed
            with JSON.

        Raises:
            StateError: if the file containing the latest state cannot be
                opened or parsed with JSON.
        """
        files_in_bucket = self._get_s3_state_files()
        LOGGER.debug('Files in bucket: %s', files_in_bucket)
        if not files_in_bucket:
            raise StateError('No stored state found')
        latest_state_file = os.path.join(files_in_bucket[-1])
        latest_state_file_local_path = os.path.join(DEFAULT_LOCAL_STATE_DIR, latest_state_file)
        LOGGER.debug('Latest state file: %s', latest_state_file)
        self._ensure_local_dir_path_exists()
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=InsecureRequestWarning)
                self.s3.Object(self.bucket_name, latest_state_file).download_file(latest_state_file_local_path)
            LOGGER.debug('Downloaded %s to %s', latest_state_file, latest_state_file_local_path)
        except (BotoCoreError, ClientError, Boto3Error) as err:
            raise StateError(f'Unable to download {latest_state_file} from s3: {err}')

        try:
            with open(latest_state_file_local_path) as f:
                state_data = json.load(f)
            return state_data
        except OSError as err:
            raise StateError(
                f'Failed to open downloaded file {latest_state_file_local_path} to read latest state: {err}'
            )
        except ValueError as err:
            raise StateError(f'Failed to parse JSON from downloaded file {latest_state_file_local_path}: {err}')
        finally:
            os.remove(latest_state_file_local_path)


class PodStateRecorder(StateRecorder):
    """Records the state of k8s pods based on the k8s API."""

    def __init__(self):
        num_to_keep = get_config_value('bootsys.max_pod_states')
        s3 = get_s3_resource()
        bucket_name = get_config_value('s3.bucket')
        super().__init__('kubernetes pod state', POD_STATE_DIR,
                         POD_STATE_FILE_PREFIX, num_to_keep, s3, bucket_name)

    def get_state_data(self):
        """Get K8s pod information in a dictionary.

        Returns:
            K8s pod information as a dictionary mapping from namespace to pod
            name to pod phase string.

        Raises:
            PodStateError: if we failed to load kubernetes config
        """
        # Load k8s configuration before trying to use API
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            raise PodStateError('Failed to load kubernetes config: {}'.format(err)) from err

        k8s_api = CoreV1Api()
        all_pods = k8s_api.list_pod_for_all_namespaces()
        return k8s_pods_to_status_dict(all_pods)


class HSNStateRecorder(StateRecorder):
    """Records the state of the High-speed Network (HSN) according to the fabric controller API."""

    def __init__(self):
        num_to_keep = get_config_value('bootsys.max_hsn_states')
        s3 = get_s3_resource()
        bucket_name = get_config_value('s3.bucket')
        super().__init__('high-speed network (HSN) state', HSN_STATE_DIR,
                         HSN_STATE_FILE_PREFIX, num_to_keep, s3, bucket_name)

        self.fabric_client = FabricControllerClient(SATSession())

    def get_state_data(self):
        """Get HSN state information in a dictionary.

        Queries the fabric controller API to get the state of all the links in
        the high-speed network (HSN).

        Returns:
            HSN state information as a dictionary mapping from HSN port set name
            to a dictionary mapping from xname strings to booleans indicating
            whether that port is enabled or not.
        """
        return self.fabric_client.get_fabric_edge_ports_enabled_status()


def do_state_capture(args):
    """Capture and record state about k8s pods.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootsys subcommand.

    Returns:
        None.

    Raises:
        SystemExit: if there is a failure to capture state.
    """
    state_recorders = [PodStateRecorder()]

    failed = []
    LOGGER.info('Capturing system state.')
    with BeginEndLogger('system state capture'):
        for sr in state_recorders:
            try:
                LOGGER.info(f'Capturing {sr.description}')
                sr.dump_state()
            except StateError as err:
                LOGGER.error(f'Failed to capture {sr.description}: {err}')
                failed.append(sr)

    if failed:
        sys.exit(1)
    else:
        LOGGER.info('Finished capturing system state.')
