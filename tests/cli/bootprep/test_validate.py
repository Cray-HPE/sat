"""
Unit tests for validation of bootprep input file based on the schema

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
from copy import deepcopy
import unittest
from unittest.mock import patch

from sat.cli.bootprep.errors import BootPrepValidationError
from sat.cli.bootprep.validate import (
    load_bootprep_schema,
    validate_instance
)
from tests.common import ExtendedTestCase

COMPUTE_CONFIG_IMAGE_NAME = 'compute-shasta-1.4.2'
UAN_CONFIG_IMAGE_NAME = 'uan-shasta-1.4.2'

VALID_CONFIG_LAYER_PRODUCT_VERSION = {
    'name': 'sma-1.4.2',
    'product': {
        'name': 'sma',
        'version': '1.4.2'
    }
}

VALID_CONFIG_LAYER_PRODUCT_BRANCH = {
    'name': 'cos-integration-2.0.38',
    'product': {
        'name': 'cos',
        'branch': 'integration'
    }
}

VALID_CONFIG_LAYER_GIT_BRANCH = {
    'name': 'cpe',
    'git': {
        'url': 'https://api-gw-service-nmn.local/vcs/cray/cpe-config-management.git',
        'branch': 'integration'
    }
}

VALID_CONFIG_LAYER_GIT_COMMIT = {
    'name': 'analytics',
    'git': {
        'url': 'https://api-gw-service-nmn.local/vcs/cray/analytics-config-management.git',
        'commit': '323fae03f4606ea9991df8befbb2fca795e648fa'
    }
}

VALID_IMAGE_IMS_NAME_WITH_CONFIG = {
    'name': 'compute-shasta-sles15sp1-1.4.2',
    'ims': {
        'is_recipe': True,
        'name': 'cray-shasta-compute-sles15sp1.x86_64-1.4.80'
    },
    'configuration': COMPUTE_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Compute', 'Compute_GPU']
}

VALID_IMAGE_IMS_ID_WITH_CONFIG = {
    'name': 'uan-shasta-sles15sp1-1.4.2',
    'ims': {
        'is_recipe': True,
        'id': '4744ccb8-fce6-4e2b-84f5-393b86cbafde'
    },
    'configuration': UAN_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Application', 'Application_UAN']
}

VALID_SESSION_TEMPLATE_COMPUTE = {
    'name': COMPUTE_CONFIG_IMAGE_NAME,
    'image': 'compute-shasta-sles15sp1-1.4.2',
    'configuration': COMPUTE_CONFIG_IMAGE_NAME,
    'bos_parameters': {
        'boot_sets': {
            'compute': {
                'kernel_parameters': 'console=ttyS0,115200 bad_page=panic crashkernel=340M',
                'node_roles_groups': ['Compute'],
                'rootfs_provider': 'cpss3',
                'rootfs_provider_passthrough': 'dvs:api-gw-service-nmn.local:300:nmn0'
            }
        }
    }
}

VALID_SESSION_TEMPLATE_UAN = {
    'name': UAN_CONFIG_IMAGE_NAME,
    'image': 'uan-shasta-sles15sp1-1.4.2',
    'configuration': UAN_CONFIG_IMAGE_NAME,
    'bos_parameters': {
        'boot_sets': {
            'uan': {
                'kernel_parameters': 'console=ttyS0,115200 bad_page=panic crashkernel=340M',
                'node_list': ['x3000c0s19b0n0', 'x3000c0s24b0n0'],
                'rootfs_provider': 'cpss3',
                'rootfs_provider_passthrough': 'dvs:api-gw-service-nmn.local:300:nmn0'
            }
        }
    }
}

VALID_COMPUTE_CONFIGURATION = {
    'name': COMPUTE_CONFIG_IMAGE_NAME,
    'layers': [
        VALID_CONFIG_LAYER_PRODUCT_VERSION,
        VALID_CONFIG_LAYER_PRODUCT_BRANCH,
        VALID_CONFIG_LAYER_GIT_BRANCH,
        VALID_CONFIG_LAYER_GIT_COMMIT
    ]
}

VALID_UAN_CONFIGURATION = {
    'name': UAN_CONFIG_IMAGE_NAME,
    'layers': [
        VALID_CONFIG_LAYER_PRODUCT_VERSION,
        VALID_CONFIG_LAYER_GIT_BRANCH
    ]
}


class TestValidateInstance(ExtendedTestCase):
    """Tests for the validate_instance function."""

    @classmethod
    def setUpClass(cls):
        """Load the schema validator from file.

        This is only needed once for all tests in this class since these tests
        do not modify the schema_validator.
        """
        cls.schema_validator = load_bootprep_schema()

    def assert_valid_instance(self, instance):
        """Helper assertion for asserting instance validates.

        This is preferable to just letting the exceptions raise because if an
        unexpected exception occurs in a unit test, it is treated as an error,
        but we want to treat any unexpected validation errors as a test failure
        because the schema validator is reporting a valid schema is invalid.

        Args:
            instance: The instance to assert is valid.
        """
        try:
            validate_instance(instance, self.schema_validator)
        except BootPrepValidationError as err:
            self.fail(f'validate_instance failed to validate a valid '
                      f'instance with error: {err}')

    def assert_invalid_instance(self, instance, expected_errs=None):
        """Assert that the given instance is invalid

        Args:
            instance: The instance to assert is invalid
            expected_errs (list of tuple): A list of tuples describing
                the expected validation errors. Each tuple should be
                of the form:

                    (path, msg, level)

                where path is a tuple describing the path where the
                error was expected, msg is a substring that should
                appear in the error message, and level is the expected
                indentation level of the message.
        """
        if expected_errs is None:
            expected_errs = []

        with self.assertRaises(BootPrepValidationError) as cm:
            validate_instance(instance, self.schema_validator)

        val_err = cm.exception

        for path, msg, level in expected_errs:
            path_str = ''.join(fr'\[{repr(p)}\]' for p in path)
            indent = (' ' * 4) * level
            regex_str = fr'{indent}{path_str}:.*{msg}'
            self.assert_regex_matches_element(regex_str,
                                              str(val_err).splitlines())

    def test_valid_config_product_version(self):
        """Valid configuration with a layer with product and version"""
        instance = {
            'configurations': [{
                'name': 'valid-config-product-version-layer',
                'layers': [VALID_CONFIG_LAYER_PRODUCT_VERSION]
            }]
        }
        self.assert_valid_instance(instance)

    def test_valid_config_product_branch(self):
        """Valid configuration with a layer with product and branch"""
        instance = {
            'configurations': [{
                'name': 'valid-config-product-branch-layer',
                'layers': [VALID_CONFIG_LAYER_PRODUCT_BRANCH]
            }]
        }
        self.assert_valid_instance(instance)

    def test_valid_config_product_version_branch(self):
        """Valid configuration with a layer with product and branch and version"""
        layer = deepcopy(VALID_CONFIG_LAYER_PRODUCT_VERSION)
        layer['product']['branch'] = 'integration'
        instance = {
            'configurations': [{
                'name': 'valid-config-product-branch-version-layer',
                'layers': [layer]
            }]
        }
        self.assert_valid_instance(instance)

    def test_valid_config_product_playbook(self):
        """Valid configuration with a product layer that specifies a playbook"""
        layer = deepcopy(VALID_CONFIG_LAYER_PRODUCT_VERSION)
        layer['playbook'] = 'site.yml'
        instance = {
            'configurations': [{
                'name': 'valid-config-product-branch-version-layer',
                'layers': [layer]
            }]
        }
        self.assert_valid_instance(instance)

    def test_valid_config_git_commit(self):
        """Valid configuration with a layer with git commit"""
        instance = {
            'configurations': [{
                'name': 'valid-config-git-commit-layer',
                'layers': [VALID_CONFIG_LAYER_GIT_COMMIT]
            }]
        }
        self.assert_valid_instance(instance)

    def test_valid_config_git_branch(self):
        """Valid configuration with a layer with a git branch"""
        instance = {
            'configurations': [{
                'name': 'valid-config-git-branch-layer',
                'layers': [VALID_CONFIG_LAYER_GIT_BRANCH]
            }]
        }
        self.assert_valid_instance(instance)

    def test_valid_config_git_playbook(self):
        """Valid configuration with a git layer that specifies a playbook"""
        layer = deepcopy(VALID_CONFIG_LAYER_GIT_BRANCH)
        layer['playbook'] = 'site.yml'
        instance = {
            'configurations': [{
                'name': 'valid-config-product-layer-playbook',
                'layers': [layer]
            }]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_name_with_config(self):
        """Valid image by name with config specified"""
        instance = {
            'images': [VALID_IMAGE_IMS_NAME_WITH_CONFIG]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_name_without_config(self):
        """Valid image by name without config specified"""
        image = deepcopy(VALID_IMAGE_IMS_NAME_WITH_CONFIG)
        del image['configuration']
        del image['configuration_group_names']
        instance = {
            'images': [VALID_IMAGE_IMS_NAME_WITH_CONFIG],
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_id_with_config(self):
        """Valid image by id with config specified"""
        instance = {
            'images': [VALID_IMAGE_IMS_ID_WITH_CONFIG]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_roles(self):
        """Valid session template with node_roles_groups"""
        instance = {
            'session_templates': [VALID_SESSION_TEMPLATE_COMPUTE]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_nodes(self):
        """Valid session template with node_list"""
        instance = {
            'session_templates': [VALID_SESSION_TEMPLATE_UAN]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_node_groups(self):
        """Valid session template with node_list"""
        session_template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE)
        boot_set = session_template['bos_parameters']['boot_sets']['compute']
        del boot_set['node_roles_groups']
        boot_set['node_groups'] = ['compute']
        instance = {
            'session_templates': [session_template]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_all_properties(self):
        """Valid session template with all possible properties"""
        session_template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE)
        boot_set = session_template['bos_parameters']['boot_sets']['compute']
        boot_set['node_list'] = ['x1000c0s0b0n0', 'x1000c0s0b0n1']
        boot_set['node_groups'] = ['compute_x86', 'compute_aarch']
        instance = {
            'session_templates': [session_template]
        }
        self.assert_valid_instance(instance)

    def test_valid_full_instance(self):
        """Valid instance with configurations, images, and session_templates"""
        instance = {
            'configurations': [
                VALID_COMPUTE_CONFIGURATION,
                VALID_UAN_CONFIGURATION
            ],
            'images': [
                VALID_IMAGE_IMS_ID_WITH_CONFIG,
                VALID_IMAGE_IMS_NAME_WITH_CONFIG
            ],
            'session_templates': [
                VALID_SESSION_TEMPLATE_COMPUTE,
                VALID_SESSION_TEMPLATE_UAN
            ]
        }
        self.assert_valid_instance(instance)

    def test_valid_empty(self):
        """Valid instance without configurations, images, or session_templates properties"""
        self.assert_valid_instance({})

    def test_valid_empty_lists(self):
        """Valid instance with empty lists for all property values"""
        instance = {
            'configurations': [],
            'images': [],
            'session_templates': []
        }
        self.assert_valid_instance(instance)

    def test_invalid_configurations_not_array(self):
        """Invalid instance with non-array configurations value"""
        instance = {
            'configurations': VALID_COMPUTE_CONFIGURATION
        }
        expected_errs = [
            (('configurations',), "is not of type 'array'", 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)


class TestLoadAndValidateInstance(unittest.TestCase):
    """Tests for the load_and_validate_instance function."""

    def setUp(self):
        """Mock the open function and yaml.safe_load"""
        self.mock_open = patch('builtins.open').start()
        self.mock_yaml_load = patch('sat.cli.bootprep.validate.safe_load').start()

        self.input_file_path = 'input.yaml'

    def tearDown(self):
        patch.stopall()

    def assert_file_opened_and_loaded(self):
        """Helper function to assert input file opened and loaded."""
        pass


if __name__ == '__main__':
    unittest.main()
