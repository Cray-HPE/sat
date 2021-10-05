"""
Tests for sat.cli.bootprep.configuration

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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
from argparse import Namespace
from copy import deepcopy
import logging
import os
from textwrap import dedent
import unittest
from unittest.mock import patch, MagicMock, Mock

from kubernetes.config import ConfigException
from kubernetes.client import ApiException

from sat.apiclient import APIError
from sat.cli.bootprep.configuration import (
    create_cfs_configurations,
    handle_existing_configs,
    CFSConfiguration,
    CFSConfigurationLayer,
    GitCFSConfigurationLayer,
    LATEST_VERSION_VALUE,
    ProductCFSConfigurationLayer
)
from sat.cli.bootprep.errors import ConfigurationCreateError


class TestCFSConfigurationLayer(unittest.TestCase):
    """Tests for the CFSConfigurationLayer class"""

    def setUp(self):
        """Mock the constructors for the child classes"""
        self.mock_git_layer = patch('sat.cli.bootprep.configuration.GitCFSConfigurationLayer').start()
        self.mock_product_layer = patch('sat.cli.bootprep.configuration.ProductCFSConfigurationLayer').start()

    def tearDown(self):
        patch.stopall()

    def test_get_configuration_layer_git(self):
        """Test the get_configuration_layer static method with a git layer"""
        # Just needs a 'git' key; we're mocking the GitCFSConfigurationLayer class
        layer_data = {'git': {}}
        layer = CFSConfigurationLayer.get_configuration_layer(layer_data)
        self.assertEqual(self.mock_git_layer.return_value, layer)

    def test_get_configuration_layer_product(self):
        """Test the get_configuration_layer static method with a product layer"""
        layer_data = {'product': {}}
        layer = CFSConfigurationLayer.get_configuration_layer(layer_data)
        self.assertEqual(self.mock_product_layer.return_value, layer)

    def test_get_configuration_layer_unknown(self):
        """Test the get_configuration_layer static method with bad layer data"""
        # All that matters is that it does not have a 'product' or 'git' key
        # This should never happen in practice because input files are validated against
        # a JSON schema that requires either the 'git' or 'product' keys.
        layer_data = {'unknown': {}}
        expected_err = 'Unrecognized type of configuration layer'
        with self.assertRaisesRegex(ValueError, expected_err):
            CFSConfigurationLayer.get_configuration_layer(layer_data)


class TestGitCFSConfigurationLayer(unittest.TestCase):
    """Tests for the GitCFSConfigurationLayer class"""

    def setUp(self):
        """Create some layer data to use in unit tests."""
        self.playbook = 'site.yaml'
        self.branch_layer_data = {
            'playbook': self.playbook,
            'name': 'branch_layer',
            'git': {
                'url': 'https://api-gw-service-nmn.local/vcs/cray/cos-config-management.git',
                'branch': 'integration'
            }
        }
        self.commit_layer_data = {
            'playbook': self.playbook,
            'name': 'commit_layer',
            'git': {
                'url': 'https://api-gw-service-nmn.local/vcs/cray/analytics-config-management.git',
                'commit': '01f9a2aac3e315c5caa00db4019f1d934171dba0'
            }
        }

    def test_playbook_property_present(self):
        """Test the playbook property when a playbook is in the layer data"""
        layer = GitCFSConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.playbook, layer.playbook)

    def test_playbook_property_not_present(self):
        """Test the playbook property when a playbook is not in the layer data"""
        del self.branch_layer_data['playbook']
        layer = GitCFSConfigurationLayer(self.branch_layer_data)
        self.assertIsNone(layer.playbook)

    def test_name_property_present(self):
        """Test the name property when the name is in the layer data"""
        layer = GitCFSConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.branch_layer_data['name'], layer.name)

    def test_name_property_not_present(self):
        """Test the name property when the name is not in the layer data"""
        del self.branch_layer_data['name']
        layer = GitCFSConfigurationLayer(self.branch_layer_data)
        self.assertIsNone(layer.name)

    def test_clone_url_property(self):
        """Test the clone_url property."""
        layer = GitCFSConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.branch_layer_data['git']['url'], layer.clone_url)

    def test_branch_property_present(self):
        """Test the branch property when the branch is in the layer data"""
        layer = GitCFSConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.branch_layer_data['git']['branch'], layer.branch)

    def test_branch_property_not_present(self):
        """Test the branch property when the branch is not in the layer data"""
        layer = GitCFSConfigurationLayer(self.commit_layer_data)
        self.assertIsNone(layer.branch)

    def test_commit_property_present(self):
        """Test the commit property when the commit is in the layer data"""
        layer = GitCFSConfigurationLayer(self.commit_layer_data)
        self.assertEqual(self.commit_layer_data['git']['commit'], layer.commit)

    def test_commit_property_not_present(self):
        """Test the commit property when the commit is not in the layer data"""
        layer = GitCFSConfigurationLayer(self.branch_layer_data)
        self.assertIsNone(layer.commit)

    def test_get_cfs_api_data_optional_properties(self):
        """Test get_cfs_api_data method with all optional properties present."""
        branch_layer = GitCFSConfigurationLayer(self.branch_layer_data)
        commit_layer = GitCFSConfigurationLayer(self.commit_layer_data)
        subtests = (('branch', branch_layer), ('commit', commit_layer))
        for present_property, layer in subtests:
            with self.subTest(present_property=present_property):
                expected = deepcopy(getattr(self, f'{present_property}_layer_data'))
                expected['cloneUrl'] = expected['git']['url']
                del expected['git']['url']
                # Move branch or commit to the top level
                for key, value in expected['git'].items():
                    expected[key] = value
                del expected['git']
                self.assertEqual(expected, layer.get_cfs_api_data())


class TestProductConfigurationLayer(unittest.TestCase):
    """Tests for the ProductConfigurationLayer class."""

    def setUp(self):
        """Mock K8s API to return fake product catalog data and set up layers"""
        # Minimal set of product catalog data needed for these tests
        self.old_url = 'https://vcs.local/vcs/cray/cos-config-management.git'
        self.old_commit = '82537e59c24dd5607d5f5d6f92cdff971bd9c615'
        self.new_url = 'https://vcs.local/vcs/cray/newcos-config-management.git'
        self.new_commit = '6b0d9d55d399c92abae08002e75b9a1ce002f917'
        self.product_name = 'cos'
        self.product_version = '2.1.50'
        self.cos_data_string = dedent(f"""
        {self.product_version}:
          configuration:
            clone_url: {self.old_url}
            commit: {self.old_commit}
        2.1.51:
          configuration:
            clone_url: {self.new_url}
            commit: {self.new_commit}
        """)
        self.product_catalog_data = {
            'cos': self.cos_data_string
        }

        self.playbook = 'site.yaml'
        self.version_layer_data = {
            'name': 'version_layer',
            'playbook': self.playbook,
            'product': {
                'name': self.product_name,
                'version': self.product_version
            }
        }
        self.version_layer = ProductCFSConfigurationLayer(self.version_layer_data)
        self.branch = 'integration'
        self.branch_layer_data = {
            'name': 'branch_layer',
            'playbook': self.playbook,
            'product': {
                'name': self.product_name,
                'branch': self.branch
            }
        }
        self.branch_layer = ProductCFSConfigurationLayer(self.branch_layer_data)

        self.mock_core_v1_api_cls = patch('sat.cli.bootprep.configuration.CoreV1Api').start()
        self.mock_core_v1_api = self.mock_core_v1_api_cls.return_value
        self.mock_load_kube_config = patch('sat.cli.bootprep.configuration.load_kube_config').start()
        mock_config_map_response = Mock(data=self.product_catalog_data)
        self.mock_core_v1_api.read_namespaced_config_map.return_value = mock_config_map_response

    def tearDown(self):
        patch.stopall()

    def test_k8s_api_property_success(self):
        """Test getting the k8s_api property when the config is successfully loaded"""
        k8s_api = self.version_layer.k8s_api
        self.assertEqual(self.mock_core_v1_api, k8s_api)

    def test_k8s_api_property_load_failure(self):
        """Test getting the k8s_api property when there is a failure loading the config"""
        exceptions = (FileNotFoundError, ConfigException)
        err_regex = 'Failed to load Kubernetes config which is required to read product catalog data'
        for exception in exceptions:
            with self.subTest(exception=exception):
                self.mock_load_kube_config.side_effect = exception
                with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
                    _ = self.version_layer.k8s_api

    def test_product_name_property(self):
        """Test the product_name property"""
        self.assertEqual(self.product_name, self.version_layer.product_name)

    def test_product_version_property_present(self):
        """Test the product_version property when version is in the layer data"""
        self.assertEqual(self.product_version, self.version_layer.product_version)

    def test_product_version_property_not_present(self):
        """Test the product_version property when version is not in the layer data"""
        self.assertEqual(LATEST_VERSION_VALUE, self.branch_layer.product_version)

    def test_product_version_data_explicit_version(self):
        """Test getting product version data from the product catalog for an explicit version"""
        expected_version_data = {
            'configuration': {
                'clone_url': self.old_url,
                'commit': self.old_commit
            }
        }
        self.assertEqual(expected_version_data, self.version_layer.product_version_data)

    def test_product_version_data_no_version(self):
        """Test getting product version data from the product catalog for an assumed latest version"""
        expected_version_data = {
            'configuration': {
                'clone_url': self.new_url,
                'commit': self.new_commit
            }
        }
        self.assertEqual(expected_version_data, self.branch_layer.product_version_data)

    def test_product_version_data_latest_version(self):
        """Test getting product version data from the product catalog for explicit latest version"""
        latest_layer_data = deepcopy(self.branch_layer_data)
        latest_layer_data['product']['version'] = LATEST_VERSION_VALUE
        latest_layer = ProductCFSConfigurationLayer(latest_layer_data)
        expected_version_data = {
            'configuration': {
                'clone_url': self.new_url,
                'commit': self.new_commit
            }
        }
        self.assertEqual(expected_version_data, latest_layer.product_version_data)

    def test_product_version_data_k8s_api_exception(self):
        """Test getting product version data when there is a failure to obtain the config map"""
        self.mock_core_v1_api.read_namespaced_config_map.side_effect = ApiException
        err_regex = 'Failed to read Kubernetes ConfigMap cray-product-catalog in services namespace'
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            _ = self.version_layer.product_version_data

    def test_product_version_data_unknown_product(self):
        """Test getting product version data for an unknown product"""
        layer_data = deepcopy(self.version_layer_data)
        unknown_product = 'unknown'
        layer_data['product']['name'] = unknown_product
        layer = ProductCFSConfigurationLayer(layer_data)

        err_regex = f'Product {unknown_product} not present in product catalog'
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            _ = layer.product_version_data

    def test_product_version_data_bad_yaml(self):
        """Test getting product version data when the data is not valid YAML"""
        invalid_yaml_data = {self.product_name: 'foo: bar: baz'}
        mock_response = Mock(data=invalid_yaml_data)
        self.mock_core_v1_api.read_namespaced_config_map.return_value = mock_response

        err_regex = f'Product {self.product_name} data not in valid YAML format in product catalog'
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            _ = self.version_layer.product_version_data

    def test_product_version_data_unknown_version(self):
        """Test getting product version data for an unknown version of a product"""
        layer_data = deepcopy(self.version_layer_data)
        unknown_version = '99.99.99'
        layer_data['product']['version'] = unknown_version
        layer = ProductCFSConfigurationLayer(layer_data)

        err_regex = (f'No match found for version {unknown_version} of product '
                     f'{self.product_name} in product catalog')
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            _ = layer.product_version_data

    def test_clone_url_present(self):
        """Test clone_url when present in product catalog data"""
        self.assertEqual(self.old_url, self.version_layer.clone_url)

    def test_clone_url_configuration_key_not_present(self):
        """Test clone_url when the 'configuration' key is missing in product catalog data"""
        bad_product_catalog_data = {self.product_name: f'{self.product_version}: {{}}'}
        mock_response = Mock(data=bad_product_catalog_data)
        self.mock_core_v1_api.read_namespaced_config_map.return_value = mock_response

        err_regex = (f"No clone URL present for product {self.product_name}; "
                     f"missing key: 'configuration'")
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            _ = self.version_layer.clone_url

    def test_clone_url_clone_url_key_not_present(self):
        """Test clone_url when the 'clone_url' key is missing in product catalog data"""
        bad_product_catalog_data = {self.product_name: f'{self.product_version}:\n'
                                                       f'  configuration: {{}}'}
        mock_response = Mock(data=bad_product_catalog_data)
        self.mock_core_v1_api.read_namespaced_config_map.return_value = mock_response

        err_regex = (f"No clone URL present for product {self.product_name}; "
                     f"missing key: 'clone_url'")
        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            _ = self.version_layer.clone_url

    def test_branch_property_present(self):
        """Test the branch property when branch is in the layer data"""
        self.assertEqual(self.branch, self.branch_layer.branch)

    def test_branch_property_not_present(self):
        """Test the branch property when branch is not in the layer data"""
        self.assertIsNone(self.version_layer.branch)

    def test_commit_property_branch_present(self):
        """Test the commit property when a branch is in the layer data"""
        self.assertIsNone(self.branch_layer.commit)

    def test_commit_property_branch_not_present(self):
        """Test the commit property when a branch is not in the layer data"""
        self.assertEqual(self.old_commit, self.version_layer.commit)


class TestCFSConfiguration(unittest.TestCase):
    """Tests for the CFSConfiguration class"""

    def setUp(self):
        """Mock CFSConfigurationLayer.get_configuration_layer"""
        self.config_name = 'compute-config'
        self.num_layers = 3
        self.config_data = {
            'name': self.config_name,
            'layers': [{}] * self.num_layers
        }
        self.layers = [Mock() for _ in range(self.num_layers)]
        self.mock_get_config_layer = patch(
            'sat.cli.bootprep.configuration.CFSConfigurationLayer.get_configuration_layer').start()
        self.mock_get_config_layer.side_effect = self.layers

    def tearDown(self):
        patch.stopall()

    def test_init(self):
        """Test creation of a CFSConfiguration"""
        config = CFSConfiguration(self.config_data)
        self.assertEqual(self.config_name, config.name)
        self.assertEqual(self.layers, config.layers)

    def test_name_property(self):
        """Test the name property of the CFSConfiguration"""
        config = CFSConfiguration(self.config_data)
        self.assertEqual(self.config_name, config.name)

    def test_get_cfs_api_data(self):
        """Test successful case of get_cfs_api_data"""
        expected = {
            'layers': [layer.get_cfs_api_data.return_value
                       for layer in self.layers]
        }
        config = CFSConfiguration(self.config_data)
        self.assertEqual(expected, config.get_cfs_api_data())

    def test_get_cfs_api_data_one_failure(self):
        """Test when there is a failure to get data for one layer"""
        failing_layer = self.layers[1]
        create_fail_msg = 'bad layer'
        failing_layer.get_cfs_api_data.side_effect = ConfigurationCreateError(create_fail_msg)
        err_regex = fr'Failed to create 1 layer\(s\) of configuration {self.config_name}'
        config = CFSConfiguration(self.config_data)

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
                config.get_cfs_api_data()

        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Failed to create layers[1] of configuration '
                         f'{self.config_name}: {create_fail_msg}',
                         logs_cm.records[0].message)

    def test_get_cfs_api_data_multiple_failures(self):
        """Test when there are failures to get data for multiple layers"""
        create_fail_msg = 'bad layer'
        for layer in self.layers:
            layer.get_cfs_api_data.side_effect = ConfigurationCreateError(create_fail_msg)
        err_regex = fr'Failed to create 3 layer\(s\) of configuration {self.config_name}'
        config = CFSConfiguration(self.config_data)

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
                config.get_cfs_api_data()

        self.assertEqual(self.num_layers, len(logs_cm.records))
        for idx in range(self.num_layers):
            self.assertEqual(f'Failed to create layers[{idx}] of configuration '
                             f'{self.config_name}: {create_fail_msg}',
                             logs_cm.records[idx].message)


class TestHandleExistingConfigs(unittest.TestCase):
    """Tests for handle_existing_configs function"""

    def setUp(self):
        """Mock CFSClient, mock CFSConfigurations, args, and Mock pester_choices"""
        self.set_up_cfs_configs(['compute-1.4.2', 'uan-1.4.2'])
        self.set_up_input_configs(['compute-1.5.0', 'uan-1.5.0'])

        self.args = Namespace(dry_run=False, overwrite_configs=False,
                              skip_existing_configs=False)

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
    """Tests for the create_cfs_configurations function"""

    def setUp(self):
        """Mock CFSConfiguration, CFSClient, SATSession, open, json.dump; create args"""

        self.config_names = ['compute-1.4.2', 'uan-1.4.2']
        self.instance_data = {
            'configurations': [{'name': name, 'layers': []} for name in self.config_names]
        }

        self.mock_cfs_config_cls = patch('sat.cli.bootprep.configuration.CFSConfiguration').start()
        self.mock_cfs_configs = []
        for config_name in self.config_names:
            mock_cfs_config = Mock()
            mock_cfs_config.name = config_name
            self.mock_cfs_configs.append(mock_cfs_config)
        self.mock_cfs_config_cls.side_effect = self.mock_cfs_configs

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

        outer_self = self

        class FakeOpenCM:
            """Context manager to replace open to return correct mock file objects"""
            def __init__(self, path, _):
                self.path = path

            def __enter__(self):
                return outer_self.mock_file_objects[os.path.basename(self.path)]

            def __exit__(self, *args):
                # Nothing needed for fake context manager
                pass

        self.mock_open = patch('builtins.open').start()
        self.mock_open.side_effect = FakeOpenCM

        self.mock_makedirs = patch('os.makedirs').start()

        self.mock_json_dump = patch('json.dump').start()

        self.args = Namespace(dry_run=False, save_files=True, output_dir='output')

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
        self.mock_cfs_config_cls.assert_not_called()
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
            config (Mock): A Mock object representing a CFSConfiguration
        """
        expected_base_file_name = f'cfs-config-{config.name}.json'
        self.mock_open.assert_any_call(
            os.path.join(self.args.output_dir, expected_base_file_name),
            'w'
        )
        self.mock_json_dump.assert_any_call(
            config.get_cfs_api_data.return_value,
            self.mock_file_objects[expected_base_file_name],
            indent=4
        )

    def assert_config_put_to_cfs(self, config):
        """Assert the given config was PUT to CFS

        Args:
            config (Mock): A mock object representing a CFSConfiguration
        """
        self.mock_cfs_client.put_configuration.assert_any_call(
            config.name,
            config.get_cfs_api_data.return_value
        )

    def test_create_cfs_configurations_no_configurations(self):
        """Test create_cfs_configurations when configurations key is not present"""
        instance = {'images': [], 'session_templates': []}
        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_cfs_configurations(instance, self.args)
        self.assert_no_action_taken(logs_cm)

    def test_create_cfs_configurations_empty_list(self):
        """Test create_cfs_configurations when configurations is an empty list"""
        instance = {'configurations': [], 'images': [], 'session_templates': []}
        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_cfs_configurations(instance, self.args)
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
            expected_logs.append(f'Saving CFS config request body to '
                                 f'{self.get_expected_file_path(config)}')
        return expected_logs

    def test_create_cfs_configurations_success(self):
        """Test create_cfs_configurations in default, successful path"""
        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_cfs_configurations(self.instance_data, self.args)

        self.assert_cfs_client_created()
        self.mock_handle_existing_configs.assert_called_once_with(
            self.mock_cfs_client, self.mock_cfs_configs, self.args
        )
        self.mock_makedirs.assert_called_once_with(self.args.output_dir, exist_ok=True)
        for config in self.mock_cfs_configs:
            self.assert_config_dumped_to_file(config)
            self.assert_config_put_to_cfs(config)
        expected_logs = [
            f'Creating {len(self.mock_cfs_configs)} CFS configuration(s)',
        ] + self.get_expected_info_logs(self.mock_cfs_configs)
        self.assertEqual(expected_logs, [rec.message for rec in logs_cm.records])

    def test_create_cfs_configurations_one_cfs_data_failure(self):
        """Test create_cfs_configurations when one fails in its get_cfs_api_data method"""
        create_err = 'failed to get CFS API data'
        self.mock_cfs_configs[0].get_cfs_api_data.side_effect = ConfigurationCreateError(create_err)
        err_regex = r'Failed to create 1 configuration\(s\)'

        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            with self.assertLogs(level=logging.INFO) as logs_cm:
                create_cfs_configurations(self.instance_data, self.args)

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

    def test_create_cfs_configurations_output_dir_failure(self):
        """Test create_cfs_configurations with a failure to create the output directory"""
        os_err_msg = 'insufficient perms'
        self.mock_makedirs.side_effect = OSError(os_err_msg)

        with self.assertLogs(level=logging.WARNING) as logs_cm:
            create_cfs_configurations(self.instance_data, self.args)

        self.assert_cfs_client_created()
        self.mock_handle_existing_configs.assert_called_once_with(
            self.mock_cfs_client, self.mock_cfs_configs, self.args
        )
        self.mock_makedirs.assert_called_once_with(self.args.output_dir, exist_ok=True)
        self.mock_open.assert_not_called()
        for config in self.mock_cfs_configs:
            self.assert_config_put_to_cfs(config)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Failed to create output directory {self.args.output_dir}: {os_err_msg}. '
                         f'Files will not be saved.',
                         logs_cm.records[0].message)

    def test_create_cfs_configurations_one_file_failure(self):
        """Test create_cfs_configurations when one fails to be written to a file"""
        os_err_msg = 'insufficient permissions'
        self.mock_open.side_effect = [OSError(os_err_msg), MagicMock()]

        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_cfs_configurations(self.instance_data, self.args)

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
        expected_warning_logs = [
            f'Failed to write CFS config request body to '
            f'{self.get_expected_file_path(self.mock_cfs_configs[0])}: {os_err_msg}'
        ]
        warning_logs = [rec.message for rec in logs_cm.records if rec.levelno == logging.WARNING]
        self.assertEqual(expected_info_logs, info_logs)
        self.assertEqual(expected_warning_logs, warning_logs)

    def test_create_cfs_configurations_dry_run(self):
        """Test create_cfs_configurations in dry-run mode"""
        self.args.dry_run = True

        with self.assertLogs(level=logging.INFO) as logs_cm:
            create_cfs_configurations(self.instance_data, self.args)

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
        """Test create_cfs_configurations when one fails to be created with an APIError"""
        api_err_msg = 'Failed to create CFS configuration'
        self.mock_cfs_client.put_configuration.side_effect = [APIError(api_err_msg), None]
        err_regex = r'Failed to create 1 configuration\(s\)'

        with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
            with self.assertLogs(level=logging.INFO) as logs_cm:
                create_cfs_configurations(self.instance_data, self.args)

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
