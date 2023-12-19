#
# MIT License
#
# (C) Copyright 2021-2023 Hewlett Packard Enterprise Development LP
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
from copy import deepcopy
import logging
import unittest
from unittest.mock import Mock, patch
from urllib.parse import urlparse

from cray_product_catalog.query import ProductCatalogError
from csm_api_client.service.vcs import VCSError
from jinja2.sandbox import SandboxedEnvironment

from csm_api_client.service.cfs import CFSClient
from sat.cli.bootprep.errors import InputItemCreateError
from sat.cli.bootprep.input.configuration import (
    AdditionalInventory,
    InputConfigurationLayer,
    GitInputConfigurationLayer,
    ProductInputConfigurationLayer,
    InputConfiguration,
    LATEST_VERSION_VALUE
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
        self.mock_product_catalog = Mock()
        self.mock_jinja_env = Mock()

    def tearDown(self):
        patch.stopall()

    def test_get_configuration_layer_git(self):
        """Test the get_configuration_layer static method with a git layer"""
        # Just needs a 'git' key; we're mocking the GitInputConfigurationLayer class
        layer_data = {'git': {}}
        layer = InputConfigurationLayer.get_configuration_layer(layer_data, self.mock_jinja_env,
                                                                self.mock_product_catalog)
        self.assertEqual(self.mock_git_layer.return_value, layer)

    def test_get_configuration_layer_product(self):
        """Test the get_configuration_layer static method with a product layer"""
        layer_data = {'product': {}}
        layer = InputConfigurationLayer.get_configuration_layer(layer_data, self.mock_jinja_env,
                                                                self.mock_product_catalog)
        self.assertEqual(self.mock_product_layer.return_value, layer)

    def test_get_configuration_layer_unknown(self):
        """Test the get_configuration_layer static method with bad layer data"""
        # All that matters is that it does not have a 'product' or 'git' key
        # This should never happen in practice because input files are validated against
        # a JSON schema that requires either the 'git' or 'product' keys.
        layer_data = {'unknown': {}}
        expected_err = 'Unrecognized type of configuration layer'
        with self.assertRaisesRegex(ValueError, expected_err):
            InputConfigurationLayer.get_configuration_layer(layer_data, self.mock_jinja_env,
                                                            self.mock_product_catalog)


class TestInputConfigurationLayerBase(unittest.TestCase):

    module_path = 'sat.cli.bootprep.input.configuration'

    def setUp(self):
        """Patch the resolve_branches class attribute on InputConfigurationLayer"""
        self.patch_resolve_branches(False).start()

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
        self.mock_vcs_repo = patch(f'{self.module_path}.VCSRepo').start()
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = self.branch_head_commit

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
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertEqual(self.playbook, layer.playbook)

    def test_playbook_property_not_present(self):
        """Test the playbook property when a playbook is not in the layer data"""
        del self.branch_layer_data['playbook']
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertIsNone(layer.playbook)

    def test_playbook_property_jinja_template(self):
        """Test the playbook property when the playbook uses Jinja2 templating"""
        self.branch_layer_data['playbook'] = 'shs_{{shs.network_type}}_install.yaml'
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertEqual(f'shs_{self.mock_network_type}_install.yaml', layer.playbook)

    def test_name_property_present(self):
        """Test the name property when the name is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertEqual(self.branch_layer_data['name'], layer.name)

    def test_name_property_not_present(self):
        """Test the name property when the name is not in the layer data"""
        del self.branch_layer_data['name']
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertIsNone(layer.name)

    def test_name_property_jinja_template(self):
        """Test the name property when the name uses Jinja2 templating"""
        self.branch_layer_data['name'] = 'sat-ncn-{{sat.version}}'
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertEqual(f'sat-ncn-{self.mock_sat_version}', layer.name)

    def test_clone_url_property(self):
        """Test the clone_url property."""
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertEqual(self.branch_layer_data['git']['url'], layer.clone_url)

    def test_branch_property_present(self):
        """Test the branch property when the branch is in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertEqual(self.branch_layer_data['git']['branch'], layer.branch)

    def test_branch_property_not_present(self):
        """Test the branch property when the branch is not in the layer data"""
        layer = GitInputConfigurationLayer(self.commit_layer_data, self.jinja_env)
        self.assertIsNone(layer.branch)

    def test_branch_property_jinja_template(self):
        """Test the branch property when the branch uses Jinja2 templating"""
        self.branch_layer_data['git']['branch'] = 'integration-{{sat.version}}'
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertEqual(f'integration-{self.mock_sat_version}', layer.branch)

    def test_commit_property_present(self):
        """Test the commit property when the commit is in the layer data"""
        layer = GitInputConfigurationLayer(self.commit_layer_data, self.jinja_env)
        self.assertEqual(self.commit_layer_data['git']['commit'], layer.commit)

    def test_commit_property_not_present(self):
        """Test the commit property when the commit is not in the layer data"""
        layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        self.assertIsNone(layer.commit)

    def test_get_cfs_api_data_optional_properties(self):
        """Test get_create_item_data method with optional name and playbook properties present."""
        branch_layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
        commit_layer = GitInputConfigurationLayer(self.commit_layer_data, self.jinja_env)
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

    def test_get_cfs_api_data_special_parameters(self):
        """Test get_create_item_data method with special_parameters present."""
        layer_data = deepcopy(self.branch_layer_data)
        require_dkms = True
        layer_data['special_parameters'] = {'ims_require_dkms': require_dkms}
        layer = GitInputConfigurationLayer(layer_data, self.jinja_env)

        expected_api_data = deepcopy(layer_data)
        # Move these values to where CFS expects them
        expected_api_data['cloneUrl'] = expected_api_data['git']['url']
        expected_api_data['branch'] = expected_api_data['git']['branch']
        del expected_api_data['git']
        expected_api_data['specialParameters'] = {'imsRequireDkms': require_dkms}
        del expected_api_data['special_parameters']

        self.assertEqual(expected_api_data, layer.get_cfs_api_data())

    def test_commit_property_branch_commit_lookup(self):
        """Test looking up commit hash from branch in VCS when branch not supported in CSM"""
        with self.patch_resolve_branches(True):
            layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
            self.assertEqual(layer.commit, self.branch_head_commit)

    def test_commit_property_branch_commit_vcs_query_fails(self):
        """Test looking up commit hash raises InputItemCreateError when VCS is inaccessible"""
        with self.patch_resolve_branches(True):
            layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
            self.mock_vcs_repo.return_value.get_commit_hash_for_branch.side_effect = VCSError
            with self.assertRaises(InputItemCreateError):
                _ = layer.commit

    def test_commit_property_branch_commit_lookup_fails(self):
        """Test looking up commit hash for nonexistent branch when branch not supported in CSM"""
        with self.patch_resolve_branches(True):
            layer = GitInputConfigurationLayer(self.branch_layer_data, self.jinja_env)
            self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = None
            with self.assertRaises(InputItemCreateError):
                _ = layer.commit


class TestProductInputConfigurationLayer(TestInputConfigurationLayerBase):
    """Tests for the ProductInputConfigurationLayer class."""

    def setUp(self):
        """Mock K8s API to return fake product catalog data and set up layers"""
        super().setUp()

        # Minimal set of product catalog data needed for these tests
        self.old_url = 'https://vcs.local/vcs/cray/cos-config-management.git'
        self.old_commit = '82537e59c24dd5607d5f5d6f92cdff971bd9c615'
        self.new_url = 'https://vcs.local/vcs/cray/newcos-config-management.git'
        self.new_commit = '6b0d9d55d399c92abae08002e75b9a1ce002f917'
        self.product_name = 'cos'
        self.product_version = '2.1.50'

        self.old_cos = Mock(clone_url=self.old_url, commit=self.old_commit)
        self.new_cos = Mock(clone_url=self.new_url, commit=self.new_commit)

        def mock_get_product(product_name, product_version=None):
            if product_name != self.product_name:
                raise ProductCatalogError('Unknown product')
            elif product_version == self.product_version:
                return self.old_cos
            elif not product_version:
                return self.new_cos
            else:
                raise ProductCatalogError('Unknown version')

        self.mock_product_catalog = Mock()
        self.mock_product_catalog.get_product.side_effect = mock_get_product

        # Used to test variable substitution in Jinja2-templated fields
        self.jinja_env = SandboxedEnvironment()
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
        self.version_layer = ProductInputConfigurationLayer(self.version_layer_data,
                                                            self.jinja_env,
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
        self.branch_layer = ProductInputConfigurationLayer(self.branch_layer_data,
                                                           self.jinja_env,
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
        self.commit_layer = ProductInputConfigurationLayer(self.commit_layer_data,
                                                           self.jinja_env,
                                                           self.mock_product_catalog)

        self.branch_head_commit = 'e6bfdb28d44669c4317d6dc021c22a75cebb3bfb'
        self.mock_vcs_repo = patch(f'{self.module_path}.VCSRepo').start()
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = self.branch_head_commit

        self.mock_sat_config = {
            'api_gateway.host': 'api_gateway.nmn'
        }
        patch_configuration('get_config_value', side_effect=self.mock_sat_config.get).start()

    def tearDown(self):
        patch.stopall()

    def test_playbook_property_jinja_template(self):
        """Test the playbook property when the playbook uses Jinja2 templating"""
        self.branch_layer_data['playbook'] = 'shs_{{shs.network_type}}_install.yaml'
        layer = ProductInputConfigurationLayer(self.branch_layer_data, self.jinja_env,
                                               self.mock_product_catalog)
        self.assertEqual(f'shs_{self.mock_network_type}_install.yaml', layer.playbook)

    def test_product_name_property(self):
        """Test the product_name property"""
        self.assertEqual(self.product_name, self.version_layer.product_name)

    def test_product_version_property_present(self):
        """Test the product_version property when version is in the layer data"""
        self.assertEqual(self.product_version, self.version_layer.product_version)

    def test_product_version_property_not_present(self):
        """Test the product_version property when version is not in the layer data"""
        self.assertEqual(LATEST_VERSION_VALUE, self.branch_layer.product_version)

    def test_product_version_jinja_template(self):
        """Test the product_version property when it uses Jinja2 templating"""
        # Have to double the literal brackets that make up the Jinja2 variable reference
        self.version_layer_data['product']['version'] = '{{' + f'{self.product_name}.version' + '}}'

        layer = ProductInputConfigurationLayer(self.version_layer_data, self.jinja_env,
                                               self.mock_product_catalog)

        self.assertEqual(self.product_version, layer.product_version)

    def test_matching_product_explicit_version(self):
        """Test getting the matching InstalledProductVersion for an explict version."""
        self.assertEqual(self.old_cos, self.version_layer.matching_product)

    def test_matching_product_no_version(self):
        """Test getting the matching InstalledProductVersion for an assumed latest version."""
        self.assertEqual(self.new_cos, self.branch_layer.matching_product)

    def test_matching_product_latest_version(self):
        """Test getting the matching InstalledProductVersion for an explict latest version."""
        latest_layer_data = deepcopy(self.branch_layer_data)
        latest_layer_data['product']['version'] = LATEST_VERSION_VALUE
        latest_layer = ProductInputConfigurationLayer(latest_layer_data, self.jinja_env,
                                                      self.mock_product_catalog)
        self.assertEqual(self.new_cos, latest_layer.matching_product)

    def test_matching_product_no_product_catalog(self):
        """Test getting the matching InstalledProductVersion when the product catalog is missing."""
        layer = ProductInputConfigurationLayer(self.version_layer_data, self.jinja_env, None)
        err_regex = 'Product catalog data is not available'
        with self.assertRaisesRegex(InputItemCreateError, err_regex):
            _ = layer.matching_product

    def test_matching_product_software_inventory_error(self):
        """Test getting the matching InstalledProductVersion when there is software inventory failure."""
        sw_inv_err_msg = 'unable find configmap'
        self.mock_product_catalog.get_product.side_effect = ProductCatalogError(sw_inv_err_msg)
        err_regex = f'Unable to get product data from product catalog: {sw_inv_err_msg}'
        with self.assertRaisesRegex(InputItemCreateError, err_regex):
            _ = self.version_layer.matching_product

    def test_clone_url_present(self):
        """Test clone_url when present in product catalog data"""
        old_url_parsed = urlparse(self.old_url)
        new_url_parsed = urlparse(self.version_layer.clone_url)
        # All parts of the URL should be unchanged, except for the 'netloc' which should
        # be replaced with what is in the configuration.
        for attr in ('scheme', 'path', 'params', 'query', 'fragment'):
            self.assertEqual(getattr(old_url_parsed, attr), getattr(new_url_parsed, attr))
        self.assertEqual(new_url_parsed.netloc, self.mock_sat_config['api_gateway.host'])

    def test_clone_url_missing(self):
        """Test clone_url when missing from product catalog data"""
        self.old_cos.clone_url = None
        err_regex = (f"No clone URL present for version {self.product_version} of "
                     f"product {self.product_name}")

        with self.assertRaisesRegex(InputItemCreateError, err_regex):
            _ = self.version_layer.clone_url

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

        layer = ProductInputConfigurationLayer(self.branch_layer_data, self.jinja_env,
                                               self.mock_product_catalog)

        self.assertEqual(f'integration-{self.product_version}', layer.branch)

    def test_commit_property_branch_present(self):
        """Test the commit property when a branch is in the layer data"""
        self.assertIsNone(self.branch_layer.commit)

    def test_commit_property_branch_not_present(self):
        """Test the commit property when a branch is not in the layer data"""
        self.assertEqual(self.old_commit, self.version_layer.commit)

    def test_commit_property_branch_commit_lookup(self):
        """Test looking up commit hash from branch in VCS when branch not supported in CSM"""
        with self.patch_resolve_branches(True):
            self.assertEqual(self.branch_layer.commit, self.branch_head_commit)

    def test_commit_property_branch_commit_vcs_query_fails(self):
        """Test looking up commit hash raises InputItemCreateError when VCS is inaccessible"""
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.side_effect = VCSError
        with self.patch_resolve_branches(True):
            with self.assertRaises(InputItemCreateError):
                _ = self.branch_layer.commit

    def test_commit_property_branch_commit_lookup_fails(self):
        """Test looking up commit hash for nonexistent branch when branch not supported in CSM"""
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = None
        with self.patch_resolve_branches(True):
            with self.assertRaises(InputItemCreateError):
                _ = self.branch_layer.commit

    def test_commit_property_when_commit_specified_in_input(self):
        """Test the commit property when commit specified in the input file"""
        self.assertEqual(self.commit_layer.commit, self.commit)

    def test_commit_property_resolve_branches(self):
        """Test the commit property when resolving branches and commit specified in the input file"""
        with self.patch_resolve_branches(True):
            self.assertEqual(self.commit_layer.commit, self.commit)


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
        self.branch_head_commit = 'e64ef6c370166285e6a674724b74e912a3f4a21e'
        self.mock_vcs_repo = patch(f'{self.module_path}.VCSRepo').start()
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = self.branch_head_commit

    def test_clone_url_property(self):
        """Test the clone_url property of AdditionalInventory"""
        additional_inventory = AdditionalInventory(self.data_with_commit, self.jinja_env)
        self.assertEqual(self.repo_url, additional_inventory.clone_url)

    def test_commit_property_specified(self):
        """Test the commit property when specified"""
        additional_inventory = AdditionalInventory(self.data_with_commit, self.jinja_env)
        self.assertEqual(self.commit_hash, additional_inventory.commit)

    def test_commit_property_unspecified(self):
        """Test the commit property when not specified"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        self.assertIsNone(additional_inventory.commit)

    def test_commit_property_branch_commit_lookup(self):
        """Test looking up commit hash from branch in VCS when branch not supported in CSM"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        with self.patch_resolve_branches(True):
            self.assertEqual(additional_inventory.commit, self.branch_head_commit)

    def test_commit_property_no_resolve_branches(self):
        """Test that commit is None when branch is specified with no_resolve_branches"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        self.assertIsNone(additional_inventory.commit)

    def test_commit_property_vcs_query_fails(self):
        """Test looking up commit hash raises InputItemCreateError when VCS is inaccessible"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.side_effect = VCSError
        with self.patch_resolve_branches(True):
            with self.assertRaises(InputItemCreateError):
                _ = additional_inventory.commit

    def test_commit_property_branch_lookup_fails(self):
        """Test looking up commit hash for nonexistent branch"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        self.mock_vcs_repo.return_value.get_commit_hash_for_branch.return_value = None
        with self.patch_resolve_branches(True):
            with self.assertRaises(InputItemCreateError):
                _ = additional_inventory.commit

    def test_branch_property_specified(self):
        """"Test the branch property when specified"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        self.assertEqual(self.branch, additional_inventory.branch)

    def test_branch_property_not_specified(self):
        """"Test the branch property when not specified"""
        additional_inventory = AdditionalInventory(self.data_with_commit, self.jinja_env)
        self.assertIsNone(additional_inventory.branch)

    def test_name_property_specified(self):
        """Test the name property when specified"""
        additional_inventory = AdditionalInventory(self.data_with_name, self.jinja_env)
        self.assertEqual(self.name, additional_inventory.name)

    def test_name_property_not_specified(self):
        """Test the name property when not specified"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        self.assertIsNone(additional_inventory.name)

    def test_get_cfs_api_data_branch_no_resolve_branches(self):
        """Test the get_cfs_api_data method with branch and name specified and no_resolve_branches"""
        additional_inventory = AdditionalInventory(self.data_with_name, self.jinja_env)
        expected = {'name': self.name, 'branch': self.branch, 'cloneUrl': self.repo_url}
        self.assertEqual(expected, additional_inventory.get_cfs_api_data())

    def test_get_cfs_api_data_branch_resolved(self):
        """Test the get_cfs_api_data method with branch resolved to a commit hash"""
        additional_inventory = AdditionalInventory(self.data_with_branch, self.jinja_env)
        expected = {'commit': self.branch_head_commit, 'cloneUrl': self.repo_url}
        with self.patch_resolve_branches(True):
            self.assertEqual(expected, additional_inventory.get_cfs_api_data())

    def test_get_cfs_api_data_commit(self):
        """Test the get_cfs_api_data method with commit specified"""
        additional_inventory = AdditionalInventory(self.data_with_commit, self.jinja_env)
        expected = {'commit': self.commit_hash, 'cloneUrl': self.repo_url}
        self.assertEqual(expected, additional_inventory.get_cfs_api_data())


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
        self.mock_cfs_client = Mock(spep=CFSClient)

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
        self.mock_additional_inventory_cls.assert_called_once_with(additional_inventory_data, self.jinja_env)
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
                                                                   self.jinja_env)
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


if __name__ == '__main__':
    unittest.main()
