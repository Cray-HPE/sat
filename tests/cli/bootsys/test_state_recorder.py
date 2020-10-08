"""
Unit tests for the service_activity module.

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
from kubernetes.config import ConfigException
import logging
import unittest
from unittest.mock import call, patch, Mock

from sat.cli.bootsys.state_recorder import (
    HSNStateRecorder,
    PodStateError, PodStateRecorder,
    StateError, StateRecorder
)


class SimpleRecorder(StateRecorder):

    CONST_DATA = {
        'foo': 'bar'
    }

    def __init__(self, *args, **kwargs):
        super().__init__('simple state', *args, **kwargs)

    def get_state_data(self):
        return self.CONST_DATA


class TestStateRecorder(unittest.TestCase):
    """Test the StateRecorder abstract base class.
    """

    def setUp(self):
        """Create an object and set up mocks."""
        self.dir_path = '/tmp'
        self.file_prefix = 'simple'
        self.num_to_keep = 5
        self.file_suffix = '.json'
        self.simple_recorder = SimpleRecorder(self.dir_path, self.file_prefix, self.num_to_keep)
        self.symlink_file_name = f'{self.file_prefix}{self.file_suffix}'
        self.symlink_file_path = f'{self.dir_path}/{self.file_prefix}{self.file_suffix}'
        self.base_file_list = [self.symlink_file_name]

        self.mock_listdir = patch('os.listdir').start()
        self.mock_remove = patch('os.remove').start()

        self.mock_open = patch('builtins.open').start()
        self.mock_date_str = '2020-09-07T18:05:14'
        self.mock_datetime = patch('sat.cli.bootsys.state_recorder.datetime').start()
        self.mock_utcnow = Mock()
        self.mock_datetime.utcnow = self.mock_utcnow
        self.mock_utcnow.return_value.strftime.return_value = self.mock_date_str

        self.mock_symlink = patch('os.symlink').start()
        self.mock_makedirs = patch('os.makedirs').start()
        self.mock_json_dump = patch('json.dump').start()
        self.mock_json_load = patch('json.load').start()

    def tearDown(self):
        """Stop all mock patches."""
        patch.stopall()

    def set_up_state_recorder_method_mocks(self):
        """Mock some of the StateRecorder methods to help test higher-level methods."""
        self.method_order_tracker = Mock()
        self.mock_create_new_file = patch('sat.cli.bootsys.state_recorder.StateRecorder._create_new_file',
                                          self.method_order_tracker._create_new_file).start()
        self.mock_update_symlink = patch('sat.cli.bootsys.state_recorder.StateRecorder._update_symlink',
                                         self.method_order_tracker._update_symlink).start()
        self.mock_remove_old_files = patch('sat.cli.bootsys.state_recorder.StateRecorder._remove_old_files',
                                           self.method_order_tracker._remove_old_files).start()

    def test_init(self):
        """Test instantiation of a simple subclass of StateRecorder."""
        self.assertEqual(self.dir_path, self.simple_recorder.dir_path)
        self.assertEqual(self.file_prefix, self.simple_recorder.file_prefix)
        self.assertEqual(self.num_to_keep, self.simple_recorder.num_to_keep)
        self.assertEqual(self.file_suffix, self.simple_recorder.file_suffix)

    def test_init_non_default_suffix(self):
        """Test instantiation of a simple subclass of StateRecorder with non-default suffix."""
        dir_path = '/tmp'
        file_prefix = 'simple'
        num_to_keep = 10
        file_suffix = '.yaml'
        recorder = SimpleRecorder(dir_path, file_prefix, num_to_keep, file_suffix)
        self.assertEqual(dir_path, recorder.dir_path)
        self.assertEqual(file_prefix, recorder.file_prefix)
        self.assertEqual(num_to_keep, recorder.num_to_keep)
        self.assertEqual(file_suffix, recorder.file_suffix)

    def test_symlink_file_name(self):
        """Test symlink_file_name property of StateRecorder."""
        self.assertEqual(self.symlink_file_name, self.simple_recorder.symlink_file_name)

    def test_symlink_file_path(self):
        """Test symlink_file_path property of StateRecorder."""
        self.assertEqual('/tmp/simple.json', self.simple_recorder.symlink_file_path)

    def test_remove_old_files_none(self):
        """Test _remove_old_files with no files except the symlink matching prefix and suffix."""
        self.mock_listdir.return_value = self.base_file_list
        self.simple_recorder._remove_old_files()
        self.mock_remove.assert_not_called()

    def test_remove_old_files_below_limit(self):
        """Test _remove_old_files with the number of files below the limit."""
        self.mock_listdir.return_value = [self.symlink_file_name,
                                          f'{self.file_prefix}.1{self.file_suffix}']
        self.simple_recorder._remove_old_files()
        self.mock_remove.assert_not_called()

    def test_remove_old_files_at_limit(self):
        """Test _remove_old_files with the number of files at the limit."""
        self.mock_listdir.return_value = (
            self.base_file_list +
            [f'{self.file_prefix}.{i}{self.file_suffix}' for i in range(self.num_to_keep)]
        )
        self.simple_recorder._remove_old_files()
        self.mock_remove.assert_not_called()

    def test_remove_old_files_over_limit(self):
        """Test _remove_old_files with the number of files over the limit."""
        numbered_files = [f'{self.file_prefix}.{i}{self.file_suffix}'
                          for i in range(self.num_to_keep * 2)]
        self.mock_listdir.return_value = self.base_file_list + numbered_files
        self.simple_recorder._remove_old_files()
        self.mock_remove.assert_has_calls([
            call(f'{self.dir_path}/{file_name}') for file_name in numbered_files[:self.num_to_keep]
        ])

    def test_create_new_file_success(self):
        """Test _create_new_file in the successful case."""
        self.simple_recorder._create_new_file()
        self.mock_open.assert_called_once_with(
            f'{self.dir_path}/{self.file_prefix}.{self.mock_date_str}{self.file_suffix}', 'w'
        )
        self.mock_open.return_value.__enter__.return_value.write.assert_called_once_with('')

    def test_create_new_file_open_failure(self):
        """Test _create_new_file when open fails."""
        self.mock_open.side_effect = OSError
        with self.assertRaises(StateError):
            self.simple_recorder._create_new_file()
        self.mock_open.assert_called_once_with(
            f'{self.dir_path}/{self.file_prefix}.{self.mock_date_str}{self.file_suffix}', 'w'
        )
        self.mock_open.return_value.__enter__.assert_not_called()

    def test_create_new_file_write_failure(self):
        """Test _create_new_file when write fails."""
        self.mock_open.return_value.__enter__.return_value.write.side_effect = OSError
        with self.assertRaises(StateError):
            self.simple_recorder._create_new_file()
        self.mock_open.assert_called_once_with(
            f'{self.dir_path}/{self.file_prefix}.{self.mock_date_str}{self.file_suffix}', 'w'
        )
        self.mock_open.return_value.__enter__.return_value.write.assert_called_once_with('')

    def test_update_symlink(self):
        """Test _update_symlink in the successful case."""
        target = '/tmp/bullseye.json'
        self.simple_recorder._update_symlink(target)
        self.mock_remove.assert_called_once_with(self.symlink_file_path)
        self.mock_symlink.assert_called_once_with(target, self.symlink_file_path)

    def test_update_symlink_remove_error(self):
        """Test _update_symlink when removal of the old symlink fails."""
        self.mock_remove.side_effect = OSError
        target = '/tmp/irreplaceable.json'
        with self.assertLogs(level=logging.WARNING):
            self.simple_recorder._update_symlink(target)
        self.mock_remove.assert_called_once_with(self.symlink_file_path)
        self.mock_symlink.assert_not_called()

    def test_update_symlink_remove_not_present(self):
        """Test _update_symlink when old symlink does not exist."""
        self.mock_remove.side_effect = FileNotFoundError
        target = '/tmp/not_present.json'
        with self.assertLogs(level=logging.INFO):
            self.simple_recorder._update_symlink(target)
        self.mock_remove.assert_called_once_with(self.symlink_file_path)
        self.mock_symlink.assert_called_once_with(target, self.symlink_file_path)

    def test_update_symlink_failure(self):
        """Test _update_symlink when symlink fails."""
        self.mock_symlink.side_effect = OSError
        target = '/tmp/fail_link.json'
        with self.assertLogs(level=logging.WARNING):
            self.simple_recorder._update_symlink(target)
        self.mock_remove.assert_called_once_with(self.symlink_file_path)
        self.mock_symlink.assert_called_once_with(target, self.symlink_file_path)

    def test_dump_state(self):
        """Test dump_state method in the successful case."""
        self.set_up_state_recorder_method_mocks()
        self.simple_recorder.dump_state()
        self.mock_makedirs.assert_called_once_with(self.simple_recorder.dir_path, exist_ok=True)
        self.method_order_tracker.assert_has_calls([
            call._create_new_file(),
            call._update_symlink(self.mock_create_new_file.return_value),
            call._remove_old_files()
        ])
        self.mock_open.assert_called_once_with(self.mock_create_new_file.return_value, 'w')
        self.mock_json_dump.assert_called_once_with(SimpleRecorder.CONST_DATA,
                                                    self.mock_open.return_value.__enter__.return_value)

    def test_dump_state_makedirs_file_exists(self):
        """Test dump_state method when the dir or a leading part of the path is a file."""
        self.set_up_state_recorder_method_mocks()
        for err in [FileExistsError, NotADirectoryError]:
            self.mock_makedirs.side_effect = err
            with self.assertRaisesRegex(StateError, 'is not a directory'):
                self.simple_recorder.dump_state()

        self.mock_makedirs.assert_called_with(self.simple_recorder.dir_path, exist_ok=True)
        self.assertEqual([], self.method_order_tracker.mock_calls)
        self.mock_open.assert_not_called()
        self.mock_json_dump.assert_not_called()

    def test_dump_state_makedirs_failure(self):
        """Test dump_state method when it fails to create the dir."""
        self.set_up_state_recorder_method_mocks()
        self.mock_makedirs.side_effect = OSError
        with self.assertRaisesRegex(StateError, f'Failed to ensure state directory {self.dir_path} exists'):
            self.simple_recorder.dump_state()

        self.mock_makedirs.assert_called_once_with(self.simple_recorder.dir_path, exist_ok=True)
        self.assertEqual([], self.method_order_tracker.mock_calls)
        self.mock_open.assert_not_called()
        self.mock_json_dump.assert_not_called()

    def test_dump_state_file_open_failure(self):
        """Test dump_state when it fails to open the file to write to."""
        self.set_up_state_recorder_method_mocks()
        self.mock_open.side_effect = OSError

        with self.assertRaisesRegex(StateError, 'Failed to write pod state to file'):
            self.simple_recorder.dump_state()

        self.mock_create_new_file.assert_called_once_with()
        self.mock_update_symlink.assert_not_called()
        self.mock_remove_old_files.assert_not_called()
        self.mock_open.assert_called_once_with(self.mock_create_new_file.return_value, 'w')
        self.mock_json_dump.assert_not_called()

    def test_get_stored_state(self):
        """Test get_stored_state method in the successful case."""
        stored_state = self.simple_recorder.get_stored_state()

        self.assertEqual(self.mock_json_load.return_value, stored_state)
        self.mock_open.assert_called_once_with(self.simple_recorder.symlink_file_path)
        self.mock_json_load.assert_called_once_with(self.mock_open.return_value.__enter__.return_value)

    def test_get_stored_state_os_error(self):
        """Test get_stored_state method when fails to open file."""
        self.mock_open.side_effect = OSError

        with self.assertRaisesRegex(StateError, 'Failed to open file'):
            self.simple_recorder.get_stored_state()

        self.mock_open.assert_called_once_with(self.simple_recorder.symlink_file_path)
        self.mock_json_load.assert_not_called()

    def test_get_stored_state_json_error(self):
        """Test get_stored_state method when fails to parse JSON from file data."""
        self.mock_json_load.side_effect = ValueError

        with self.assertRaisesRegex(StateError, 'Failed to parse JSON'):
            self.simple_recorder.get_stored_state()

        self.mock_open.assert_called_once_with(self.simple_recorder.symlink_file_path)
        self.mock_json_load.assert_called_once_with(self.mock_open.return_value.__enter__.return_value)


def get_fake_pod_list(pods):
    """Get a mock object that looks like a V1PodList.

    Args:
        pods (list): A list of tuples where each tuple has the following three
            components:
                (namespace, name, phase)
    """
    v1_pod_list = Mock()
    v1_pod_list.items = []
    for pod in pods:
        mock_pod = Mock()
        mock_pod.metadata.namespace = pod[0]
        mock_pod.metadata.name = pod[1]
        mock_pod.status.phase = pod[2]
        v1_pod_list.items.append(mock_pod)
    return v1_pod_list


class TestPodStateRecorder(unittest.TestCase):
    """Test the PodStateRecorder class."""

    def setUp(self):
        """Set up mocks."""
        self.max_pod_states = 10
        self.mock_get_config_value = patch('sat.cli.bootsys.state_recorder.get_config_value').start()
        self.mock_get_config_value.return_value = self.max_pod_states

        self.mock_load_kube_config = patch('sat.cli.bootsys.state_recorder.load_kube_config').start()
        self.mock_pods = get_fake_pod_list([
            ('services', 'boa', 'complete'),
            ('services', 'cfs', 'complete'),
            ('sma', 'sma-cstream', 'initializing'),
            ('user', 'uai', 'running')
        ])
        self.mock_k8s_api = patch('sat.cli.bootsys.state_recorder.CoreV1Api').start()
        self.mock_k8s_client = self.mock_k8s_api.return_value
        self.mock_k8s_client.list_pod_for_all_namespaces.return_value = self.mock_pods

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of a new PodStateRecorder."""
        psr = PodStateRecorder()
        self.mock_get_config_value.assert_called_once_with('bootsys.max_pod_states')
        self.assertEqual(psr.dir_path, '/var/sat/bootsys/pod-states/')
        self.assertEqual(psr.file_prefix, 'pod-states')
        self.assertEqual(psr.file_suffix, '.json')
        self.assertEqual(psr.num_to_keep, self.max_pod_states)

    def test_get_state_data(self):
        """Test the successful case for get_state_data."""
        psr = PodStateRecorder()
        expected = {
            'services': {
                'boa': 'complete',
                'cfs': 'complete'
            },
            'sma': {
                'sma-cstream': 'initializing'
            },
            'user': {
                'uai': 'running'
            }
        }
        state_data = dict(psr.get_state_data())
        self.assertEqual(expected, state_data)

    def test_get_state_data_kube_config_not_found(self):
        """Test get_state_data with a FileNotFoundError when loading k8s config."""
        self.mock_load_kube_config.side_effect = FileNotFoundError

        with self.assertRaisesRegex(PodStateError, 'Failed to load kubernetes config'):
            PodStateRecorder().get_state_data()

    def test_get_state_data_kube_config_err(self):
        """Test get_state_data with a ConfigException when loading k8s config."""
        self.mock_load_kube_config.side_effect = ConfigException

        with self.assertRaisesRegex(PodStateError, 'Failed to load kubernetes config'):
            PodStateRecorder().get_state_data()


