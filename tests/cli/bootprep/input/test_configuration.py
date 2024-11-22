#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
Tests for sat.cli.bootprep.input.configuration
"""
import logging
import unittest
from unittest.mock import Mock, patch

from jinja2.sandbox import SandboxedEnvironment

from cray_product_catalog.query import ProductCatalog
from csm_api_client.service.cfs import CFSClientBase, CFSConfigurationError, CFSV2Client, CFSV3Client
from sat.cli.bootprep.errors import InputItemCreateError, InputItemValidateError
from sat.cli.bootprep.input.configuration import (
    AdditionalInventory,
    InputConfigurationLayer,
    GitInputConfigurationLayer,
    ProductInputConfigurationLayer,
    InputConfiguration,
)
from sat.cli.bootprep.input.instance import InputInstance


def patch_configuration(path, *args, **kwargs):
    """Wrapper around unittest.mock.patch to patch something in sat.cli.bootprep.input.configuration"""
    return patch(f'sat.cli.bootprep.input.configuration.{path}', *args, **kwargs)


class TestInputConfigurationLayer(unittest.TestCase):
    """Tests for the InputConfigurationLayer class"""

    def setUp(self):
        """Mock the constructors for the child classes"""
        self.mock_git_layer = patch_configuration('GitInputConfigurationLayer').start()
        self.mock_product_layer = patch_configuration('ProductInputConfigurationLayer').start()
        self.mock_cfs_client = Mock()
        self.mock_product_catalog = Mock()
        self.mock_jinja_env = Mock()

    def tearDown(self):
        patch.stopall()

    def test_get_configuration_layer_git(self):
        """Test the get_configuration_layer static method with a git layer"""
        # Just needs a 'git' key; we're mocking the GitInputConfigurationLayer class
        layer_data = {'git': {}}
        layer = InputConfigurationLayer.get_configuration_layer(layer_data, 0, self.mock_jinja_env,
                                                                self.mock_cfs_client,
                                                                self.mock_product_catalog)
        self.assertEqual(self.mock_git_layer.return_value, layer)
        self.mock_git_layer.assert_called_once_with(layer_data, 0, self.mock_jinja_env,
                                                    self.mock_cfs_client)

    def test_get_configuration_layer_product(self):
        """Test the get_configuration_layer static method with a product layer"""
        layer_data = {'product': {}}
        layer = InputConfigurationLayer.get_configuration_layer(layer_data, 0, self.mock_jinja_env,
                                                                self.mock_cfs_client,
                                                                self.mock_product_catalog)
        self.assertEqual(self.mock_product_layer.return_value, layer)
        self.mock_product_layer.assert_called_once_with(layer_data, 0, self.mock_jinja_env,
                                                        self.mock_cfs_client, self.mock_product_catalog)

    def test_get_configuration_layer_unknown(self):
        """Test the get_configuration_layer static method with bad layer data"""
        # All that matters is that it does not have a 'product' or 'git' key
        # This should never happen in practice because input files are validated against
        # a JSON schema that requires either the 'git' or 'product' keys.
        layer_data = {'unknown': {}}
        expected_err = 'Unrecognized type of configuration layer'
        with self.assertRaisesRegex(ValueError, expected_err):
            InputConfigurationLayer.get_configuration_layer(layer_data, 0, self.mock_jinja_env,
                                                            self.mock_cfs_client,
                                                            self.mock_product_catalog)


class TestInputConfigurationLayerBase(unittest.TestCase):

    module_path = 'sat.cli.bootprep.input.configuration'

    def setUp(self):
        """Mock needed functionality for both types of InputConfigurationLayer"""
        self.patch_resolve_branches(False).start()

        self.mock_cfs_client = Mock()
        self.mock_cfs_configuration_cls = self.mock_cfs_client.configuration_cls
        self.mock_cfs_layer_cls = self.mock_cfs_configuration_cls.cfs_config_layer_cls
        self.mock_add_inv_cls = self.mock_cfs_configuration_cls.cfs_additional_inventory_cls

    def tearDown(self):
        patch.stopall()

    def patch_resolve_branches(self, value):
        """Patch InputConfigurationLayer.resolve branches to the given value"""
        return patch(f'{self.module_path}.InputConfigurationLayerBase.resolve_branches', value)


class TestGitInputConfigurationLayer(TestInputConfigurationLayerBase):
    """Tests for the GitInputConfigurationLayer class"""

    def setUp(self):
        """Create some layer data to use in unit tests."""
        super().setUp()
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

        self.mock_sat_version = '2.3.6'
        self.mock_network_type = 'cassini'
        self.jinja_env = SandboxedEnvironment()
        self.jinja_env.globals = {
            'sat': {'version': self.mock_sat_version},
            'shs': {'version': '2.1.0', 'network_type': self.mock_network_type}
        }

    def tearDown(self):
        patch.stopall()

    def test_playbook_property_present(self):
        """Test the playbook property when a playbook is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(self.playbook, layer.playbook)

    def test_playbook_property_not_present(self):
        """Test the playbook property when a playbook is not in the layer data"""
        del self.branch_layer_data['playbook']
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertIsNone(layer.playbook)

    def test_playbook_property_jinja_template(self):
        """Test the playbook property when the playbook uses Jinja2 templating"""
        self.branch_layer_data['playbook'] = 'shs_{{shs.network_type}}_install.yaml'
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(f'shs_{self.mock_network_type}_install.yaml', layer.playbook)

    def test_name_property_present(self):
        """Test the name property when the name is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(self.branch_layer_data['name'], layer.name)

    def test_name_property_not_present(self):
        """Test the name property when the name is not in the layer data"""
        del self.branch_layer_data['name']
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertIsNone(layer.name)

    def test_name_property_jinja_template(self):
        """Test the name property when the name uses Jinja2 templating"""
        self.branch_layer_data['name'] = 'sat-ncn-{{sat.version}}'
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(f'sat-ncn-{self.mock_sat_version}', layer.name)

    def test_clone_url_property(self):
        """Test the clone_url property."""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(self.branch_layer_data['git']['url'], layer.clone_url)

    def test_branch_property_present(self):
        """Test the branch property when the branch is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(self.branch_layer_data['git']['branch'], layer.branch)

    def test_branch_property_not_present(self):
        """Test the branch property when the branch is not in the layer data"""
        layer = GitInputConfigurationLayer(self.commit_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertIsNone(layer.branch)

    def test_branch_property_jinja_template(self):
        """Test the branch property when the branch uses Jinja2 templating"""
        self.branch_layer_data['git']['branch'] = 'integration-{{sat.version}}'
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(f'integration-{self.mock_sat_version}', layer.branch)

    def test_commit_property_present(self):
        """Test the commit property when the commit is in the layer data"""
        layer = GitInputConfigurationLayer(self.commit_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertEqual(self.commit_layer_data['git']['commit'], layer.commit)

    def test_commit_property_not_present(self):
        """Test the commit property when the commit is not in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.assertIsNone(layer.commit)

    def test_validate_playbook_cfs_v3(self):
        """Test the validate_playbook_specified_with_cfs_v3 method with a CFSV3Client and present playbook"""
        mock_cfs_v3_client = Mock(spec=CFSV3Client)
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           mock_cfs_v3_client)
        layer.validate_playbook_specified_with_cfs_v3()

    def test_validate_playbook_missing_cfs_v3(self):
        """Test the validate_playbook_specified_with_cfs_v3 method with a CFSV3Client and missing playbook"""
        mock_cfs_v3_client = Mock(spec=CFSV3Client)
        del self.branch_layer_data['playbook']
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           mock_cfs_v3_client)
        err_regex = 'A playbook is required when using the CFS v3 API'
        with self.assertRaisesRegex(InputItemValidateError, err_regex):
            layer.validate_playbook_specified_with_cfs_v3()

    def test_validate_playbook_cfs_v2(self):
        """Test the validate_playbook_specified_with_cfs_v3 method with a CFSV2Client and present playbook"""
        mock_cfs_v2_client = Mock(spec=CFSV2Client)
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           mock_cfs_v2_client)
        layer.validate_playbook_specified_with_cfs_v3()

    def test_validate_playbook_missing_cfs_v2(self):
        """Test the validate_playbook_specified_with_cfs_v3 method with a CFSV2Client and missing playbook"""
        mock_cfs_v2_client = Mock(spec=CFSV2Client)
        del self.branch_layer_data['playbook']
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           mock_cfs_v2_client)
        layer.validate_playbook_specified_with_cfs_v3()

    def test_get_cfs_api_data_no_resolve_branches(self):
        """Test get_cfs_api_data method without branch resolution"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)

        cfs_api_data = layer.get_cfs_api_data()

        # All the work of getting CFS API request data is delegated to csm_api_client
        self.mock_cfs_layer_cls.from_clone_url.assert_called_once_with(
            clone_url=layer.clone_url, branch=layer.branch, commit=layer.commit,
            name=layer.name, playbook=layer.playbook, ims_require_dkms=layer.ims_require_dkms
        )
        cfs_layer_instance = self.mock_cfs_layer_cls.from_clone_url.return_value
        self.assertEqual(cfs_layer_instance.req_payload, cfs_api_data)
        cfs_layer_instance.resolve_branch_to_commit_hash.assert_not_called()

    def test_get_cfs_api_data_resolve_branches(self):
        """Test get_cfs_api_data method with branch resolution"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)

        with self.patch_resolve_branches(True):
            cfs_api_data = layer.get_cfs_api_data()

        # All the work of getting CFS API request data is delegated to csm_api_client
        self.mock_cfs_layer_cls.from_clone_url.assert_called_once_with(
            clone_url=layer.clone_url, branch=layer.branch, commit=layer.commit,
            name=layer.name, playbook=layer.playbook, ims_require_dkms=layer.ims_require_dkms
        )
        cfs_layer_instance = self.mock_cfs_layer_cls.from_clone_url.return_value
        self.assertEqual(cfs_layer_instance.req_payload, cfs_api_data)
        cfs_layer_instance.resolve_branch_to_commit_hash.assert_called_once_with()

    def test_get_cfs_api_data_value_error(self):
        """Test get_cfs_api_data method when from_clone_url raises ValueError"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        self.mock_cfs_layer_cls.from_clone_url.side_effect = ValueError('error')
        with self.assertRaisesRegex(InputItemCreateError, 'error'):
            _ = layer.get_cfs_api_data()

    def test_get_cfs_api_data_resolve_branch_error(self):
        """Test get_cfs_api_data method when branch resolution fails"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                           self.mock_cfs_client)
        with self.patch_resolve_branches(True):
            cfs_layer_instance = self.mock_cfs_layer_cls.from_clone_url.return_value
            cfs_layer_instance.resolve_branch_to_commit_hash.side_effect = CFSConfigurationError('error')
            with self.assertRaisesRegex(InputItemCreateError, 'error'):
                _ = layer.get_cfs_api_data()


class TestProductInputConfigurationLayer(TestInputConfigurationLayerBase):
    """Tests for the ProductInputConfigurationLayer class."""

    def setUp(self):
        """Mock K8s API to return fake product catalog data and set up layers"""
        super().setUp()

        self.mock_product_catalog = Mock()

        # Used to test variable substitution in Jinja2-templated fields
        self.jinja_env = SandboxedEnvironment()
        self.product_name = 'cos'
        self.product_version = '2.1.50'
        self.mock_network_type = 'cassini'
        self.jinja_env.globals = {
            self.product_name: {'version': self.product_version},
            'shs': {'version': '2.1.0', 'network_type': self.mock_network_type}
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
        self.version_layer = ProductInputConfigurationLayer(self.version_layer_data, 0,
                                                            self.jinja_env,
                                                            self.mock_cfs_client,
                                                            self.mock_product_catalog)
        self.branch = 'integration'
        self.branch_layer_data = {
            'name': 'branch_layer',
            'playbook': self.playbook,
            'product': {
                'name': self.product_name,
                'branch': self.branch
            }
        }
        self.branch_layer = ProductInputConfigurationLayer(self.branch_layer_data, 0,
                                                           self.jinja_env,
                                                           self.mock_cfs_client,
                                                           self.mock_product_catalog)

        self.commit = 'c07f317c4127d8667a4bd6c08d48e716b1d47da1'
        self.commit_layer_data = {
            'name': 'commit_layer',
            'playbook': self.playbook,
            'product': {
                'name': self.product_name,
                'commit': self.commit
            }
        }
        self.commit_layer = ProductInputConfigurationLayer(self.commit_layer_data, 0,
                                                           self.jinja_env,
                                                           self.mock_cfs_client,
                                                           self.mock_product_catalog)

        self.mock_api_gw = 'api_gateway.nmn'
        self.mock_sat_config = {
            'api_gateway.host': self.mock_api_gw
        }
        patch_configuration('get_config_value', side_effect=self.mock_sat_config.get).start()

    def tearDown(self):
        patch.stopall()

    def test_playbook_property_jinja_template(self):
        """Test the playbook property when the playbook uses Jinja2 templating"""
        self.branch_layer_data['playbook'] = 'shs_{{shs.network_type}}_install.yaml'
        layer = ProductInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                               self.mock_cfs_client, self.mock_product_catalog)
        self.assertEqual(f'shs_{self.mock_network_type}_install.yaml', layer.playbook)

    def test_product_name_property(self):
        """Test the product_name property"""
        self.assertEqual(self.product_name, self.version_layer.product_name)

    def test_product_version_property_present(self):
        """Test the product_version property when version is in the layer data"""
        self.assertEqual(self.product_version, self.version_layer.product_version)

    def test_product_version_property_not_present(self):
        """Test the product_version property when version is not in the layer data"""
        self.assertIsNone(self.branch_layer.product_version)

    def test_product_version_jinja_template(self):
        """Test the product_version property when it uses Jinja2 templating"""
        # Have to double the literal brackets that make up the Jinja2 variable reference
        self.version_layer_data['product']['version'] = '{{' + f'{self.product_name}.version' + '}}'

        layer = ProductInputConfigurationLayer(self.version_layer_data, 0, self.jinja_env,
                                               self.mock_cfs_client, self.mock_product_catalog)

        self.assertEqual(self.product_version, layer.product_version)

    def test_branch_property_present(self):
        """Test the branch property when branch is in the layer data"""
        self.assertEqual(self.branch, self.branch_layer.branch)

    def test_branch_property_not_present(self):
        """Test the branch property when branch is not in the layer data"""
        self.assertIsNone(self.version_layer.branch)

    def test_branch_property_jinja_template(self):
        """Test the branch property when the branch uses Jinja2 templating"""
        # Have to double the literal brackets that make up the Jinja2 variable reference
        self.branch_layer_data['product']['branch'] = 'integration-{{' + f'{self.product_name}.version' + '}}'

        layer = ProductInputConfigurationLayer(self.branch_layer_data, 0, self.jinja_env,
                                               self.mock_cfs_client, self.mock_product_catalog)

        self.assertEqual(f'integration-{self.product_version}', layer.branch)

    def test_commit_property_present(self):
        """Test the commit property when commit is in the layer data"""
        self.assertEqual(self.commit, self.commit_layer.commit)

    def test_commit_property_not_present(self):
        """Test the commit property when a branch is in the layer data"""
        self.assertIsNone(self.branch_layer.commit)

    def test_commit_property_resolve_branches(self):
        """Test the commit property when resolving branches and commit specified in the input file"""
        with self.patch_resolve_branches(True):
            self.assertEqual(self.commit_layer.commit, self.commit)

    def test_get_cfs_api_data_no_resolve_branches(self):
        """Test get_cfs_api_data method without branch resolution"""
        cfs_api_data = self.version_layer.get_cfs_api_data()

        # All the work of getting CFS API request data is delegated to csm_api_client
        self.mock_cfs_layer_cls.from_product_catalog.assert_called_once_with(
            product_name=self.product_name, api_gw_host=self.mock_api_gw,
            product_version=self.product_version, commit=None,
            branch=None, name=self.version_layer.name,
            playbook=self.playbook, ims_require_dkms=None,
            product_catalog=self.mock_product_catalog
        )
        cfs_layer_instance = self.mock_cfs_layer_cls.from_product_catalog.return_value
        self.assertEqual(cfs_layer_instance.req_payload, cfs_api_data)
        cfs_layer_instance.resolve_branch_to_commit_hash.assert_not_called()

    def test_get_cfs_api_data_resolve_branches(self):
        """Test get_cfs_api_data method with branch resolution"""
        with self.patch_resolve_branches(True):
            cfs_api_data = self.version_layer.get_cfs_api_data()

        # All the work of getting CFS API request data is delegated to csm_api_client
        self.mock_cfs_layer_cls.from_product_catalog.assert_called_once_with(
            product_name=self.product_name, api_gw_host=self.mock_api_gw,
            product_version=self.product_version, commit=None,
            branch=None, name=self.version_layer.name,
            playbook=self.playbook, ims_require_dkms=None,
            product_catalog=self.mock_product_catalog
        )
        cfs_layer_instance = self.mock_cfs_layer_cls.from_product_catalog.return_value
        self.assertEqual(cfs_layer_instance.req_payload, cfs_api_data)
        cfs_layer_instance.resolve_branch_to_commit_hash.assert_called_once_with()

    def test_get_cfs_api_data_value_error(self):
        """Test get_cfs_api_data method when from_product_catalog raises ValueError"""
        self.mock_cfs_layer_cls.from_product_catalog.side_effect = ValueError('error')
        with self.assertRaisesRegex(InputItemCreateError, 'error'):
            _ = self.version_layer.get_cfs_api_data()

    def test_get_cfs_api_data_cfs_configuration_error(self):
        """Test get_cfs_api_data method when from_product_catalog raises CFSConfigurationError"""
        self.mock_cfs_layer_cls.from_product_catalog.side_effect = CFSConfigurationError('error')
        with self.assertRaisesRegex(InputItemCreateError, 'error'):
            _ = self.version_layer.get_cfs_api_data()

    def test_get_cfs_api_data_resolve_branch_error(self):
        """Test get_cfs_api_data method when branch resolution raises CFSConfigurationError"""
        with self.patch_resolve_branches(True):
            cfs_layer_instance = self.mock_cfs_layer_cls.from_product_catalog.return_value
            cfs_layer_instance.resolve_branch_to_commit_hash.side_effect = CFSConfigurationError('error')
            with self.assertRaisesRegex(InputItemCreateError, 'error'):
                _ = self.version_layer.get_cfs_api_data()


class TestAdditionalInventory(TestInputConfigurationLayerBase):
    """Tests for the AdditionalInventory class"""

    def setUp(self):
        super().setUp()

        self.repo_url = 'https://api-gw-service.nmn.local/vcs/cray/inventory.git'
        self.commit_hash = '3b18e512dba79e4c8300dd08aeb37f8e728b8dad'
        self.branch = 'main'
        self.name = 'inventory'
        self.data_with_commit = {'url': self.repo_url, 'commit': self.commit_hash}
        self.data_with_branch = {'url': self.repo_url, 'branch': self.branch}
        self.data_with_name = {'url': self.repo_url, 'branch': self.branch, 'name': self.name}
        self.jinja_env = SandboxedEnvironment()

    def test_clone_url_property(self):
        """Test the clone_url property of AdditionalInventory"""
        additional_inventory = AdditionalInventory(self.data_with_commit, self.jinja_env,
                                                   self.mock_cfs_client)
        self.assertEqual(self.repo_url, additional_inventory.clone_url)

    def test_commit_property_specified(self):
        """Test the commit property when specified"""
        additional_inventory = AdditionalInventory(self.data_with_commit, self.jinja_env,
                                                   self.mock_cfs_client)
        self.assertEqual(self.commit_hash, additional_inventory.commit)

    def test_commit_property_unspecified(self):
        """Test the commit property when not specified"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env,
                                                   self.mock_cfs_client)
        self.assertIsNone(additional_inventory.commit)

    def test_branch_property_specified(self):
        """"Test the branch property when specified"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env,
                                                   self.mock_cfs_client)
        self.assertEqual(self.branch, additional_inventory.branch)

    def test_branch_property_not_specified(self):
        """"Test the branch property when not specified"""
        additional_inventory = AdditionalInventory(self.data_with_commit, self.jinja_env,
                                                   self.mock_cfs_client)
        self.assertIsNone(additional_inventory.branch)

    def test_name_property_specified(self):
        """Test the name property when specified"""
        additional_inventory = AdditionalInventory(self.data_with_name, self.jinja_env,
                                                   self.mock_cfs_client)
        self.assertEqual(self.name, additional_inventory.name)

    def test_name_property_not_specified(self):
        """Test the name property when not specified"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env,
                                                   self.mock_cfs_client)
        self.assertIsNone(additional_inventory.name)

    def test_get_cfs_api_data_no_resolve_branches(self):
        """Test get_cfs_api_data method without branch resolution"""
        additional_inventory = AdditionalInventory(self.data_with_name, self.jinja_env,
                                                   self.mock_cfs_client)
        cfs_api_data = additional_inventory.get_cfs_api_data()

        # All the work of getting CFS API request data is delegated to csm_api_client
        self.mock_add_inv_cls.from_clone_url.assert_called_once_with(
            clone_url=self.repo_url, name=self.name,
            branch=self.branch, commit=None
        )
        add_inv_instance = self.mock_add_inv_cls.from_clone_url.return_value
        self.assertEqual(add_inv_instance.req_payload, cfs_api_data)
        add_inv_instance.resolve_branch_to_commit_hash.assert_not_called()

    def test_get_cfs_api_data_resolve_branches(self):
        """Test get_cfs_api_data method with branch resolution"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env,
                                                   self.mock_cfs_client)
        with self.patch_resolve_branches(True):
            cfs_api_data = additional_inventory.get_cfs_api_data()

        # All the work of getting CFS API request data is delegated to csm_api_client
        self.mock_add_inv_cls.from_clone_url.assert_called_once_with(
            clone_url=self.repo_url, name=None,
            branch=self.branch, commit=None
        )
        add_inv_instance = self.mock_add_inv_cls.from_clone_url.return_value
        self.assertEqual(add_inv_instance.req_payload, cfs_api_data)
        add_inv_instance.resolve_branch_to_commit_hash.assert_called_once_with()

    def test_get_cfs_api_data_value_error(self):
        """Test get_cfs_api_data method when from_clone_url raises ValueError"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env,
                                                   self.mock_cfs_client)
        self.mock_add_inv_cls.from_clone_url.side_effect = ValueError('error')
        with self.assertRaisesRegex(InputItemCreateError, 'error'):
            _ = additional_inventory.get_cfs_api_data()

    def test_get_cfs_api_data_resolve_branch_error(self):
        """Test get_cfs_api_data method when branch resolution raises CFSConfigurationError"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env,
                                                   self.mock_cfs_client)
        with self.patch_resolve_branches(True):
            add_inv_instance = self.mock_add_inv_cls.from_clone_url.return_value
            add_inv_instance.resolve_branch_to_commit_hash.side_effect = CFSConfigurationError('error')
            with self.assertRaisesRegex(InputItemCreateError, 'error'):
                _ = additional_inventory.get_cfs_api_data()


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
        self.mock_additional_inventory_cls = patch_configuration('AdditionalInventory').start()
        self.mock_additional_inventory = self.mock_additional_inventory_cls.return_value
        self.mock_product_catalog = Mock()

        self.shasta_version = '22.06'
        self.jinja_env = SandboxedEnvironment()
        self.jinja_env.globals = {
            'shasta': {'version': self.shasta_version}
        }
        self.mock_instance = Mock(spec=InputInstance)
        # Fake index of configuration data in an input file
        self.index = 0
        self.mock_cfs_client = Mock(spec=CFSClientBase)

    def tearDown(self):
        patch.stopall()

    def test_init(self):
        """Test creation of an InputConfiguration"""
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)
        self.assertEqual(self.config_name, config.name)
        self.assertEqual(self.layers, config.layers)

    def test_init_with_additional_inventory(self):
        """Test creation of an InputConfiguration when there is additional_inventory specified"""
        additional_inventory_data = Mock()
        self.config_data['additional_inventory'] = additional_inventory_data
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)
        self.mock_additional_inventory_cls.assert_called_once_with(additional_inventory_data, self.jinja_env,
                                                                   self.mock_cfs_client)
        self.assertEqual(self.mock_additional_inventory, config.additional_inventory)

    def test_name_property(self):
        """Test the name property of the InputConfiguration"""
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)
        self.assertEqual(self.config_name, config.name)

    def test_name_property_jinja_template(self):
        """Test the name property when it uses Jinja2 templating"""
        self.config_data['name'] = 'compute-config-shasta-{{shasta.version}}'
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)
        self.assertEqual(f'compute-config-shasta-{self.shasta_version}', config.name)

    def test_get_create_item_data(self):
        """Test successful case of get_create_item_data"""
        expected = {
            'layers': [layer.get_cfs_api_data.return_value
                       for layer in self.layers]
        }
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)
        self.assertEqual(expected, config.get_create_item_data())

    def test_get_create_item_data_with_additional_inventory(self):
        """Test successfully getting get_create_item_data with additional_inventory"""
        additional_inventory_data = Mock()
        self.config_data['additional_inventory'] = additional_inventory_data
        expected = {
            'layers': [layer.get_cfs_api_data.return_value
                       for layer in self.layers],
            'additional_inventory': self.mock_additional_inventory.get_cfs_api_data.return_value
        }
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)
        self.mock_additional_inventory_cls.assert_called_once_with(additional_inventory_data,
                                                                   self.jinja_env, self.mock_cfs_client)
        self.assertEqual(expected, config.get_create_item_data())

    def test_get_create_item_data_one_layer_failure(self):
        """Test when there is a failure to get data for one layer"""
        failing_layer = self.layers[1]
        create_fail_msg = 'bad layer'
        failing_layer.get_cfs_api_data.side_effect = InputItemCreateError(create_fail_msg)
        err_regex = (fr'Failed to create configuration {self.config_name} '
                     fr'due to failure to create 1 layer\(s\)')
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(InputItemCreateError, err_regex):
                config.get_create_item_data()

        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Failed to create layers[1] of configuration '
                         f'{self.config_name}: {create_fail_msg}',
                         logs_cm.records[0].message)

    def test_get_create_item_data_multiple_layer_failures(self):
        """Test when there are failures to get data for multiple layers"""
        create_fail_msg = 'bad layer again'
        for layer in self.layers:
            layer.get_cfs_api_data.side_effect = InputItemCreateError(create_fail_msg)
        err_regex = (fr'Failed to create configuration {self.config_name} due to '
                     fr'failure to create {len(self.layers)} layer\(s\)')
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(InputItemCreateError, err_regex):
                config.get_create_item_data()

        self.assertEqual(self.num_layers, len(logs_cm.records))
        for idx in range(self.num_layers):
            self.assertEqual(f'Failed to create layers[{idx}] of configuration '
                             f'{self.config_name}: {create_fail_msg}',
                             logs_cm.records[idx].message)

    def test_get_create_item_data_additional_inventory_failure(self):
        """Test when there is a failure to get the create data for additional_inventory"""
        self.config_data['additional_inventory'] = {}
        create_fail_msg = 'bad inventory'
        self.mock_additional_inventory.get_cfs_api_data.side_effect = InputItemCreateError(create_fail_msg)
        err_regex = (fr'Failed to create configuration {self.config_name} due to '
                     fr'failure to resolve additional_inventory')
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(InputItemCreateError, err_regex):
                config.get_create_item_data()

        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Failed to resolve additional_inventory of configuration '
                         f'{self.config_name}: {create_fail_msg}',
                         logs_cm.records[0].message)

    def test_get_create_item_data_multiple_failures(self):
        """Test when there is a failure to get the create data for layers and additional_inventory"""
        self.config_data['additional_inventory'] = {}

        layer_fail_msg = 'layer failure'
        inventory_fail_msg = 'inventory failure'
        for layer in self.layers:
            layer.get_cfs_api_data.side_effect = InputItemCreateError(layer_fail_msg)
        self.mock_additional_inventory.get_cfs_api_data.side_effect = InputItemCreateError(inventory_fail_msg)
        err_regex = (fr'Failed to create configuration {self.config_name} due to '
                     fr'failure to create {len(self.layers)} layer\(s\) and failure '
                     fr'to resolve additional_inventory')
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, self.mock_cfs_client, self.mock_product_catalog)

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(InputItemCreateError, err_regex):
                config.get_create_item_data()

        # An error will be logged for each layer and for additional_inventory
        self.assertEqual(self.num_layers + 1, len(logs_cm.records))
        self.assertEqual(f'Failed to resolve additional_inventory of configuration '
                         f'{self.config_name}: {inventory_fail_msg}',
                         logs_cm.records[0].message)
        for idx in range(self.num_layers):
            self.assertEqual(f'Failed to create layers[{idx}] of configuration '
                             f'{self.config_name}: {layer_fail_msg}',
                             logs_cm.records[idx + 1].message)


