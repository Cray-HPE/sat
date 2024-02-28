#
# MIT License
#
# (C) Copyright 2020-2021,2023,2024 Hewlett Packard Enterprise Development LP
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
Tests for sat.cli.showrev.products module.
"""
import uuid
import logging
import os
import unittest
from unittest.mock import patch, Mock

from cray_product_catalog.query import InstalledProductVersion, ProductCatalogError

from sat.cli.showrev.products import get_product_versions
from tests.test_util import ExtendedTestCase

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'samples')


def get_fake_ims_data(name, ims_id=None):
    """Generate mock value InstalledProductVersion.{images,recipes}."""
    return {'name': name, 'id': ims_id if ims_id else uuid.uuid4()}


def get_mock_installed_product_version(name, version, image_names=None, recipe_names=None,
                                       supports_active=False, active=False):
    """Generate a mock InstalledProductVersion object."""
    mock_ipv = Mock(
        spec=InstalledProductVersion,
        version=version,
        images=[get_fake_ims_data(image_name) for image_name in image_names] if image_names else [],
        recipes=[get_fake_ims_data(recipe_name) for recipe_name in recipe_names] if recipe_names else [],
        supports_active=supports_active,
        active=active
    )
    mock_ipv.name = name
    return mock_ipv


COS_IMAGE_NAME = COS_RECIPE_NAME = 'cray-shasta-compute-sles15sp1.x86_64-1.4.23'
UAN_IMAGE_NAME = UAN_RECIPE_NAME = 'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0'


class TestGetProducts(ExtendedTestCase):
    """Tests for getting product revision information."""

    def setUp(self):
        """Sets up patches."""
        self.mock_product_catalog_cls = patch('sat.cli.showrev.products.ProductCatalog').start()
        self.mock_product_catalog = self.mock_product_catalog_cls.return_value
        self.mock_cos_product = get_mock_installed_product_version(
            'cos', '1.4.0', image_names=[COS_IMAGE_NAME], recipe_names=[COS_RECIPE_NAME]
        )
        self.mock_uan_product = get_mock_installed_product_version(
            'uan', '2.0.0', image_names=[UAN_IMAGE_NAME], recipe_names=[UAN_RECIPE_NAME]
        )
        self.mock_pbs_product = get_mock_installed_product_version('pbs', '0.1.0')

        self.mock_product_catalog.products = [self.mock_cos_product,
                                              self.mock_uan_product,
                                              self.mock_pbs_product]

        self.expected_headers = ['product_name', 'product_version', 'images', 'image_recipes']

    def tearDown(self):
        """Stops all patches"""
        patch.stopall()

    def test_get_product_versions(self):
        """Test a basic invocation of get_product_versions."""
        expected_fields = [
            ['cos', '1.4.0', COS_IMAGE_NAME, COS_RECIPE_NAME],
            ['uan', '2.0.0', UAN_IMAGE_NAME, UAN_RECIPE_NAME],
            ['pbs', '0.1.0', '-', '-']
        ]
        actual_headers, actual_fields = get_product_versions()
        self.mock_product_catalog_cls.assert_called_once_with()
        self.assertEqual(self.expected_headers, actual_headers)
        self.assertEqual(expected_fields, actual_fields)

    def test_get_product_versions_multiple_versions(self):
        """Test an invocation of get_product_versions with multiple of one product."""
        new_uan_image_name = new_uan_recipe_name = 'new-uan-recipe-2.0.1'
        new_uan_product = get_mock_installed_product_version('uan', '2.0.1',
                                                             image_names=[new_uan_image_name],
                                                             recipe_names=[new_uan_recipe_name])
        self.mock_product_catalog.products.insert(2, new_uan_product)

        expected_fields = [
            ['cos', '1.4.0', COS_IMAGE_NAME, COS_RECIPE_NAME],
            ['uan', '2.0.0', UAN_IMAGE_NAME, UAN_RECIPE_NAME],
            ['uan', '2.0.1', new_uan_image_name, new_uan_recipe_name],
            ['pbs', '0.1.0', '-', '-']
        ]
        actual_headers, actual_fields = get_product_versions()
        self.mock_product_catalog_cls.assert_called_once_with()
        self.assertEqual(self.expected_headers, actual_headers)
        self.assertEqual(expected_fields, actual_fields)

    def test_get_product_versions_multiple_images_recipes(self):
        """Test an invocation of get_product_versions where products have multiple images and recipes."""
        other_uan_image = other_uan_recipe = 'cray-shasta-uan-cos-sles15sp1.aarch64-2.0.0'
        self.mock_uan_product.images.append(get_fake_ims_data(other_uan_image))
        self.mock_uan_product.recipes.append(get_fake_ims_data(other_uan_recipe))

        expected_fields = [
            ['cos', '1.4.0', COS_IMAGE_NAME, COS_RECIPE_NAME],
            ['uan', '2.0.0', f'{other_uan_image}\n{UAN_IMAGE_NAME}', f'{other_uan_recipe}\n{UAN_RECIPE_NAME}'],
            ['pbs', '0.1.0', '-', '-']
        ]
        actual_headers, actual_fields = get_product_versions()
        self.mock_product_catalog_cls.assert_called_once_with()
        self.assertEqual(self.expected_headers, actual_headers)
        self.assertEqual(expected_fields, actual_fields)

    def test_get_product_versions_product_catalog_error(self):
        """Test when a ProductCatalogError occurs when loading the product catalog data"""
        pc_err_msg = 'failed to load K8s config'
        self.mock_product_catalog_cls.side_effect = ProductCatalogError(pc_err_msg)

        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertEqual(get_product_versions(), ([], []))

        self.assert_in_element(f'Unable to obtain product version information from '
                               f'product catalog: {pc_err_msg}', logs.output)

    def test_get_product_versions_active_version(self):
        """Test that a product that appears "active" in the catalog does not generate a report with the active field."""
        self.mock_uan_product.supports_active = True
        self.mock_uan_product.active = False
        expected_fields = [
            ['cos', '1.4.0', COS_IMAGE_NAME, COS_RECIPE_NAME],
            ['uan', '2.0.0', UAN_IMAGE_NAME, UAN_RECIPE_NAME],
            ['pbs', '0.1.0', '-', '-']
        ]
        actual_headers, actual_fields = get_product_versions()
        self.mock_product_catalog_cls.assert_called_once_with()
        self.assertEqual(self.expected_headers, actual_headers)
        self.assertEqual(expected_fields, actual_fields)


if __name__ == '__main__':
    unittest.main()
