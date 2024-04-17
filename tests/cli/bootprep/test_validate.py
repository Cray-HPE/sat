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
Unit tests for validation of bootprep input file based on the schema
"""
from copy import deepcopy
import logging
import unittest
from unittest.mock import mock_open, patch, Mock

from sat.cli.bootprep.errors import (
    BootPrepInternalError,
    BootPrepValidationError,
    ValidationErrorCollection
)
from sat.cli.bootprep.validate import (
    load_and_validate_instance,
    load_bootprep_schema,
    validate_instance,
    validate_instance_schema_version
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
    },
    'special_parameters': {
        'ims_require_dkms': True
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
    },
    'special_parameters': {
        'ims_require_dkms': True
    }
}

VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1 = {
    'name': 'compute-shasta-sles15sp1-1.4.2',
    'ims': {
        'is_recipe': True,
        'name': 'cray-shasta-compute-sles15sp1.x86_64-1.4.80'
    },
    'configuration': COMPUTE_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Compute', 'Compute_GPU']
}

VALID_IMAGE_IMS_ID_WITH_CONFIG_V1 = {
    'name': 'uan-shasta-sles15sp1-1.4.2',
    'ims': {
        'is_recipe': True,
        'id': '4744ccb8-fce6-4e2b-84f5-393b86cbafde'
    },
    'configuration': UAN_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Application', 'Application_UAN']
}

VALID_IMAGE_IMS_NAME_WITH_CONFIG_V2 = {
    'name': 'compute-shasta-sles15sp1-1.4.2',
    'base': {
        'ims': {
            'type': 'recipe',
            'name': 'cray-shasta-compute-sles15sp1.x86_64-1.4.80'
        }
    },
    'configuration': COMPUTE_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Compute', 'Compute_GPU']
}

VALID_IMAGE_IMS_ID_WITH_CONFIG_V2 = {
    'name': 'uan-shasta-sles15sp1-1.4.2',
    'base': {
        'ims': {
            'type': 'image',
            'id': '4744ccb8-fce6-4e2b-84f5-393b86cbafde'
        }
    },
    'configuration': UAN_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Application', 'Application_UAN']
}

VALID_IMAGE_PRODUCT_WITH_CONFIG = {
    'name': 'compute-{{ base.name }}',
    'ref_name': 'cos-compute-image',
    'base': {
        'product': {
            'type': 'recipe',
            'name': 'cos',
            'version': '2.2.101'
        }
    },
    'configuration': COMPUTE_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Compute', 'Compute_GPU']
}

VALID_IMAGE_PRODUCT_WITH_PREFIX_AND_CONFIG = deepcopy(VALID_IMAGE_PRODUCT_WITH_CONFIG)
VALID_IMAGE_PRODUCT_WITH_PREFIX_AND_CONFIG['base']['product']['filter'] = {'prefix': 'cray-shasta-compute'}

VALID_IMAGE_PRODUCT_WITH_WILDCARD_AND_CONFIG = deepcopy(VALID_IMAGE_PRODUCT_WITH_CONFIG)
VALID_IMAGE_PRODUCT_WITH_WILDCARD_AND_CONFIG['base']['product']['filter'] = {'wildcard': '*compute*'}

VALID_IMAGE_PRODUCT_WITH_ARCH_AND_CONFIG = deepcopy(VALID_IMAGE_PRODUCT_WITH_CONFIG)
VALID_IMAGE_PRODUCT_WITH_ARCH_AND_CONFIG['base']['product']['filter'] = {'arch': 'x86_64'}

VALID_IMAGE_REF_WITH_CONFIG = {
    'name': 'compute-{{ base.name }}',
    'ref_name': 'compute-cos-image',
    'base': {
        'image_ref': 'cos-image'
    },
    'configuration': COMPUTE_CONFIG_IMAGE_NAME,
    'configuration_group_names': ['Compute', 'Compute_GPU']
}

VALID_SESSION_TEMPLATE_COMPUTE_V1 = {
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


VALID_SESSION_TEMPLATE_COMPUTE_V2 = {
    'name': COMPUTE_CONFIG_IMAGE_NAME,
    'image': {
        'ims': {
            'name': 'compute-shasta-sles15sp1-1.4.2'
        }
    },
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

VALID_SESSION_TEMPLATE_UAN_V2 = {
    'name': UAN_CONFIG_IMAGE_NAME,
    'image': {
        'ims': {
            'id': 'some-uuid'
        }
    },
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


VALID_CONFIG_ADDITIONAL_INV_COMMIT = {
    'name': 'config-with-additional-inventory-commit',
    'layers': [],
    'additional_inventory': {
        'url': 'https://api-gw-service-nmn.local/vcs/cray/additional_inventory.git',
        'commit': '257cc5642cb1a054f08cc83f2d943e56fd3ebe99'
    }
}

VALID_CONFIG_ADDITIONAL_INV_BRANCH = {
    'name': 'config-with-additional-inventory-branch',
    'layers': [],
    'additional_inventory': {
        'url': 'https://api-gw-service-nmn.local/vcs/cray/additional_inventory.git',
        'branch': 'main'
    }
}

NOT_VALID_ANY_OF_MESSAGE = "Not valid under any of the given schemas"
NOT_OF_TYPE_ARRAY_MESSAGE = "is not of type 'array'"
NOT_OF_TYPE_STRING_MESSAGE = "is not of type 'string'"


class TestBootprepSchema(unittest.TestCase):
    """Test whether the bootprep_schema.yaml is valid in JSON Schema."""

    def test_bootprep_schema_is_valid_json_schema(self):
        """Test that the bootprep_schema.yaml is still valid against the JSON Schema metaschema"""
        try:
            load_bootprep_schema()
        except BootPrepInternalError as e:
            self.fail(f'Bootprep Schema file invalid against JSON Schema metaschema: {e}')


class TestValidateInstanceSchemaVersion(unittest.TestCase):
    """Tests for the validate_instance_schema_version function."""

    def setUp(self):
        self.current_schema_version = '2.1.4'
        self.mock_schema_validator = Mock()
        self.mock_schema_validator.schema = {'version': self.current_schema_version}

    def assert_valid_schema_version(self, version=None):
        """Assert that the given schema version is valid.

        Args:
            version (str, optional): the schema version to use in the input instance
        """
        try:
            validate_instance_schema_version({'schema_version': version} if version else {},
                                             self.mock_schema_validator)
        except BootPrepValidationError as err:
            self.fail(f'Expected valid schema version failed to validate: {err}')

    def assert_invalid_schema_version(self, version=None):
        """Assert that the given schema version is invalid.

        Args:
            version (str, optional): the schema version to use in the input instance.
        """
        with self.assertRaises(BootPrepValidationError):
            validate_instance_schema_version({'schema_version': version} if version else {},
                                             self.mock_schema_validator)

    def test_equal_schema_version(self):
        """Test validate_instance_schema_version with equal version."""
        self.assert_valid_schema_version(self.current_schema_version)

    def test_older_major_schema_version(self):
        """Test validate_instance_schema_version with older major version."""
        self.assert_invalid_schema_version('1.0.5')

    def test_older_minor_schema_version(self):
        """Test validate_instance_schema_version with older minor version."""
        with self.assertLogs(level=logging.WARNING):
            self.assert_valid_schema_version('2.0.1')

    def test_older_patch_schema_version(self):
        """Test validate_instance_schema_version with older minor version."""
        self.assert_valid_schema_version('2.1.0')

    def test_newer_schema_version(self):
        """Test validate_instance_schema_version with a newer version."""
        self.assert_invalid_schema_version('4.2.0')

    def test_default_schema_version(self):
        """Test validate_instance_schema_version with no version specified."""
        def default_patch(version):
            """Patch the DEFAULT_INPUT_SCHEMA_VERSION."""
            return patch('sat.cli.bootprep.validate.DEFAULT_INPUT_SCHEMA_VERSION', version)

        with default_patch(self.current_schema_version):
            self.assert_valid_schema_version()

        with default_patch('9.9.9'):
            self.assert_invalid_schema_version()

    def test_malformed_schema_version(self):
        """Test validate_instance_schema_version with a malformed schema version."""
        invalid_schema_versions = ['1.2.3.4', '1.2.3-rc1', 'not-even-close']
        for invalid_version in invalid_schema_versions:
            with self.subTest(version=invalid_version):
                self.assert_invalid_schema_version(invalid_version)


class TestValidateInstance(ExtendedTestCase):
    """Tests for the validate_instance function."""

    @classmethod
    def setUpClass(cls):
        """Load the schema validator from file.

        This is only needed once for all tests in this class since these tests
        do not modify the schema_validator.
        """
        cls.schema_validator = load_bootprep_schema()

    def setUp(self):
        self.mock_validate_schema_version = patch('sat.cli.bootprep.validate'
                                                  '.validate_instance_schema_version').start()

    def tearDown(self):
        patch.stopall()

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

    def assert_invalid_instance(self, instance, expected_errs=None, match_num_errors=True):
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
            match_num_errors (bool): Whether the number of errors reported
                should match the number of top-level errors specified in
                expected_errs.
        """
        if expected_errs is None:
            expected_errs = []

        with self.assertRaises(ValidationErrorCollection) as cm:
            validate_instance(instance, self.schema_validator)

        val_err = cm.exception

        for path, msg, level in expected_errs:
            path_str = ''.join(fr'\[{repr(p)}\]' for p in path)
            indent = (' ' * 4) * level
            regex_str = fr'{indent}{path_str}:.*{msg}'
            self.assert_regex_matches_element(regex_str,
                                              str(val_err).splitlines())

        if match_num_errors:
            top_level_errors = [err for err in expected_errs if err[2] == 1]
            self.assertEqual(len(top_level_errors), len(val_err.errors),
                             'Number of reported errors does not match '
                             'expected number of errors')

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

    def test_valid_config_additional_inventory_commit(self):
        """Valid configuration with additional inventory that uses a commit"""
        instance = {
            'configurations': [VALID_CONFIG_ADDITIONAL_INV_COMMIT]
        }
        self.assert_valid_instance(instance)

    def test_valid_config_additional_inventory_branch(self):
        """Valid configuration with additional inventory that uses a branch"""
        instance = {
            'configurations': [VALID_CONFIG_ADDITIONAL_INV_BRANCH]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_name_with_config_v1(self):
        """Valid image from IMS by name with config specified (deprecated schema)"""
        instance = {
            'images': [VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_name_without_config_v1(self):
        """Valid image from IMS by name without config specified (deprecated schema)"""
        image = deepcopy(VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1)
        del image['configuration']
        del image['configuration_group_names']
        instance = {
            'images': [VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1],
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_id_with_config_v1(self):
        """Valid image from IMS by id with config specified (deprecated schema)"""
        instance = {
            'images': [VALID_IMAGE_IMS_ID_WITH_CONFIG_V1]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_name_with_config_v2(self):
        """Valid image from IMS by name with config specified (new schema)"""
        instance = {
            'images': [VALID_IMAGE_IMS_NAME_WITH_CONFIG_V2]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_name_without_config_v2(self):
        """Valid image from IMS by name without config specified (new schema)"""
        image = deepcopy(VALID_IMAGE_IMS_NAME_WITH_CONFIG_V2)
        del image['configuration']
        del image['configuration_group_names']
        instance = {
            'images': [VALID_IMAGE_IMS_NAME_WITH_CONFIG_V2],
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ims_id_with_config_v2(self):
        """Valid image from IMS by id with config specified (new schema)"""
        instance = {
            'images': [VALID_IMAGE_IMS_ID_WITH_CONFIG_V2]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_product_with_config(self):
        """Valid image from a version of a product with config specified"""
        instance = {
            'images': [VALID_IMAGE_PRODUCT_WITH_CONFIG]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_product_with_prefix_and_config(self):
        """Valid image from a version of a product with a prefix filter and config specified."""
        instance = {
            'images': [VALID_IMAGE_PRODUCT_WITH_PREFIX_AND_CONFIG]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_product_with_wildcard_and_config(self):
        """Valid image from a version of a product with a wildcard filter and config specified."""
        instance = {
            'images': [VALID_IMAGE_PRODUCT_WITH_WILDCARD_AND_CONFIG]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_product_with_arch_and_config(self):
        """Valid image from a version of a product with an arch filter and config specified."""
        instance = {
            'images': [VALID_IMAGE_PRODUCT_WITH_ARCH_AND_CONFIG]
        }
        self.assert_valid_instance(instance)

    def test_valid_image_ref_with_config(self):
        """Valid image using another image from bootprep input file as a base"""
        instance = {
            'images': [VALID_IMAGE_REF_WITH_CONFIG]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_v1(self):
        """Valid session template using the deprecated image schema"""
        instance = {
            'session_templates': [VALID_SESSION_TEMPLATE_COMPUTE_V1]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_roles(self):
        """Valid session template with node_roles_groups"""
        instance = {
            'session_templates': [VALID_SESSION_TEMPLATE_COMPUTE_V2]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_nodes(self):
        """Valid session template with node_list"""
        instance = {
            'session_templates': [VALID_SESSION_TEMPLATE_UAN_V2]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_node_groups(self):
        """Valid session template with node_list"""
        session_template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
        boot_set = session_template['bos_parameters']['boot_sets']['compute']
        del boot_set['node_roles_groups']
        boot_set['node_groups'] = ['compute']
        instance = {
            'session_templates': [session_template]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_all_properties(self):
        """Valid session template with all possible properties"""
        session_template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
        boot_set = session_template['bos_parameters']['boot_sets']['compute']
        boot_set['node_list'] = ['x1000c0s0b0n0', 'x1000c0s0b0n1']
        boot_set['node_groups'] = ['compute_x86', 'compute_aarch']
        instance = {
            'session_templates': [session_template]
        }
        self.assert_valid_instance(instance)

    def test_valid_session_template_boot_set_arch(self):
        """Valid session template with a valid arch specified for a boot set"""
        session_template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
        valid_arch_vals = ['X86', 'ARM', 'Other', 'Unknown']
        for valid_arch in valid_arch_vals:
            session_template['bos_parameters']['boot_sets']['compute']['arch'] = valid_arch
            instance = {
                'session_templates': [session_template]
            }
            self.assert_valid_instance(instance)

    def test_invalid_session_template_boot_set_arch(self):
        """Invalid session template with an invalid arch specified for a boot set"""
        session_template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
        invalid_arch_vals = ['aarch64', 'x86_64']
        for invalid_arch in invalid_arch_vals:
            session_template['bos_parameters']['boot_sets']['compute']['arch'] = invalid_arch
            instance = {
                'session_templates': [session_template]
            }
            expected_errs = [
                (('session_templates', 0, 'bos_parameters', 'boot_sets', 'compute', 'arch'),
                 f"'{invalid_arch}' is not one of", 1)
            ]
            self.assert_invalid_instance(instance, expected_errs)

    def test_valid_full_instance(self):
        """Valid instance with configurations, images, and session_templates"""
        instance = {
            'configurations': [
                VALID_COMPUTE_CONFIGURATION,
                VALID_UAN_CONFIGURATION
            ],
            'images': [
                VALID_IMAGE_IMS_ID_WITH_CONFIG_V2,
                VALID_IMAGE_IMS_NAME_WITH_CONFIG_V2
            ],
            'session_templates': [
                VALID_SESSION_TEMPLATE_COMPUTE_V2,
                VALID_SESSION_TEMPLATE_UAN_V2
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
            (('configurations',), NOT_OF_TYPE_ARRAY_MESSAGE, 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_images_not_array(self):
        """Invalid instance with non-array images value"""
        instance = {
            'images': VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1
        }
        expected_errs = [
            (('images',), NOT_OF_TYPE_ARRAY_MESSAGE, 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_session_templates_not_array(self):
        """Invalid instance with non-array session_templates value"""
        instance = {
            'session_templates': VALID_SESSION_TEMPLATE_COMPUTE_V2
        }
        expected_errs = [
            (('session_templates',), NOT_OF_TYPE_ARRAY_MESSAGE, 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_missing_layers(self):
        """Invalid configuration missing 'layers' key"""
        instance = {'configurations': [{'name': COMPUTE_CONFIG_IMAGE_NAME}]}
        expected_errs = [
            (('configurations', 0), "'layers' is a required property", 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_extra_property(self):
        """Invalid configuration with an extra property"""
        config = deepcopy(VALID_COMPUTE_CONFIGURATION)
        extra_key = 'something_strange'
        config[extra_key] = 'in the neighborhood'
        instance = {'configurations': [config]}
        expected_errs = [
            (('configurations', 0),
             fr"Additional properties are not allowed \('{extra_key}' was unexpected\)",
             1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_name_type(self):
        """Invalid instance with wrong type for a configuration's name"""
        configuration = {'name': ['a', 'b', 'c'], 'layers': []}
        instance = {'configurations': [configuration]}
        expected_errs = [
            (('configurations', 0, 'name'), NOT_OF_TYPE_STRING_MESSAGE, 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_layers_type(self):
        """Invalid instance with wrong type for a configuration's layers"""
        configuration = {'name': 'invalid-layers-config', 'layers': {}}
        instance = {'configurations': [configuration]}
        expected_errs = [
            (('configurations', 0, 'layers'), NOT_OF_TYPE_ARRAY_MESSAGE, 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    @staticmethod
    def get_instance_with_config_layer(layer):
        """Get an instance with a single configuration with a single layer."""
        return {
            'configurations': [
                {
                    'name': 'cpe-2.0.38',
                    'layers': [layer]
                }
            ]
        }

    def test_invalid_config_layer_missing_keys(self):
        """Invalid configuration layer missing 'git' and 'product' keys"""
        instance = self.get_instance_with_config_layer({'name': 'bad-layer'})
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            # The 'git' property is preferred because it's first in the schema
            (('configurations', 0, 'layers', 0), "'git' is a required property", 2),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_layer_both_keys(self):
        """Invalid configuration layer with both 'git' and 'product' keys"""
        layer = {
            'name': 'bad-layer',
            'product': VALID_CONFIG_LAYER_PRODUCT_VERSION['product'],
            'git': VALID_CONFIG_LAYER_GIT_BRANCH['git']
        }
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            # The 'git' property is preferred because it's first in the schema
            (('configurations', 0, 'layers', 0), "'product' was unexpected", 2),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_git_layer_extra_property(self):
        """Invalid configuration git layer with extra property"""
        layer = {
            'name': 'bad-layer',
            'git': VALID_CONFIG_LAYER_GIT_BRANCH['git'],
            'who_ya_gonna': 'call'
        }
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0), "'who_ya_gonna' was unexpected", 2),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_config_git_layer_name_type(self):
        """Invalid configuration git layer with bad type for 'name' property"""
        layer = deepcopy(VALID_CONFIG_LAYER_GIT_BRANCH)
        layer['name'] = False
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'name'), NOT_OF_TYPE_STRING_MESSAGE, 2),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_config_git_layer_url_commit_type(self):
        """Invalid configuration git layer with bad type for 'url' and 'commit' properties"""
        layer = deepcopy(VALID_CONFIG_LAYER_GIT_COMMIT)
        layer['git']['url'] = {}
        layer['git']['commit'] = 1
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'git'), NOT_VALID_ANY_OF_MESSAGE, 2),
            (('configurations', 0, 'layers', 0, 'git', 'url'), NOT_OF_TYPE_STRING_MESSAGE, 3),
            (('configurations', 0, 'layers', 0, 'git', 'commit'), NOT_OF_TYPE_STRING_MESSAGE, 3),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_config_git_layer_url_branch_type(self):
        """Invalid configuration git layer with bad type for 'url' and 'branch' properties"""
        layer = deepcopy(VALID_CONFIG_LAYER_GIT_BRANCH)
        layer['git']['url'] = False
        layer['git']['branch'] = True
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'git'), NOT_VALID_ANY_OF_MESSAGE, 2),
            (('configurations', 0, 'layers', 0, 'git', 'url'), NOT_OF_TYPE_STRING_MESSAGE, 3),
            (('configurations', 0, 'layers', 0, 'git', 'branch'), NOT_OF_TYPE_STRING_MESSAGE, 3),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_product_layer_extra_property(self):
        """Invalid configuration product layer with extra property"""
        layer = {
            'name': 'bad-layer',
            'product': VALID_CONFIG_LAYER_PRODUCT_VERSION['product'],
            'ghost': 'busters'
        }
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0), "'ghost' was unexpected", 2),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_config_product_layer_name_type(self):
        """Invalid configuration product layer with bad type for 'name' property"""
        layer = deepcopy(VALID_CONFIG_LAYER_PRODUCT_VERSION)
        layer['name'] = {'foo': 'bar'}
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'name'), NOT_OF_TYPE_STRING_MESSAGE, 2),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_config_product_layer_name_branch_type(self):
        """Invalid configuration product layer with bad type for 'name' and 'branch' properties"""
        layer = deepcopy(VALID_CONFIG_LAYER_PRODUCT_BRANCH)
        layer['product']['name'] = False
        layer['product']['branch'] = 42
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'product'), NOT_VALID_ANY_OF_MESSAGE, 2),
            (('configurations', 0, 'layers', 0, 'product', 'name'), NOT_OF_TYPE_STRING_MESSAGE, 3),
            (('configurations', 0, 'layers', 0, 'product', 'branch'), NOT_OF_TYPE_STRING_MESSAGE, 3),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_config_product_layer_name_version_type(self):
        """Invalid configuration product layer with bad type for 'name' and 'version' properties"""
        layer = deepcopy(VALID_CONFIG_LAYER_PRODUCT_BRANCH)
        layer['product']['name'] = 2
        layer['product']['version'] = 3
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'product'), NOT_VALID_ANY_OF_MESSAGE, 2),
            (('configurations', 0, 'layers', 0, 'product', 'name'), NOT_OF_TYPE_STRING_MESSAGE, 3),
            (('configurations', 0, 'layers', 0, 'product', 'version'), NOT_OF_TYPE_STRING_MESSAGE, 3),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_product_layer_missing_name(self):
        """Invalid configuration product layers with missing product 'name'"""
        layers = {
            'branch': VALID_CONFIG_LAYER_PRODUCT_BRANCH,
            'version': VALID_CONFIG_LAYER_PRODUCT_VERSION
        }
        for present_property, layer in layers.items():
            with self.subTest(present_property=present_property):
                bad_layer = deepcopy(layer)
                del bad_layer['product']['name']
                instance = self.get_instance_with_config_layer(bad_layer)
                expected_errs = [
                    (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
                    (('configurations', 0, 'layers', 0, 'product'), NOT_VALID_ANY_OF_MESSAGE, 2),
                    (('configurations', 0, 'layers', 0, 'product'), "'name' is a required property", 3)
                ]
                self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_product_layer_missing_version_branch(self):
        """Invalid configuration product layer missing either version or branch"""
        layer = deepcopy(VALID_CONFIG_LAYER_PRODUCT_VERSION)
        del layer['product']['version']
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'product'), NOT_VALID_ANY_OF_MESSAGE, 2),
            # The 'version' property is assumed because that subschema comes first
            (('configurations', 0, 'layers', 0, 'product'), "'version' is a required property", 3),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_git_layer_missing_url(self):
        """Invalid configuration git layers with missing git 'url'"""
        layers = {
            'commit': VALID_CONFIG_LAYER_GIT_COMMIT,
            'branch': VALID_CONFIG_LAYER_GIT_BRANCH
        }
        for present_property, layer in layers.items():
            with self.subTest(present_property=present_property):
                bad_layer = deepcopy(layer)
                del bad_layer['git']['url']
                instance = self.get_instance_with_config_layer(bad_layer)
                expected_errs = [
                    (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
                    (('configurations', 0, 'layers', 0, 'git'), NOT_VALID_ANY_OF_MESSAGE, 2),
                    (('configurations', 0, 'layers', 0, 'git'), "'url' is a required property", 3)
                ]
                self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_git_layer_commit_and_branch(self):
        """Invalid configuration git layer with commit and branch"""
        layer = deepcopy(VALID_CONFIG_LAYER_GIT_COMMIT)
        layer['git']['branch'] = 'integration'
        instance = self.get_instance_with_config_layer(layer)
        expected_errs = [
            (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('configurations', 0, 'layers', 0, 'git'), NOT_VALID_ANY_OF_MESSAGE, 2),
            # 'branch' is assumed to be extra because the 'commit' subschema comes first
            (('configurations', 0, 'layers', 0, 'git'), "'branch' was unexpected", 3)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_config_git_layer_extra_git_property(self):
        """Invalid configuration git layers with extra property under 'git' property"""
        layers = {
            'commit': VALID_CONFIG_LAYER_GIT_COMMIT,
            'branch': VALID_CONFIG_LAYER_GIT_BRANCH
        }
        for present_property, layer in layers.items():
            with self.subTest(present_property=present_property):
                bad_layer = deepcopy(layer)
                bad_layer['git']['good_news'] = 'everyone!'
                instance = self.get_instance_with_config_layer(bad_layer)
                expected_errs = [
                    (('configurations', 0, 'layers', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
                    (('configurations', 0, 'layers', 0, 'git'), NOT_VALID_ANY_OF_MESSAGE, 2),
                    (('configurations', 0, 'layers', 0, 'git'), "'good_news' was unexpected", 3)
                ]
                self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_ims_image_missing_name(self):
        """Invalid image missing properties"""
        missing_property = 'name'
        image = deepcopy(VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1)
        del image[missing_property]
        instance = {'images': [image]}
        expected_errs = [
            (('images', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            # 'base' property is first alternative and so is preferred
            (('images', 0), f"'{missing_property}' is a required property", 2)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_image_missing_configuration_group_names(self):
        """Invalid image with 'configuration' specified but no 'configuration_group_names'"""
        image = deepcopy(VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1)
        del image['configuration_group_names']
        instance = {'images': [image]}
        expected_errs = [
            (('images', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('images', 0), "'configuration_group_names' is a dependency of 'configuration'", 2)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_image_missing_ims_properties(self):
        """Invalid image missing properties beneath the 'ims' property"""
        # Two of these have the same missing property but are meant to fail against
        # separate subschemas of a 'oneOf' keyword, so use a list of tuples
        test_images = [
            # (property_to_remove, image)
            ('is_recipe', VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1),
            ('is_recipe', VALID_IMAGE_IMS_ID_WITH_CONFIG_V1),
            # Remove and assert that 'name' is missing because that subschema is first
            ('name', VALID_IMAGE_IMS_NAME_WITH_CONFIG_V1)
        ]
        for missing_property, image in test_images:
            bad_image = deepcopy(image)
            del bad_image['ims'][missing_property]

            with self.subTest(missing_property=missing_property,
                              present_properties=list(bad_image['ims'].keys())):
                instance = {'images': [bad_image]}
                expected_errs = [
                    (('images', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
                    (('images', 0, 'ims'), NOT_VALID_ANY_OF_MESSAGE, 2),
                    (('images', 0, 'ims'), f"'{missing_property}' is a required property", 3)
                ]
                self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_image_bad_types(self):
        """Invalid image with bad types"""
        instance = {
            'images': [
                {
                    'name': 6,
                    'configuration': 7,
                    'configuration_group_names': 8,
                    'ims': {
                        'is_recipe': 'bunch',
                        'name': 6
                    }
                }
            ]
        }
        expected_errs = [
            (('images', 0), NOT_VALID_ANY_OF_MESSAGE, 1),
            (('images', 0, 'name'), NOT_OF_TYPE_STRING_MESSAGE, 2),
            (('images', 0, 'configuration'), NOT_OF_TYPE_STRING_MESSAGE, 2),
            (('images', 0, 'configuration_group_names'), NOT_OF_TYPE_ARRAY_MESSAGE, 2),
            (('images', 0, 'ims'), NOT_VALID_ANY_OF_MESSAGE, 2),
            (('images', 0, 'ims', 'is_recipe'), "'bunch' is not of type 'boolean'", 3),
            (('images', 0, 'ims', 'name'), NOT_OF_TYPE_STRING_MESSAGE, 3),
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_session_template_types(self):
        """Invalid session templates with bad types"""
        string_properties = ['name', 'configuration']
        for bad_property in string_properties:
            with self.subTest(bad_property=bad_property):
                template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
                template[bad_property] = 42
                instance = {'session_templates': [template]}
                expected_errs = [
                    (('session_templates', 0, bad_property), NOT_OF_TYPE_STRING_MESSAGE, 1)
                ]
                self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_session_template_missing_property(self):
        """Invalid session templates with missing property"""
        missing_properties = ['name', 'image', 'configuration', 'bos_parameters']
        for missing_property in missing_properties:
            with self.subTest(missing_property=missing_property):
                template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
                del template[missing_property]
                instance = {'session_templates': [template]}
                expected_errs = [
                    (('session_templates', 0), f"'{missing_property}' is a required property", 1)
                ]
                self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_session_template_missing_boot_sets(self):
        """Invalid session template missing 'boot_sets' property"""
        template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
        template['bos_parameters'] = {}
        instance = {'session_templates': [template]}
        expected_errs = [
            (('session_templates', 0, 'bos_parameters'), "'boot_sets' is a required property", 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_session_template_empty_boot_sets(self):
        """Invalid session template with empty boot_sets object"""
        template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
        template['bos_parameters']['boot_sets'] = {}
        instance = {'session_templates': [template]}
        expected_errs = [
            (('session_templates', 0, 'bos_parameters', 'boot_sets'),
             "does not have enough properties", 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    # noinspection PyTypedDict
    def test_invalid_session_template_invalid_boot_sets_type(self):
        """Invalid session template with invalid type of 'boot_sets' property"""
        template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
        template['bos_parameters']['boot_sets'] = []
        instance = {'session_templates': [template]}
        expected_errs = [
            (('session_templates', 0, 'bos_parameters', 'boot_sets'),
             "not of type 'object'", 1)
        ]
        self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_session_template_invalid_node_types(self):
        """Invalid session template with invalid types of 'node_*' properties"""
        property_values = {
            'node_list': 'x3000c0s19b0n0',
            'node_roles_groups': 'Compute',
            'node_groups': 'nvidia'
        }
        for bad_property, bad_value in property_values.items():
            with self.subTest(bad_property=bad_property):
                template = deepcopy(VALID_SESSION_TEMPLATE_COMPUTE_V2)
                template['bos_parameters']['boot_sets']['compute'][bad_property] = bad_value
                instance = {'session_templates': [template]}
                expected_errs = [
                    (('session_templates', 0, 'bos_parameters', 'boot_sets', 'compute', bad_property),
                     f"'{bad_value}' is not of type 'array'", 1)
                ]
                self.assert_invalid_instance(instance, expected_errs)

    def test_invalid_schema_version(self):
        """Invalid schema version specified in bootprep input file."""
        err_msg = 'Incompatible schema version.'
        self.mock_validate_schema_version.side_effect = BootPrepValidationError(err_msg)

        with self.assertRaisesRegex(BootPrepValidationError, err_msg):
            validate_instance({}, self.schema_validator)


class TestLoadBootprepSchema(unittest.TestCase):
    """Tests for the load_bootprep_schema function"""

    def setUp(self):
        """Mock the pkgutil.get_data function"""
        self.mock_get_data = patch('pkgutil.get_data').start()

    def tearDown(self):
        patch.stopall()

    def test_unable_to_open_schema_file(self):
        """Test load_bootprep_schema when unable to open schema file"""
        errors_to_raise = [FileNotFoundError, PermissionError]
        for error in errors_to_raise:
            with self.subTest(error=error):
                self.mock_get_data.side_effect = error
                err_regex = 'Unable to open bootprep schema file'
                with self.assertRaisesRegex(BootPrepInternalError, err_regex):
                    load_bootprep_schema()

    def test_unable_to_find_package(self):
        """Test load_bootprep_schema when unable to find installed sat package"""
        self.mock_get_data.return_value = None
        err_regex = 'Unable to find installed sat package'
        with self.assertRaisesRegex(BootPrepInternalError, err_regex):
            load_bootprep_schema()

    def test_invalid_yaml(self):
        """Test load_bootprep_schema when the schema file has invalid YAML content"""
        self.mock_get_data.return_value = b'foo: bar: baz'
        err_regex = 'Invalid YAML in bootprep schema file'
        with self.assertRaisesRegex(BootPrepInternalError, err_regex):
            load_bootprep_schema()

    @patch('sat.cli.bootprep.validate.safe_load')
    def test_bad_schema(self, mock_safe_load):
        """Test load_bootprep_schema when the schema file is invalid JSON Schema"""
        mock_safe_load.return_value = {
            'schema': 'https://json-schema.org/draft-07/schema',
            'type': 'object',
            # JSON Schema's metaschema says properties should be an object not an array
            'properties': ['configurations', 'images', 'session_templates']
        }
        err_regex = 'bootprep schema file is invalid'
        with self.assertRaisesRegex(BootPrepInternalError, err_regex):
            load_bootprep_schema()


class TestLoadAndValidateInstance(unittest.TestCase):
    """Tests for the load_and_validate_instance function."""

    def setUp(self):
        """Mock validate_instance function"""
        self.mock_validate_instance = patch('sat.cli.bootprep.validate.validate_instance').start()
        self.instance_file_path = 'input.yaml'
        self.mock_schema_validator = Mock()

    def tearDown(self):
        patch.stopall()

    def assert_validate_instance_called(self, instance):
        """Helper to assert that the validate_instance function was called"""
        self.mock_validate_instance.assert_called_once_with(instance, self.mock_schema_validator)

    def assert_validate_instance_not_called(self):
        """Helper to assert that the validate_instance function was not called"""
        self.mock_validate_instance.assert_not_called()

    @patch('builtins.open')
    def test_unable_to_open_instance_file(self, mocked_open):
        """Test load_and_validate_instance when instance file can't be opened"""
        errors = [FileNotFoundError, PermissionError]
        for error in errors:
            with self.subTest(error=error):
                mocked_open.side_effect = error
                err_regex = 'Failed to open input file'
                with self.assertRaisesRegex(BootPrepValidationError, err_regex):
                    load_and_validate_instance(self.instance_file_path, self.mock_schema_validator)
                self.assert_validate_instance_not_called()

    @patch('builtins.open', mock_open(read_data='not: valid: yaml'))
    def test_bad_yaml_instance(self):
        """Test load_and_validate_instance when instance file contains bad YAML"""
        err_regex = f'Failed to load YAML from input file {self.instance_file_path}'
        with self.assertRaisesRegex(BootPrepValidationError, err_regex):
            load_and_validate_instance(self.instance_file_path, self.mock_schema_validator)
        self.assert_validate_instance_not_called()

    @patch('builtins.open', mock_open(read_data='valid: yaml'))
    def test_invalid_instance_schema(self):
        """Test load_and_validate_instance when instance does not validate against schema"""
        self.mock_validate_instance.side_effect = BootPrepValidationError
        with self.assertRaises(BootPrepValidationError):
            load_and_validate_instance(self.instance_file_path, self.mock_schema_validator)
        self.assert_validate_instance_called({'valid': 'yaml'})

    @patch('builtins.open', mock_open(read_data='{}'))
    def test_valid_instance_schema(self):
        """Test load_and_validate_instance when instance does validate against schema"""
        loaded_instance = load_and_validate_instance(self.instance_file_path,
                                                     self.mock_schema_validator)
        self.assert_validate_instance_called({})
        self.assertEqual({}, loaded_instance)


if __name__ == '__main__':
    unittest.main()