class TestInputConfigurationValidation(unittest.TestCase):
    """Tests for the validate method of the InputConfiguration class"""

    def setUp(self):
        self.config_name = 'compute-config'
        self.config_data = {
            'name': self.config_name,
            'layers': [
                {
                    'name': 'branch_layer',
                    'git': {
                        'url': 'https://api-gw-service-nmn.local/vcs/cray/cos-config-management.git',
                        'branch': 'integration'
                    },
                    'playbook': 'site.yaml'
                },
                {
                    'name': 'version_layer',
                    'product': {
                        'name': 'csm',
                        'version': '1.6.0'
                    },
                    'playbook': 'site.yaml'
                }
            ]
        }
        self.jinja_env = SandboxedEnvironment()
        self.mock_product_catalog = Mock(spec=ProductCatalog)
        self.mock_instance = Mock(spec=InputInstance)
        # Fake index of configuration data in an input file
        self.index = 0

    def test_validate_layers_missing_playbook_cfs_v3(self):
        """Test validate function when layers are missing playbooks and we are using the CFS v3 API"""
        self.config_data['layers'][0].pop('playbook')
        self.config_data['layers'][1].pop('playbook')
        mock_cfs_v3_client = Mock(spec=CFSV3Client)
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, mock_cfs_v3_client, self.mock_product_catalog)
        err_regex = f'The CFS configuration at index {self.index} is not valid'
        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaisesRegex(InputItemValidateError, err_regex):
                config.validate()

        self.assertEqual(5, len(logs_cm.records))
        self.assertRegex(logs_cm.records[0].message, 'A playbook is required when using the CFS v3 API')
        self.assertRegex(logs_cm.records[1].message, 'The CFS configuration layer at index 0 is not valid')
        self.assertRegex(logs_cm.records[2].message, 'A playbook is required when using the CFS v3 API')
        self.assertRegex(logs_cm.records[3].message, 'The CFS configuration layer at index 1 is not valid')
        self.assertRegex(logs_cm.records[4].message,
                         f'One or more layers is not valid in CFS configuration at index {self.index}')

    def test_validate_layers_playbook_present_cfs_v3(self):
        """Test validate function when layers have playbooks and we are using the CFS v3 API"""
        mock_cfs_v3_client = Mock(spec=CFSV3Client)
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, mock_cfs_v3_client, self.mock_product_catalog)
        config.validate()

    def test_validate_layers_missing_playbook_cfs_v2(self):
        """Test validate function when layers are missing playbooks and we are using the CFS v2 API"""
        mock_cfs_v2_client = Mock(spec=CFSV2Client)
        self.config_data['layers'][0].pop('playbook')
        self.config_data['layers'][1].pop('playbook')
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, mock_cfs_v2_client, self.mock_product_catalog)
        config.validate()

    def test_validate_layers_playbook_present_cfs_v2(self):
        """Test validate function when layers have playbooks and we are using the CFS v2 API"""
        mock_cfs_v2_client = Mock(spec=CFSV2Client)
        config = InputConfiguration(self.config_data, self.mock_instance, self.index,
                                    self.jinja_env, mock_cfs_v2_client, self.mock_product_catalog)
        config.validate()


if __name__ == '__main__':
    unittest.main()