class TestHSNStateRecorder(unittest.TestCase):
    """Test the HSNStateRecorder class."""

    def setUp(self):
        """Set up mocks."""
        self.max_hsn_states = 10
        self.mock_get_config_value = patch('sat.cli.bootsys.state_recorder.get_config_value').start()
        self.mock_get_config_value.return_value = self.max_hsn_states

        patch('sat.cli.bootsys.state_recorder.SATSession').start()
        mock_fc_class = patch('sat.cli.bootsys.state_recorder.FabricControllerClient').start()
        self.mock_fc_client = mock_fc_class.return_value

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of a new HSNStateRecorder."""
        hsr = HSNStateRecorder()
        self.mock_get_config_value.assert_called_once_with('bootsys.max_hsn_states')
        self.assertEqual(hsr.dir_path, '/var/sat/bootsys/hsn-states/')
        self.assertEqual(hsr.file_prefix, 'hsn-state')
        self.assertEqual(hsr.file_suffix, '.json')
        self.assertEqual(hsr.num_to_keep, self.max_hsn_states)

    def test_get_state_data(self):
        """Test the successful case for get_state_data."""
        hsr = HSNStateRecorder()
        state_data = hsr.get_state_data()
        self.assertEqual(self.mock_fc_client.get_fabric_edge_ports_enabled_status.return_value,
                         state_data)


if __name__ == '__main__':
    unittest.main()
