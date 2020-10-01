"""
Handles capturing state (e.g. k8s pod state) before a shutdown operation.

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
from abc import ABC, abstractmethod
import json
import logging
import os
import sys
import warnings
from datetime import datetime

from kubernetes.client import CoreV1Api
from kubernetes.config import load_kube_config, ConfigException
from yaml import YAMLLoadWarning

from sat.apiclient import FabricControllerClient
from sat.session import SATSession
from sat.cli.bootsys.defaults import (
    DEFAULT_STATE_DIR,
    POD_STATE_DIR, POD_STATE_FILE_PREFIX,
    HSN_STATE_DIR, HSN_STATE_FILE_PREFIX
)
from sat.cli.bootsys.util import k8s_pods_to_status_dict
from sat.config import get_config_value
from sat.util import BeginEndLogger


LOGGER = logging.getLogger(__name__)


class StateError(Exception):
    """Failed to capture state information or load captured state information."""
    pass


class PodStateError(StateError):
    """Failed to capture or load pod state."""
    pass


class StateRecorder(ABC):
    """
    Records some state information to a time-stamped file and maintains a
    symbolic link to the most recent version of that state.

    The data is stored in JSON and loaded as JSON.
    """

    def __init__(self, dir_path, file_prefix, num_to_keep, file_suffix='.json'):
        """
        Create a new StateRecorder object to record and load state information.

        Args:
            dir_path (str): The path to the directory containing the files.
            file_prefix (str): The prefix of files to count and remove extras.
            num_to_keep (int): The number of files to keep.
            file_suffix (str): The suffix of the files to remove.
        """
        self.dir_path = dir_path
        self.file_prefix = file_prefix
        self.num_to_keep = num_to_keep
        self.file_suffix = file_suffix

    @property
    def symlink_file_name(self):
        """str: The name of the symlink file, not including the directory."""
        return f'{self.file_prefix}{self.file_suffix}'

    @property
    def symlink_file_path(self):
        """str: The full path to the symbolic link that points to the latest state file."""
        return os.path.join(self.dir_path, self.symlink_file_name)

    def _remove_old_files(self):
        """Remove old files within the given directory that match the given prefix.

        File names will be sorted alphabetically, the file with the name consisting
        of only the prefix followed by the suffix will be disregarded, and then all
        but the last `self.num_to_keep` files will be removed.
        """
        # Get the list of all files with the given prefix and suffix but omit the
        # symlink which will have a file name that is just prefix and suffix.
        files = [x for x in sorted(os.listdir(self.dir_path))
                 if x.startswith(self.file_prefix) and x.endswith(self.file_suffix)
                 and x != self.symlink_file_name]

        num_to_remove = len(files) - self.num_to_keep
        if num_to_remove > 0:
            for file_to_remove in files[:num_to_remove]:
                try:
                    os.remove(os.path.join(self.dir_path, file_to_remove))
                except (PermissionError, FileNotFoundError) as err:
                    LOGGER.warning(f'Failed to remove old file {file_to_remove}: {err}')

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

        try:
            with open(new_file, 'w') as f:
                f.write('')
        except OSError as err:
            raise StateError(f'Failed to create new file {new_file}: {err}') from err

        return new_file

    def _update_symlink(self, target_file):
        """Update the symbolic link for the default file.

        An old symbolic link at `self.dir_path`/`self.file_prefix``self.file_suffix`
        will be removed and replaced with a symbolic link that points at `target_file`.

        An error is not raised if the symlink cannot be altered, but a warning is logged.

        Args:
            target_file (str): The target file path for the symlink.
        """
        symlink_file = self.symlink_file_path

        try:
            os.remove(symlink_file)
        except FileNotFoundError:
            LOGGER.info(f'No existing file found to remove at {symlink_file}.')
        except OSError as err:
            LOGGER.warning(f'Failed to remove symlink at {symlink_file}: {err}')
            return

        try:
            os.symlink(target_file, symlink_file)
        except OSError as err:
            LOGGER.warning(f'Failed to create symlink at {symlink_file} pointing '
                           f'to {target_file}: {err}')

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
        the current state info, removes the existing symlink and re-creates it
        to point to the newly created file, and then dumps state info to that
        file. Then removes existing files if necessary to maintain the maximum
        number of state files to keep based on `self.num_to_keep`.

        Raises:
            StateError: if we failed to capture the pod state and save it to the
                given file path
        """
        # This can raise a StateError
        state_data = self.get_state_data()
        try:
            os.makedirs(self.dir_path, exist_ok=True)
        except (FileExistsError, NotADirectoryError) as err:
            raise StateError(
                f'Cannot create state file because one of the leading components '
                f'of the path {self.dir_path} is not a directory.'
            ) from err
        except OSError as err:
            raise StateError(f'Failed to ensure state directory {self.dir_path} exists: {err}')

        new_file_name = self._create_new_file()

        try:
            with open(new_file_name, 'w') as f:
                json.dump(state_data, f)
        except OSError as err:
            raise PodStateError(f'Failed to write pod state to file {new_file_name}: {err}') from err
        self._update_symlink(new_file_name)
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
        symlink_file = self.symlink_file_path
        try:
            with open(symlink_file) as f:
                return json.load(f)
        except OSError as err:
            raise StateError(f'Failed to open file {symlink_file} to read latest state: {err}')
        except ValueError as err:
            raise StateError(f'Failed to parse JSON from file {symlink_file}: {err}')


class PodStateRecorder(StateRecorder):
    """Records the state of k8s pods based on the k8s API."""

    def __init__(self):
        pod_state_dir = os.path.join(DEFAULT_STATE_DIR, POD_STATE_DIR)
        num_to_keep = get_config_value('bootsys.max_pod_states')
        super().__init__(pod_state_dir, POD_STATE_FILE_PREFIX, num_to_keep)

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
        hsn_state_dir = os.path.join(DEFAULT_STATE_DIR, HSN_STATE_DIR)
        num_to_keep = get_config_value('bootsys.max_hsn_states')
        super().__init__(hsn_state_dir, HSN_STATE_FILE_PREFIX, num_to_keep)

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
    print('Capturing state of k8s pods.')
    with BeginEndLogger('kubernetes pod state capture'):
        try:
            PodStateRecorder().dump_state()
        except StateError as err:
            msg = str(err)
            if args.ignore_pod_failures:
                LOGGER.warning(msg)
            else:
                LOGGER.error(msg)
                sys.exit(1)