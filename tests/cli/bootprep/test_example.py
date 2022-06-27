#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
Tests for sat.cli.bootprep.example
"""
import logging
import unittest
from unittest.mock import Mock, call, patch

from sat.cli.bootprep.example import (
    EXAMPLE_COS_CONFIG_NAME,
    EXAMPLE_UAN_CONFIG_NAME,
    ExampleConfigLayer,
    get_example_cos_and_uan_configs,
    get_example_cos_and_uan_data,
    get_example_cos_and_uan_images_session_templates,
    get_example_input_config_data,
    get_example_images_and_templates,
    get_product_recipe_names,
)
from sat.software_inventory.products import (
    InstalledProductVersion,
    ProductCatalog,
    SoftwareInventoryError
)


def mpatch(path, *args, **kwargs):
    """Convenience function to patch things in example module."""
    return patch(f'sat.cli.bootprep.example.{path}', *args, **kwargs)


class TestGetExampleInputConfigData(unittest.TestCase):

    def test_get_multiple_layers_config_data(self):
        """Test getting config data with multiple example layers."""
        config_name = 'cos-config'
        default_playbook = 'site.yml'
        special_playbook = 'special.yml'
        branch = 'integration'
        special_branch = 'master'
        cos_version = '2.0.1'
        analytics_version = '1.1.24'
        example_layers = [ExampleConfigLayer('cos', branch, default_playbook),
                          ExampleConfigLayer('cpe', special_branch, default_playbook),
                          ExampleConfigLayer('analytics', branch, special_playbook)]

        err_msg = 'No installed products with name cpe.'
        mock_product_catalog = Mock(spec=ProductCatalog)
        mock_product_catalog.get_product.side_effect = [
            Mock(spec=InstalledProductVersion, version=cos_version),
            SoftwareInventoryError(err_msg),
            Mock(spec=InstalledProductVersion, version=analytics_version)
        ]

        expected_data = {
            'name': config_name,
            'layers': [
                {
                    'name': f'cos-{branch}-{cos_version}',
                    'playbook': default_playbook,
                    'product': {'name': 'cos', 'version': cos_version, 'branch': branch}
                },
                {
                    'name': f'cpe-{special_branch}-latest',
                    'playbook': default_playbook,
                    'product': {'name': 'cpe', 'version': 'latest', 'branch': special_branch}
                },
                {
                    'name': f'analytics-{branch}-{analytics_version}',
                    'playbook': special_playbook,
                    'product': {'name': 'analytics', 'version': analytics_version, 'branch': branch}
                },
            ]
        }

        with self.assertLogs(level=logging.WARNING) as logs_cm:
            example_data = get_example_input_config_data(mock_product_catalog, config_name, example_layers)

        self.assertEqual(expected_data, example_data)
        self.assertEqual(1, len(logs_cm.records))
        expected_warning = f'Unable to determine latest version of product cpe: {err_msg}'
        self.assertEqual(expected_warning, logs_cm.records[0].message)


class TestGetExampleCOSAndUANConfigs(unittest.TestCase):
    """Test the get_example_cos_and_uan_configs function."""

    @mpatch('get_example_input_config_data')
    def test_get_example_cos_and_uan_configs(self, mock_get_example_data):
        """Test that get_example_cos_and_uan_configs gets input data for examples."""
        mock_product_catalog = Mock()
        mock_cos_layers = Mock()
        mock_uan_layers = Mock()
        mock_example_configs = {
            'cos-config': mock_cos_layers,
            'uan-config': mock_uan_layers
        }
        mock_cos_config_data = Mock()
        mock_uan_config_data = Mock()
        mock_get_example_data.side_effect = [mock_cos_config_data, mock_uan_config_data]

        with mpatch('EXAMPLE_CONFIGS', mock_example_configs):
            example_configs = get_example_cos_and_uan_configs(mock_product_catalog)

        self.assertEqual(example_configs, [mock_cos_config_data, mock_uan_config_data])
        mock_get_example_data.assert_has_calls([
            call(mock_product_catalog, 'cos-config', mock_cos_layers),
            call(mock_product_catalog, 'uan-config', mock_uan_layers)
        ])


class TestGetProductRecipeNames(unittest.TestCase):
    """Test the get_product_recipe_names function."""

    def test_get_product_recipe_names_success(self):
        """Test get_product_recipe_names when the product exists."""
        mock_product_catalog = Mock()
        expected_recipe_names = ['recipe1', 'recipe2']
        mock_product = mock_product_catalog.get_product.return_value
        mock_product.recipes = [{'name': name} for name in expected_recipe_names]
        actual_recipe_names = get_product_recipe_names(mock_product_catalog, 'sat')
        self.assertEqual(expected_recipe_names, actual_recipe_names)

    def test_get_product_recipes_names_failure(self):
        """Test get_product_recipe_names when the product does not exist."""
        mock_product_catalog = Mock()
        err_msg = 'No installed products with name sat.'
        mock_product_catalog.get_product.side_effect = SoftwareInventoryError(err_msg)
        with self.assertLogs(level=logging.WARNING) as logs_cm:
            actual_recipe_names = get_product_recipe_names(mock_product_catalog, 'sat')

        self.assertEqual([], actual_recipe_names)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Unable to find latest version of product sat to find '
                         f'its image recipes: {err_msg}', logs_cm.records[0].message)


class TestGetExampleImagesAndTemplates(unittest.TestCase):
    """Test the get_example_images_and_templates function."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_product_catalog = Mock()
        self.mock_get_product_recipe_names = mpatch('get_product_recipe_names').start()
        self.mock_get_example_image_data = mpatch('get_example_image_data').start()
        self.mock_get_example_st_data = mpatch('get_example_session_template_data').start()

    def tearDown(self):
        patch.stopall()

    def test_get_example_images_and_templates(self):
        """Test get_example_images_and_templates when recipes are found"""
        recipe_names = image_names = ['cos-compute-2.0.0', 'cos-compute-2.0.1']
        self.mock_get_product_recipe_names.return_value = recipe_names
        self.mock_get_example_image_data.return_value = [{'name': name} for name in image_names]
        product_name = 'cos'
        config_name = 'cos-config'
        config_group = target_role = 'Compute'

        images, session_templates = get_example_images_and_templates(
            self.mock_product_catalog, product_name, config_name, config_group, target_role
        )

        self.mock_get_product_recipe_names.assert_called_once_with(self.mock_product_catalog, product_name)
        self.mock_get_example_image_data.assert_called_once_with(recipe_names, config_name, config_group)
        self.mock_get_example_st_data.assert_called_once_with(image_names, config_name, target_role)
        self.assertEqual(self.mock_get_example_image_data.return_value, images)
        self.assertEqual(self.mock_get_example_st_data.return_value, session_templates)

    def test_get_example_images_and_templates_no_recipes(self):
        """Test get_example_images_and_templates when no recipes are found"""
        self.mock_get_product_recipe_names.return_value = []

        with self.assertLogs(level=logging.WARNING):
            images, session_templates = get_example_images_and_templates(
                self.mock_product_catalog, 'sat', 'sat-config', 'Management', 'Management'
            )

        self.assertEqual([], images)
        self.assertEqual([], session_templates)
        self.mock_get_product_recipe_names.assert_called_once_with(self.mock_product_catalog, 'sat')
        self.mock_get_example_image_data.assert_not_called()
        self.mock_get_example_st_data.assert_not_called()


