"""
Tests for sat.cli.bootprep.input.configuration

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
import logging
import unittest
from copy import deepcopy
from textwrap import dedent
from unittest.mock import patch, Mock

from kubernetes.client import ApiException
from kubernetes.config import ConfigException

from sat.apiclient.vcs import VCSError
from sat.cli.bootprep.errors import ConfigurationCreateError
from sat.cli.bootprep.input.configuration import (
    InputConfigurationLayer,
    GitInputConfigurationLayer,
    ProductInputConfigurationLayer,
    InputConfiguration,
    LATEST_VERSION_VALUE
)


def patch_configuration(path, *args, **kwargs):
    """Wrapper around unittest.mock.patch to patch something in sat.cli.bootprep.input.configuration"""
    return patch(f'sat.cli.bootprep.input.configuration.{path}', *args, **kwargs)


class TestInputConfigurationLayer(unittest.TestCase):
    """Tests for the InputConfigurationLayer class"""

    def setUp(self):
        """Mock the constructors for the child classes"""
        self.mock_git_layer = patch_configuration('GitInputConfigurationLayer').start()
        self.mock_product_layer = patch_configuration('ProductInputConfigurationLayer').start()

    def tearDown(self):
        patch.stopall()

    def test_get_configuration_layer_git(self):
        """Test the get_configuration_layer static method with a git layer"""
        # Just needs a 'git' key; we're mocking the GitInputConfigurationLayer class
        layer_data = {'git': {}}
        layer = InputConfigurationLayer.get_configuration_layer(layer_data)
        self.assertEqual(self.mock_git_layer.return_value, layer)

    def test_get_configuration_layer_product(self):
        """Test the get_configuration_layer static method with a product layer"""
        layer_data = {'product': {}}
        layer = InputConfigurationLayer.get_configuration_layer(layer_data)
        self.assertEqual(self.mock_product_layer.return_value, layer)

    def test_get_configuration_layer_unknown(self):
        """Test the get_configuration_layer static method with bad layer data"""
        # All that matters is that it does not have a 'product' or 'git' key
        # This should never happen in practice because input files are validated against
        # a JSON schema that requires either the 'git' or 'product' keys.
        layer_data = {'unknown': {}}
        expected_err = 'Unrecognized type of configuration layer'
        with self.assertRaisesRegex(ValueError, expected_err):
            InputConfigurationLayer.get_configuration_layer(layer_data)


class TestGitInputConfigurationLayer(unittest.TestCase):
    """Tests for the GitInputConfigurationLayer class"""

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

        self.branch_head_commit = 'e6bfdb28d44669c4317d6dc021c22a75cebb3bfb'
        self.mock_vcs_repo = patch('sat.cli.bootprep.input.configuration.VCSRepo').start()
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = self.branch_head_commit

        patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', False).start()

    def tearDown(self):
        patch.stopall()

    def test_playbook_property_present(self):
        """Test the playbook property when a playbook is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.playbook, layer.playbook)

    def test_playbook_property_not_present(self):
        """Test the playbook property when a playbook is not in the layer data"""
        del self.branch_layer_data['playbook']
        layer = GitInputConfigurationLayer(self.branch_layer_data)
        self.assertIsNone(layer.playbook)

    def test_name_property_present(self):
        """Test the name property when the name is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.branch_layer_data['name'], layer.name)

    def test_name_property_not_present(self):
        """Test the name property when the name is not in the layer data"""
        del self.branch_layer_data['name']
        layer = GitInputConfigurationLayer(self.branch_layer_data)
        self.assertIsNone(layer.name)

    def test_clone_url_property(self):
        """Test the clone_url property."""
        layer = GitInputConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.branch_layer_data['git']['url'], layer.clone_url)

    def test_branch_property_present(self):
        """Test the branch property when the branch is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data)
        self.assertEqual(self.branch_layer_data['git']['branch'], layer.branch)

    def test_branch_property_not_present(self):
        """Test the branch property when the branch is not in the layer data"""
        layer = GitInputConfigurationLayer(self.commit_layer_data)
        self.assertIsNone(layer.branch)

    def test_commit_property_present(self):
        """Test the commit property when the commit is in the layer data"""
        layer = GitInputConfigurationLayer(self.commit_layer_data)
        self.assertEqual(self.commit_layer_data['git']['commit'], layer.commit)

    def test_commit_property_not_present(self):
        """Test the commit property when the commit is not in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data)
        self.assertIsNone(layer.commit)

    def test_get_cfs_api_data_optional_properties(self):
        """Test get_cfs_api_data method with all optional properties present."""
        branch_layer = GitInputConfigurationLayer(self.branch_layer_data)
        commit_layer = GitInputConfigurationLayer(self.commit_layer_data)
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

    def test_commit_property_branch_commit_lookup(self):
        """Test looking up commit hash from branch in VCS when branch not supported in CSM"""
        with patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', True):
            layer = GitInputConfigurationLayer(self.branch_layer_data)
            self.assertEqual(layer.commit, self.branch_head_commit)

    def test_commit_property_branch_commit_vcs_query_fails(self):
        """Test looking up commit hash raises ConfiurationCreateError when VCS is inaccessible"""
        with patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', True):
            layer = GitInputConfigurationLayer(self.branch_layer_data)
            self.mock_vcs_repo.return_value.get_commit_hash_for_branch.side_effect = VCSError
            with self.assertRaises(ConfigurationCreateError):
                _ = layer.commit

    def test_commit_property_branch_commit_lookup_fails(self):
        """Test looking up commit hash for nonexistent branch when branch not supported in CSM"""
        with patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', True):
            layer = GitInputConfigurationLayer(self.branch_layer_data)
            self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = None
            with self.assertRaises(ConfigurationCreateError):
                _ = layer.commit


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
        self.version_layer = ProductInputConfigurationLayer(self.version_layer_data)
        self.branch = 'integration'
        self.branch_layer_data = {
            'name': 'branch_layer',
            'playbook': self.playbook,
            'product': {
                'name': self.product_name,
                'branch': self.branch
            }
        }
        self.branch_layer = ProductInputConfigurationLayer(self.branch_layer_data)

        self.mock_core_v1_api_cls = patch_configuration('CoreV1Api').start()
        self.mock_core_v1_api = self.mock_core_v1_api_cls.return_value
        self.mock_load_kube_config = patch_configuration('load_kube_config').start()
        mock_config_map_response = Mock(data=self.product_catalog_data)
        self.mock_core_v1_api.read_namespaced_config_map.return_value = mock_config_map_response

        self.branch_head_commit = 'e6bfdb28d44669c4317d6dc021c22a75cebb3bfb'
        self.mock_vcs_repo = patch('sat.cli.bootprep.input.configuration.VCSRepo').start()
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = self.branch_head_commit

        patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', False).start()

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
        latest_layer = ProductInputConfigurationLayer(latest_layer_data)
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
        layer = ProductInputConfigurationLayer(layer_data)

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
        layer = ProductInputConfigurationLayer(layer_data)

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

    def test_commit_property_branch_commit_lookup(self):
        """Test looking up commit hash from branch in VCS when branch not supported in CSM"""
        with patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', True):
            self.assertEqual(self.branch_layer.commit, self.branch_head_commit)

    def test_commit_property_branch_commit_vcs_query_fails(self):
        """Test looking up commit hash raises ConfiurationCreateError when VCS is inaccessible"""
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.side_effect = VCSError
        with patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', True):
            with self.assertRaises(ConfigurationCreateError):
                _ = self.branch_layer.commit

    def test_commit_property_branch_commit_lookup_fails(self):
        """Test looking up commit hash for nonexistent branch when branch not supported in CSM"""
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = None
        with patch('sat.cli.bootprep.input.configuration.InputConfigurationLayer.resolve_branches', True):
            with self.assertRaises(ConfigurationCreateError):
                _ = self.branch_layer.commit


class TestInputConfiguration(unittest.TestCase):
    """Tests for the InputConfiguration class"""

    def setUp(self):
        """Mock InputConfigurationLayer.get_configuration_layer"""
        self.config_name = 'compute-config'
        self.num_layers = 3
        self.config_data = {
            'name': self.config_name,
            'layers': [{}] * self.num_layers
        }
        self.layers = [Mock() for _ in range(self.num_layers)]
        self.mock_get_config_layer = patch_configuration('InputConfigurationLayer.get_configuration_layer').start()
        self.mock_get_config_layer.side_effect = self.layers

    def tearDown(self):
        patch.stopall()

    def test_init(self):
        """Test creation of a InputConfiguration"""
        config = InputConfiguration(self.config_data)
        self.assertEqual(self.config_name, config.name)
        self.assertEqual(self.layers, config.layers)

    def test_name_property(self):
        """Test the name property of the InputConfiguration"""
        config = InputConfiguration(self.config_data)
        self.assertEqual(self.config_name, config.name)

    def test_get_cfs_api_data(self):
        """Test successful case of get_cfs_api_data"""
        expected = {
            'layers': [layer.get_cfs_api_data.return_value
                       for layer in self.layers]
        }
        config = InputConfiguration(self.config_data)
        self.assertEqual(expected, config.get_cfs_api_data())

    def test_get_cfs_api_data_one_failure(self):
        """Test when there is a failure to get data for one layer"""
        failing_layer = self.layers[1]
        create_fail_msg = 'bad layer'
        failing_layer.get_cfs_api_data.side_effect = ConfigurationCreateError(create_fail_msg)
        err_regex = fr'Failed to create 1 layer\(s\) of configuration {self.config_name}'
        config = InputConfiguration(self.config_data)

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
        config = InputConfiguration(self.config_data)

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(ConfigurationCreateError, err_regex):
                config.get_cfs_api_data()

        self.assertEqual(self.num_layers, len(logs_cm.records))
        for idx in range(self.num_layers):
            self.assertEqual(f'Failed to create layers[{idx}] of configuration '
                             f'{self.config_name}: {create_fail_msg}',
                             logs_cm.records[idx].message)


if __name__ == '__main__':
    unittest.main()
