#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Tests for sat.cli.bootprep.configuration
"""
from argparse import Namespace
import logging
import os
import unittest
from unittest.mock import patch, Mock

from sat.apiclient import APIError
from sat.cli.bootprep.configuration import (
    create_configurations,
    handle_existing_configs
)
from sat.cli.bootprep.errors import ConfigurationCreateError


class TestHandleExistingConfigs(unittest.TestCase):
    """Tests for handle_existing_configs function"""

    def setUp(self):
        """Mock CFSClient, mock CFSConfigurations, args, and Mock pester_choices"""
        self.set_up_cfs_configs(['compute-1.4.2', 'uan-1.4.2'])
        self.set_up_input_configs(['compute-1.5.0', 'uan-1.5.0'])

        self.args = Namespace(dry_run=False, overwrite_configs=False,
                              skip_existing_configs=False, resolve_branches=False)

        self.mock_pester = patch('sat.cli.bootprep.configuration.pester_choices').start()
        self.mock_pester.return_value = 'abort'

    def tearDown(self):
        patch.stopall()

    def set_up_cfs_configs(self, cfs_config_names):
        """Set up existing configs in CFS with the given names

        Args:
            cfs_config_names (list of str): names to set for config data returned by
                self.cfs_client.get_configurations
        """
        self.cfs_config_names = cfs_config_names
        self.cfs_client = Mock()
        self.cfs_client.get_configurations.return_value = [{'name': name}
                                                           for name in self.cfs_config_names]

    def set_up_input_configs(self, input_config_names):
        """Set up input configs with the given names

        Args:
            input_config_names (list of str): list of names to set for self.input_configs
        """
        self.input_config_names = input_config_names
        self.input_configs = []
        for name in self.input_config_names:
            input_config = Mock()
            # name kwarg has special meaning in Mock constructor, so it must be set this way
            input_config.name = name
            self.input_configs.append(input_config)

    def assert_pester_choices_called(self, existing_configs):
        """Assert the pester_choices function was called

        Args:
            existing_configs (list of str): list of existing config names mentioned
                in the pester_choices prompt
        """
        self.mock_pester.assert_called_once()
        # We are asserting on the first and only call. Each call is a 3-tuple of
        # (name, args, kwargs). Get just the first of the args of the first call
        call_arg = self.mock_pester.mock_calls[0][1][0]
        # Just assert the variable part of the message to avoid having to change this
        # assert if the message changes slightly.
        self.assertIn(f'exist: {", ".join(existing_configs)}.', call_arg)

    def test_no_overlapping_configs(self):
        """Test handle_existing_configs when no input configs already exist"""
        configs_to_create = handle_existing_configs(self.cfs_client, self.input_configs, self.args)
        self.assertEqual(self.input_configs, configs_to_create)

    def test_cfs_query_failed(self):
        """Test handle_existing_configs when the CFS request fails"""
        cfs_client = Mock()
        cfs_err_msg = 'unable to get configs'
        cfs_client.get_configurations.side_effect = APIError(cfs_err_msg)
        err_regex = f'Failed to query CFS for existing configurations: {cfs_err_msg}'
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            handle_existing_configs(cfs_client, self.input_configs, self.args)

    def test_overlapping_configs_prompt_abort(self):
        """Test handle_existing_configs when input configs exist, and the user aborts"""
        # Fully overlap with existing CFS configs
        self.set_up_input_configs(self.cfs_config_names)
        self.mock_pester.return_value = 'abort'
        err_regex = 'User chose to abort'
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            handle_existing_configs(self.cfs_client, self.input_configs, self.args)
        self.assert_pester_choices_called(self.input_config_names)

    def set_up_overlapping_configs(self):
        """Set up input configs and existing configs such that two of four overlap"""
        new_config_names = ['new-1', 'new-2']
        existing_config_names = ['old-1', 'old-2']
        # Overlap two of the four configs
        input_config_names = [new_config_names[0], existing_config_names[0],
                              new_config_names[1], existing_config_names[1]]
        self.set_up_input_configs(input_config_names)
        self.set_up_cfs_configs(existing_config_names)

    def test_overlapping_configs_prompt_skip(self):
        """Test handle_existing_configs when input configs exist, and user skips them"""
        self.set_up_overlapping_configs()
        self.mock_pester.return_value = 'skip'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            configs_to_create = handle_existing_configs(self.cfs_client, self.input_configs, self.args)
        self.assertEqual([self.input_configs[0], self.input_configs[2]],
                         configs_to_create)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(logs_cm.records[0].message,
                         f'The following CFS configurations already exist '
                         f'and will be skipped: {", ".join(self.cfs_config_names)}')

    def test_overlapping_configs_prompt_overwrite(self):
        """Test handle_existing_configs when input configs exist, and user overwrites them"""
        self.set_up_overlapping_configs()
        self.mock_pester.return_value = 'overwrite'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            configs_to_create = handle_existing_configs(self.cfs_client, self.input_configs, self.args)
        self.assertEqual(self.input_configs, configs_to_create)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(logs_cm.records[0].message,
                         f'The following CFS configurations already exist '
                         f'and will be overwritten: {", ".join(self.cfs_config_names)}')

    def test_overlapping_configs_args_skip(self):
        """Test handle_existing_configs when input configs exist, and args skips them"""
        self.set_up_overlapping_configs()
        self.args.skip_existing_configs = True
        with self.assertLogs(level=logging.INFO) as logs_cm:
            configs_to_create = handle_existing_configs(self.cfs_client, self.input_configs, self.args)
        self.assertEqual([self.input_configs[0], self.input_configs[2]],
                         configs_to_create)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(logs_cm.records[0].message,
                         f'The following CFS configurations already exist '
                         f'and will be skipped: {", ".join(self.cfs_config_names)}')

    def test_overlapping_configs_args_overwrite(self):
        """Test handle_existing_configs when input configs exist, and args overwrites them"""
        self.set_up_overlapping_configs()
        self.args.overwrite_configs = True
        with self.assertLogs(level=logging.INFO) as logs_cm:
            configs_to_create = handle_existing_configs(self.cfs_client, self.input_configs, self.args)
        self.assertEqual(self.input_configs, configs_to_create)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(logs_cm.records[0].message,
                         f'The following CFS configurations already exist '
                         f'and will be overwritten: {", ".join(self.cfs_config_names)}')

    def test_overlapping_configs_args_skip_dry_run(self):
        """Test handle_existing_configs when input configs exists, args skips and is dry-run"""
        self.set_up_overlapping_configs()
        self.args.skip_existing_configs = True
        self.args.dry_run = True
        with self.assertLogs(level=logging.INFO) as logs_cm:
            configs_to_create = handle_existing_configs(self.cfs_client, self.input_configs, self.args)
        self.assertEqual([self.input_configs[0], self.input_configs[2]],
                         configs_to_create)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(logs_cm.records[0].message,
                         f'The following CFS configurations already exist '
                         f'and would be skipped: {", ".join(self.cfs_config_names)}')


class TestCreateCFSConfigurations(unittest.TestCase):
    """Tests for the create_configurations function"""

    def setUp(self):
        """Mock InputConfiguration, CFSClient, SATSession, open, json.dump; create args"""

        self.config_names = ['compute-1.4.2', 'uan-1.4.2']
        self.instance_data = {
            'configurations': [{'name': name, 'layers': []} for name in self.config_names]
        }

        self.mock_cfs_configs = []
        for config_name in self.config_names:
            mock_cfs_config = Mock()
            mock_cfs_config.name = config_name
            self.mock_cfs_configs.append(mock_cfs_config)
        self.mock_instance = Mock(input_configurations=self.mock_cfs_configs)

        self.mock_session = patch('sat.cli.bootprep.configuration.SATSession').start()
        self.mock_cfs_client_cls = patch('sat.cli.bootprep.configuration.CFSClient').start()
        self.mock_cfs_client = self.mock_cfs_client_cls.return_value

        def mock_handle_existing(*args):
            """A mock handle_existing_configs that just returns all the input_configs"""
            return args[1]

        self.mock_handle_existing_configs = patch(
            'sat.cli.bootprep.configuration.handle_existing_configs').start()
        self.mock_handle_existing_configs.side_effect = mock_handle_existing

        self.mock_file_objects = {
            f'cfs-config-{config_name}.json': Mock()
            for config_name in self.config_names
        }

        self.mock_req_dumper = patch('sat.cli.bootprep.configuration.RequestDumper').start()

        self.args = Namespace(dry_run=False, save_files=True, output_dir='output',
                              resolve_branches=False, action='run')

    def tearDown(self):
        patch.stopall()

    def assert_no_action_taken(self, logs_cm):
        """Helper assertion for asserting no action is taken

        Args:
            logs_cm: context manager from self.assertLogs
        """
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual('Given input did not define any CFS configurations',
                         logs_cm.records[0].message)
        self.mock_session.assert_not_called()
        self.mock_cfs_client_cls.assert_not_called()
        self.mock_handle_existing_configs.assert_not_called()

    def assert_cfs_client_created(self):
        """Helper to assert CFS client creation"""
        self.mock_session.assert_called_once_with()
        self.mock_cfs_client_cls.assert_called_once_with(self.mock_session.return_value)

    def assert_config_dumped_to_file(self, config):
        """Assert the given config was dumped to a file

        Args:
            config (Mock): A Mock object representing a InputConfiguration
        """
        self.mock_req_dumper.return_value.write_request_body.assert_any_call(
            config.name, config.get_cfs_api_data.return_value
        )

    def assert_config_put_to_cfs(self, config):
        """Assert the given config was PUT to CFS

        Args:
            config (Mock): A mock object representing a InputConfiguration
        """
        self.mock_cfs_client.put_configuration.assert_any_call(
            config.name,
            config.get_cfs_api_data.return_value
        )

    def test_create_cfs_configurations_no_configurations(self):
        """Test create_configurations when instance contains no configurations"""
        instance = Mock(input_configurations=[])
        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_configurations(instance, self.args)
        self.assert_no_action_taken(logs_cm)

    def get_expected_file_path(self, config):
        """Get the expected file path for a config."""
        return os.path.join(self.args.output_dir, f'cfs-config-{config.name}.json')

    def get_expected_info_logs(self, configs, dry_run=False):
        """Get a list of expected info log messages for successfully created configs

        configs (list of Mock): mock CFSConfigurations which should have successful
            info log messages
        dry_run (bool): whether messages should be for a dry run or not
        """
        expected_logs = []
        for config in configs:
            expected_logs.append(f'{("Creating", "Would create")[dry_run]} '
                                 f'CFS configuration with name "{config.name}"')
        return expected_logs

    def test_create_cfs_configurations_success(self):
        """Test create_configurations in default, successful path"""
        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_configurations(self.mock_instance, self.args)

        self.assert_cfs_client_created()
        self.mock_handle_existing_configs.assert_called_once_with(
            self.mock_cfs_client, self.mock_cfs_configs, self.args
        )
        for config in self.mock_cfs_configs:
            self.assert_config_dumped_to_file(config)
            self.assert_config_put_to_cfs(config)
        expected_logs = [
            f'Creating {len(self.mock_cfs_configs)} CFS configuration(s)',
        ] + self.get_expected_info_logs(self.mock_cfs_configs)
        self.assertEqual(expected_logs, [rec.message for rec in logs_cm.records])

    def test_create_cfs_configurations_one_cfs_data_failure(self):
        """Test create_configurations when one fails in its get_cfs_api_data method"""
        create_err = 'failed to get CFS API data'
        self.mock_cfs_configs[0].get_cfs_api_data.side_effect = ConfigurationCreateError(create_err)
        err_regex = r'Failed to create 1 configuration\(s\)'

        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            with self.assertLogs(level=logging.INFO) as logs_cm:
                create_configurations(self.mock_instance, self.args)

        self.assert_cfs_client_created()
        self.mock_handle_existing_configs.assert_called_once_with(
            self.mock_cfs_client, self.mock_cfs_configs, self.args
        )

        # Even though the first config fails, the second should still be processed
        self.assert_config_dumped_to_file(self.mock_cfs_configs[1])
        self.assert_config_put_to_cfs(self.mock_cfs_configs[1])

        expected_logs = [
            f'Creating {len(self.mock_cfs_configs)} CFS configuration(s)',
            f'Creating CFS configuration with name "{self.mock_cfs_configs[0].name}"',
            f'Failed to get data to create configuration {self.mock_cfs_configs[0].name}: {create_err}',
        ] + self.get_expected_info_logs(self.mock_cfs_configs[1:])
        self.assertEqual(expected_logs, [rec.message for rec in logs_cm.records])

    def test_create_cfs_configurations_one_file_failure(self):
        """Test create_configurations when one fails to be written to a file"""
        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_configurations(self.mock_instance, self.args)

        self.assert_cfs_client_created()
        self.mock_handle_existing_configs.assert_called_once_with(
            self.mock_cfs_client, self.mock_cfs_configs, self.args
        )

        for config in self.mock_cfs_configs:
            self.assert_config_put_to_cfs(config)

        expected_info_logs = [
            f'Creating {len(self.mock_cfs_configs)} CFS configuration(s)',
        ] + self.get_expected_info_logs(self.mock_cfs_configs)
        info_logs = [rec.message for rec in logs_cm.records if rec.levelno == logging.INFO]
        self.assertEqual(expected_info_logs, info_logs)

    def test_create_cfs_configurations_dry_run(self):
        """Test create_configurations in dry-run mode"""
        self.args.dry_run = True

        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_configurations(self.mock_instance, self.args)

        self.assert_cfs_client_created()
        self.mock_handle_existing_configs.assert_called_once_with(
            self.mock_cfs_client, self.mock_cfs_configs, self.args
        )
        for config in self.mock_cfs_configs:
            self.assert_config_dumped_to_file(config)
        self.mock_cfs_client.put_configuration.assert_not_called()
        expected_logs = [
            f'Would create {len(self.mock_cfs_configs)} CFS configuration(s)',
        ] + self.get_expected_info_logs(self.mock_cfs_configs, dry_run=True)
        self.assertEqual(expected_logs, [rec.message for rec in logs_cm.records])

    def test_create_cfs_configurations_one_api_error(self):
        """Test create_configurations when one fails to be created with an APIError"""
        api_err_msg = 'Failed to create CFS configuration'
        self.mock_cfs_client.put_configuration.side_effect = [APIError(api_err_msg), None]
        err_regex = r'Failed to create 1 configuration\(s\)'

        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            with self.assertLogs(level=logging.INFO) as logs_cm:
                create_configurations(self.mock_instance, self.args)

        self.assert_cfs_client_created()
        self.mock_handle_existing_configs.assert_called_once_with(
            self.mock_cfs_client, self.mock_cfs_configs, self.args
        )
        for config in self.mock_cfs_configs:
            self.assert_config_dumped_to_file(config)
            self.assert_config_put_to_cfs(config)
        expected_info_logs = [
            f'Creating {len(self.mock_cfs_configs)} CFS configuration(s)',
        ] + self.get_expected_info_logs(self.mock_cfs_configs)
        info_msgs = [rec.message for rec in logs_cm.records if rec.levelno == logging.INFO]
        self.assertEqual(expected_info_logs, info_msgs)
        expected_error_logs = [f'Failed to create or update configuration '
                               f'{self.mock_cfs_configs[0].name}: {api_err_msg}']
        error_msgs = [rec.message for rec in logs_cm.records if rec.levelno == logging.ERROR]
        self.assertEqual(expected_error_logs, error_msgs)


if __name__ == '__main__':
    unittest.main()
