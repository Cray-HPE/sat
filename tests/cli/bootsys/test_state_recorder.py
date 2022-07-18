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
Unit tests for the service_activity module.
"""
from boto3.exceptions import Boto3Error
from kubernetes.config import ConfigException
import datetime
import os
import unittest
from unittest.mock import call, patch, Mock

from sat.cli.bootsys.defaults import DEFAULT_LOCAL_STATE_DIR
from sat.cli.bootsys.state_recorder import (
    HSNStateRecorder,
    PodStateError, PodStateRecorder,
    StateError, StateRecorder,
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
        self.dir_path = 'states'
        self.file_prefix = 'simple'
        self.num_to_keep = 5
        self.file_suffix = '.json'
        self.mock_s3 = Mock()
        self.bucket_name = 'sat'

        self.simple_recorder = SimpleRecorder(
            self.dir_path, self.file_prefix, self.num_to_keep, self.mock_s3, self.bucket_name
        )

        self.mock_s3_bucket = self.mock_s3.Bucket.return_value
        self.bucket_files = [
            Mock(key='states/simple.2020-09-07T18:05:14.json',
                 last_modified=datetime.datetime(2020, 9, 7, 18, 5, 14, 266170))
        ]
        self.mock_s3_bucket.objects.filter.return_value = self.bucket_files

        self.mock_open = patch('builtins.open').start()
        self.mock_date_str = '2020-09-07T18:05:14'
        self.expected_new_file_name = os.path.join(
            self.dir_path, f'{self.file_prefix}.{self.mock_date_str}{self.file_suffix}'
        )
        self.expected_local_new_file_name = os.path.join(
            DEFAULT_LOCAL_STATE_DIR, self.expected_new_file_name
        )
        self.mock_datetime = patch('sat.cli.bootsys.state_recorder.datetime').start()
        self.mock_utcnow = Mock()
        self.mock_datetime.utcnow = self.mock_utcnow
        self.mock_utcnow.return_value.strftime.return_value = self.mock_date_str

        self.local_dir_path = os.path.join(DEFAULT_LOCAL_STATE_DIR, self.dir_path)
        self.mock_remove = patch('os.remove').start()
        self.mock_makedirs = patch('os.makedirs').start()
        self.mock_json_dump = patch('json.dump').start()
        self.mock_json_load = patch('json.load').start()

    def tearDown(self):
        """Stop all mock patches."""
        patch.stopall()

    def set_up_mock_create_new_file(self):
        """Mock some of the StateRecorder methods to help test higher-level methods."""
        self.mock_create_new_file = patch('sat.cli.bootsys.state_recorder.StateRecorder._create_new_file').start()
        self.mock_create_new_file.return_value = self.expected_new_file_name

    def assert_instance_variables(self):
        """Check that self.simple_recorder has the expected instance variables"""
        self.assertEqual(self.dir_path, self.simple_recorder.dir_path)
        self.assertEqual(self.file_prefix, self.simple_recorder.file_prefix)
        self.assertEqual(self.num_to_keep, self.simple_recorder.num_to_keep)
        self.assertEqual(self.file_suffix, self.simple_recorder.file_suffix)
        self.assertEqual(self.mock_s3, self.simple_recorder.s3)
        self.assertEqual(self.bucket_name, self.simple_recorder.bucket_name)

    def test_init(self):
        """Test instantiation of a simple subclass of StateRecorder."""
        self.assert_instance_variables()

    def test_init_non_default_values(self):
        """Test instantiation of a simple subclass of StateRecorder with non-default num_to_keep and suffix"""
        self.num_to_keep = 10
        self.file_suffix = '.yaml'
        self.simple_recorder = SimpleRecorder(
            self.dir_path, self.file_prefix, self.num_to_keep, self.mock_s3, self.bucket_name, self.file_suffix
        )
        self.assert_instance_variables()

    def test_remove_old_files_none(self):
        """Test _remove_old_files with no files removes no files."""
        self.mock_s3_bucket.objects.filter.return_value = []
        self.simple_recorder._remove_old_files()
        self.mock_s3.Bucket.assert_called_with(self.bucket_name)
        self.mock_s3.Bucket.return_value.objects.filter.assert_called_with(Prefix=self.dir_path)
        self.mock_s3.Object.return_value.delete.assert_not_called()

    def test_remove_old_files_below_limit(self):
        """Test _remove_old_files with the number of files below the limit removes no files."""
        self.simple_recorder._remove_old_files()
        self.mock_s3.Bucket.assert_called_with(self.bucket_name)
        self.mock_s3.Bucket.return_value.objects.filter.assert_called_with(Prefix=self.dir_path)
        self.mock_s3.Object.return_value.delete.assert_not_called()

    def test_remove_old_files_at_limit(self):
        """Test _remove_old_files with the number of files at the limit removes no files."""
        bucket_files = [
            Mock(key=f'states/simple.2020-09-07T18:0{i}:14.json',
                 last_modified=datetime.datetime(2020, 9, 7, 18, i, 14, 266170))
            for i in range(self.num_to_keep)
        ]
        self.mock_s3_bucket.objects.filter.return_value = bucket_files
        self.simple_recorder._remove_old_files()
        self.mock_s3.Bucket.assert_called_with(self.bucket_name)
        self.mock_s3.Bucket.return_value.objects.filter.assert_called_with(Prefix=self.dir_path)
        self.mock_s3.Object.return_value.delete.assert_not_called()

    def test_remove_old_files_over_limit(self):
        """Test _remove_old_files with the number of files over the limit."""
        bucket_files = [
            Mock(key=f'states/simple.2020-09-07T18:0{i}:14.json',
                 last_modified=datetime.datetime(2020, 9, 7, 18, i, 14, 266170))
            for i in range(self.num_to_keep + 1)
        ]
        self.mock_s3.Bucket.return_value.objects.filter.return_value = bucket_files
        self.simple_recorder._remove_old_files()
        self.mock_s3.Bucket.assert_called_with(self.bucket_name)
        self.mock_s3.Bucket.return_value.objects.filter.assert_called_with(Prefix=self.dir_path)
        self.mock_s3.Object.return_value.delete.called_once_with(bucket_files[0])

    def test_remove_old_files_s3_list_error(self):
        """Test _remove_old_files when S3 can't list files raises a StateError."""
        self.mock_s3.Bucket.return_value.objects.filter.side_effect = Boto3Error
        with self.assertRaisesRegex(StateError, 'Unable to list files in S3 Bucket'):
            self.simple_recorder._remove_old_files()
        self.mock_s3.Bucket.assert_called_with(self.bucket_name)
        self.mock_s3.Bucket.return_value.objects.filter.assert_called_with(Prefix=self.dir_path)
        self.mock_s3.Object.return_value.delete.assert_not_called()

    def test_remove_old_files_irrelevant_file(self):
        """Test _remove_old_files under the limit but with an extra file that should be ignored"""
        bucket_files = [
            Mock(key=f'states/simple.2020-09-07T18:0{i}:14.json',
                 last_modified=datetime.datetime(2020, 9, 7, 18, i, 14, 266170))
            for i in range(self.num_to_keep)] + [
            Mock(key='some-other-file',
                 last_modified=datetime.datetime(2018, 9, 7, 19, 0, 14, 266170))
            ]
        self.mock_s3_bucket.objects.filter.return_value = bucket_files
        self.simple_recorder._remove_old_files()
        self.mock_s3.Bucket.assert_called_with(self.bucket_name)
        self.mock_s3.Bucket.return_value.objects.filter.assert_called_with(Prefix=self.dir_path)
        self.mock_s3.Object.return_value.delete.assert_not_called()

    def test_create_new_file_success(self):
        """Test _create_new_file in the successful case."""
        self.simple_recorder._create_new_file()
        self.mock_open.assert_called_once_with(self.expected_local_new_file_name, 'w')
        self.mock_open.return_value.__enter__.return_value.write.assert_called_once_with('')

    def test_create_new_file_open_failure(self):
        """Test _create_new_file when open fails."""
        self.mock_open.side_effect = OSError
        with self.assertRaises(StateError):
            self.simple_recorder._create_new_file()
        self.mock_open.assert_called_once_with(self.expected_local_new_file_name, 'w')
        self.mock_open.return_value.__enter__.assert_not_called()

    def test_create_new_file_write_failure(self):
        """Test _create_new_file when write fails."""
        self.mock_open.return_value.__enter__.return_value.write.side_effect = OSError
        with self.assertRaises(StateError):
            self.simple_recorder._create_new_file()
        self.mock_open.assert_called_once_with(
            self.expected_local_new_file_name, 'w'
        )
        self.mock_open.return_value.__enter__.return_value.write.assert_called_once_with('')

    def test_dump_state(self):
        """Test dump_state method in the successful case."""
        self.set_up_mock_create_new_file()
        self.simple_recorder.dump_state()
        self.mock_makedirs.assert_called_once_with(self.local_dir_path, exist_ok=True)
        self.mock_create_new_file.assert_called_once_with()
        self.mock_open.assert_called_once_with(self.expected_local_new_file_name, 'w')
        self.mock_s3.Object.assert_called_once_with(self.bucket_name, self.expected_new_file_name)
        self.mock_s3.Object.return_value.upload_file.assert_called_once_with(self.expected_local_new_file_name)
        self.mock_remove.assert_called_once_with(self.expected_local_new_file_name)
        self.mock_json_dump.assert_called_once_with(SimpleRecorder.CONST_DATA,
                                                    self.mock_open.return_value.__enter__.return_value)

    def test_dump_state_makedirs_file_exists(self):
        """Test dump_state method when the dir or a leading part of the path is a file."""
        self.set_up_mock_create_new_file()
        for err in [FileExistsError, NotADirectoryError]:
            self.mock_makedirs.side_effect = err
            with self.assertRaisesRegex(StateError, 'is not a directory'):
                self.simple_recorder.dump_state()

        self.mock_makedirs.assert_called_with(self.local_dir_path, exist_ok=True)
        self.mock_create_new_file.assert_not_called()
        self.mock_open.assert_not_called()
        self.mock_json_dump.assert_not_called()
        self.mock_s3.Object.assert_not_called()

    def test_dump_state_makedirs_failure(self):
        """Test dump_state method when it fails to create the dir."""
        self.set_up_mock_create_new_file()
        self.mock_makedirs.side_effect = OSError
        with self.assertRaisesRegex(StateError, f'Failed to ensure state directory {self.local_dir_path} exists'):
            self.simple_recorder.dump_state()
        self.mock_makedirs.assert_called_once_with(self.local_dir_path, exist_ok=True)
        self.mock_create_new_file.assert_not_called()
        self.mock_open.assert_not_called()
        self.mock_json_dump.assert_not_called()
        self.mock_s3.Object.assert_not_called()

    def test_dump_state_file_open_failure(self):
        """Test dump_state when it fails to open the file to write to."""
        self.set_up_mock_create_new_file()
        self.mock_open.side_effect = OSError

        with self.assertRaisesRegex(StateError, 'Failed to write state to file'):
            self.simple_recorder.dump_state()

        self.mock_makedirs.assert_called_once_with(self.local_dir_path, exist_ok=True)
        self.mock_create_new_file.assert_called_once_with()
        self.mock_json_dump.assert_not_called()
        self.mock_s3.Object.assert_not_called()
        self.mock_open.assert_called_once_with(self.expected_local_new_file_name, 'w')
        self.mock_json_dump.assert_not_called()

    def test_dump_state_s3_dump_error(self):
        """Test dump_state when uploading to S3 fails raises a StateError"""
        self.set_up_mock_create_new_file()
        self.mock_s3.Object.return_value.upload_file.side_effect = Boto3Error
        with self.assertRaisesRegex(StateError, 'Failed to dump state to S3'):
            self.simple_recorder.dump_state()
        self.mock_makedirs.assert_called_once_with(self.local_dir_path, exist_ok=True)
        self.mock_create_new_file.assert_called_once_with()
        self.mock_open.assert_called_once_with(self.expected_local_new_file_name, 'w')
        self.mock_s3.Object.assert_called_once_with(self.bucket_name, self.expected_new_file_name)
        self.mock_json_dump.assert_called_once_with(SimpleRecorder.CONST_DATA,
                                                    self.mock_open.return_value.__enter__.return_value)
        self.mock_remove.assert_called_once_with(self.expected_local_new_file_name)

    def test_get_stored_state(self):
        """Test get_stored_state method in the successful case."""
        bucket_files = [
            Mock(key=f'states/simple.2020-09-07T18:0{i}:14.json',
                 last_modified=datetime.datetime(2020, 9, 7, 18, i, 14, 266170))
            for i in range(5)
        ]
        self.mock_s3_bucket.objects.filter.return_value = bucket_files
        expected_latest_file = bucket_files[-1].key
        expected_local_path = os.path.join(DEFAULT_LOCAL_STATE_DIR, expected_latest_file)

        stored_state = self.simple_recorder.get_stored_state()

        # Assert file was downloaded from S3
        self.mock_s3_bucket.objects.filter.assert_called_once_with(Prefix=self.dir_path)
        self.mock_s3.Object.assert_called_once_with(self.bucket_name, expected_latest_file)
        self.mock_s3.Object.return_value.download_file.assert_called_once_with(expected_local_path)

        # Assert file was saved locally and opened
        self.mock_makedirs.assert_called_once_with(self.local_dir_path, exist_ok=True)
        self.assertEqual(self.mock_json_load.return_value, stored_state)
        self.mock_open.assert_called_once_with(expected_local_path)
        self.mock_json_load.assert_called_once_with(self.mock_open.return_value.__enter__.return_value)
        self.mock_remove.assert_called_once_with(expected_local_path)

    def test_get_stored_state_no_state(self):
        """Test get_stored_state when no files are returned from S3."""
        self.mock_s3_bucket.objects.filter.return_value = []
        with self.assertRaisesRegex(StateError, 'No stored state found'):
            self.simple_recorder.get_stored_state()
        self.mock_s3_bucket.objects.filter.assert_called_once_with(Prefix=self.dir_path)
        self.mock_open.assert_not_called()
        self.mock_json_load.assert_not_called()
        self.mock_remove.assert_not_called()

    def test_get_stored_state_irrelevant_file(self):
        """Test get_stored state when a file exists but should be ignored."""
        bucket_files = [
            Mock(key=f'states/some-random-file.json',
                 last_modified=datetime.datetime(2020, 9, 7, 18, 0, 14, 266170))
        ]
        self.mock_s3_bucket.objects.filter.return_value = bucket_files
        with self.assertRaisesRegex(StateError, 'No stored state found'):
            self.simple_recorder.get_stored_state()
        self.mock_s3_bucket.objects.filter.assert_called_once_with(Prefix=self.dir_path)
        self.mock_open.assert_not_called()
        self.mock_json_load.assert_not_called()
        self.mock_remove.assert_not_called()

    def test_get_stored_state_os_error(self):
        """Test get_stored_state method when fails to open file."""
        self.mock_open.side_effect = OSError
        expected_local_file = os.path.join(
            DEFAULT_LOCAL_STATE_DIR, self.bucket_files[0].key
        )

        with self.assertRaisesRegex(StateError, 'Failed to open downloaded file'):
            self.simple_recorder.get_stored_state()

        self.mock_open.assert_called_once_with(expected_local_file)
        self.mock_json_load.assert_not_called()
        self.mock_remove.assert_called_once_with(expected_local_file)

    def test_get_stored_state_json_error(self):
        """Test get_stored_state method when fails to parse JSON from file data."""
        self.mock_json_load.side_effect = ValueError
        expected_local_file = os.path.join(
            DEFAULT_LOCAL_STATE_DIR, self.bucket_files[0].key
        )

        with self.assertRaisesRegex(StateError, 'Failed to parse JSON from downloaded file'):
            self.simple_recorder.get_stored_state()

        self.mock_open.assert_called_once_with(expected_local_file)
        self.mock_json_load.assert_called_once_with(self.mock_open.return_value.__enter__.return_value)
        self.mock_remove.assert_called_once_with(expected_local_file)

    def test_get_stored_state_s3_list_error(self):
        """Test get_stored_state when S3 can't list files raises a StateError."""
        self.mock_s3_bucket.objects.filter.side_effect = Boto3Error

        with self.assertRaisesRegex(StateError, 'Unable to list files in S3 Bucket'):
            self.simple_recorder.get_stored_state()
        self.mock_remove.assert_not_called()

    def test_get_stored_state_s3_download_error(self):
        """Test get_stored_state when S3 can't download a file raises a StateError."""
        self.mock_s3.Object.return_value.download_file.side_effect = Boto3Error

        with self.assertRaisesRegex(StateError, 'Unable to download'):
            self.simple_recorder.get_stored_state()
        self.mock_remove.assert_not_called()


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
        self.fake_config = {
            'bootsys': {
                'max_pod_states': 10,
            },
            's3': {
                'bucket': 'sat'
            }
        }
        self.mock_get_config_value = patch('sat.cli.bootsys.state_recorder.get_config_value',
                                           side_effect=self.fake_get_config_value).start()
        self.mock_s3 = patch('sat.cli.bootsys.state_recorder.get_s3_resource').start().return_value

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

    def fake_get_config_value(self, query_string):
        """Mock the behavior of get_config_value"""
        section, value = query_string.split('.')
        return self.fake_config[section][value]

    def test_init(self):
        """Test creation of a new PodStateRecorder."""
        psr = PodStateRecorder()
        self.assertEqual(
            [call('bootsys.max_pod_states'), call('s3.bucket')],
            self.mock_get_config_value.mock_calls
        )
        self.assertEqual(psr.dir_path, 'pod-states/')
        self.assertEqual(psr.file_prefix, 'pod-states')
        self.assertEqual(psr.file_suffix, '.json')
        self.assertEqual(psr.num_to_keep, self.fake_config['bootsys']['max_pod_states'])
        self.assertEqual(psr.bucket_name, self.fake_config['s3']['bucket'])
        self.assertEqual(psr.s3, self.mock_s3)

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
        self.fake_config = {
            'bootsys': {
                'max_hsn_states': 10,
            },
            's3': {
                'bucket': 'sat'
            }
        }
        self.mock_get_config_value = patch('sat.cli.bootsys.state_recorder.get_config_value',
                                           side_effect=self.fake_get_config_value).start()
        self.mock_s3 = patch('sat.cli.bootsys.state_recorder.get_s3_resource').start().return_value

        patch('sat.cli.bootsys.state_recorder.SATSession').start()
        mock_fc_class = patch('sat.cli.bootsys.state_recorder.FabricControllerClient').start()
        self.mock_fc_client = mock_fc_class.return_value

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def fake_get_config_value(self, query_string):
        """Mock the behavior of get_config_value"""
        section, value = query_string.split('.')
        return self.fake_config[section][value]

    def test_init(self):
        """Test creation of a new HSNStateRecorder."""
        hsr = HSNStateRecorder()
        self.assertEqual(
            [call('bootsys.max_hsn_states'), call('s3.bucket')],
            self.mock_get_config_value.mock_calls
        )
        self.assertEqual(hsr.dir_path, 'hsn-states/')
        self.assertEqual(hsr.file_prefix, 'hsn-state')
        self.assertEqual(hsr.file_suffix, '.json')
        self.assertEqual(hsr.num_to_keep, self.fake_config['bootsys']['max_hsn_states'])
        self.assertEqual(hsr.bucket_name, self.fake_config['s3']['bucket'])
        self.assertEqual(hsr.s3, self.mock_s3)

    def test_get_state_data(self):
        """Test the successful case for get_state_data."""
        hsr = HSNStateRecorder()
        state_data = hsr.get_state_data()
        self.assertEqual(self.mock_fc_client.get_fabric_edge_ports_enabled_status.return_value,
                         state_data)


if __name__ == '__main__':
    unittest.main()