class TestGetExampleCOSAndUANImagesSessionTemplates(unittest.TestCase):
    """Test get_example_cos_and_uan_images_session_templates"""

    @mpatch('get_example_images_and_templates')
    def test_get_example_cos_and_uan_images_session_templates(self, mock_get_images_and_templates):
        """Test get_example_cos_and_uan_images_session_templates"""
        mock_product_catalog = Mock()
        mock_cos_images = [Mock()]
        mock_cos_templates = [Mock()]
        mock_uan_images = [Mock()]
        mock_uan_templates = [Mock()]
        mock_get_images_and_templates.side_effect = [
            (mock_cos_images, mock_cos_templates),
            (mock_uan_images, mock_uan_templates)
        ]

        images, session_templates = get_example_cos_and_uan_images_session_templates(mock_product_catalog)
        mock_get_images_and_templates.assert_has_calls([
            call(mock_product_catalog, 'cos', EXAMPLE_COS_CONFIG_NAME, 'Compute', 'Compute'),
            call(mock_product_catalog, 'uan', EXAMPLE_UAN_CONFIG_NAME, 'Application', 'Application')
        ])
        self.assertEqual(mock_cos_images + mock_uan_images, images)
        self.assertEqual(mock_cos_templates + mock_uan_templates, session_templates)


class TestGetExampleCOSAndUANData(unittest.TestCase):
    """Test get_example_cos_and_uan_data."""

    @mpatch('ProductCatalog')
    @mpatch('get_example_cos_and_uan_configs')
    @mpatch('get_example_cos_and_uan_images_session_templates')
    def test_get_example_cos_and_uan_data(self, mock_get_images_st,
                                          mock_get_configs, mock_product_catalog_cls):
        """Test get_example_cos_and_uan_data."""
        mock_image_data = Mock()
        mock_template_data = Mock()
        mock_get_images_st.return_value = mock_image_data, mock_template_data
        expected_data = {
            'configurations': mock_get_configs.return_value,
            'images': mock_image_data,
            'session_templates': mock_template_data
        }

        example_data = get_example_cos_and_uan_data()

        self.assertEqual(expected_data, example_data)
        mock_product_catalog = mock_product_catalog_cls.return_value
        mock_get_configs.assert_called_once_with(mock_product_catalog)
        mock_get_images_st.assert_called_once_with(mock_product_catalog)


if __name__ == '__main__':
    unittest.main()
