#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
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

import unittest
from unittest.mock import Mock, patch

from cray_product_catalog.query import InstalledProductVersion, ProductCatalog
from csm_api_client.service.cfs import CFSClient
from jinja2 import Environment

from sat.apiclient.ims import IMSClient
from sat.cli.bootprep.errors import ImageCreateError
from sat.cli.bootprep.input.image import ProductInputImage
from sat.cli.bootprep.input.instance import InputInstance


class TestProductInputImage(unittest.TestCase):
    """Tests for ProductInputImage"""

    def setUp(self):
        self.mock_input_instance = Mock(spec=InputInstance)

        # Set up a mock product catalog with some mock data for a cos product
        self.product_name = 'cos'
        self.product_version = '2.5.99'
        self.base_type = 'image'
        self.cos_recipes = [
            {'id': 'abcd1234', 'name': 'cos-recipe'},
            {'id': '6789dcba', 'name': 'other-cos-recipe'}
        ]
        self.first_image_id = '424242'
        self.second_image_id = 'ababab'
        self.cos_images = [
            {'id': self.first_image_id, 'name': 'cos-image'},
            {'id': self.second_image_id, 'name': 'other-cos-image'}
        ]
        self.mock_installed_cos = Mock(spec=InstalledProductVersion)
        self.mock_installed_cos.recipes = self.cos_recipes
        self.mock_installed_cos.images = self.cos_images
        self.mock_product_catalog = Mock(spec=ProductCatalog)
        self.mock_product_catalog.get_product.return_value = self.mock_installed_cos

        self.jinja_env = Environment()
        self.jinja_env.globals = {self.product_name: {'version': self.product_version}}
        self.mock_cfs_client = Mock(spec=CFSClient)
        self.mock_ims_client = Mock(spec=IMSClient)

        self.product_input_image = self.get_product_input_image()

    def tearDown(self):
        patch.stopall()

    def get_product_input_image_data(self, filter_prefix=None):
        data = {
            'name': 'configured-{{ base.name }}',
            'base': {
                'product': {
                    'name': self.product_name,
                    'type': self.base_type
                }
            }
        }
        if self.product_version is not None:
            data['base']['product']['version'] = self.product_version
        if filter_prefix is not None:
            data['base']['product']['filter'] = {'prefix': filter_prefix}
        return data

    def get_product_input_image(self, data=None, index=0, filter_prefix=None):
        if not data:
            data = self.get_product_input_image_data(filter_prefix)
        return ProductInputImage(data, index, self.mock_input_instance, self.jinja_env,
                                 self.mock_product_catalog, self.mock_ims_client, self.mock_cfs_client)

    def test_base_is_recipe(self):
        """Test base_is_recipe property of ProductInputImage"""
        base_type_tests = [
            ('image', False),
            ('recipe', True)
        ]
        for base_type, expected_value in base_type_tests:
            self.base_type = base_type
            input_image = self.get_product_input_image()
            self.assertEqual(expected_value, input_image.base_is_recipe)

    def test_product_name(self):
        """Test product_name property of ProductInputImage"""
        self.assertEqual(self.product_name, self.product_input_image.product_name)

    def test_product_version(self):
        """Test product_version property of ProductInputImage"""
        self.assertEqual(self.product_version, self.product_input_image.product_version)

    def test_product_version_jinja_rendered(self):
        """Test product_version property of ProductInputImage when it uses variable substitution"""
        product_input_image_data = self.get_product_input_image_data()
        product_input_image_data['base']['product']['version'] = f'{{{{{self.product_name}.version}}}}'
        product_input_image = self.get_product_input_image(product_input_image_data)
        self.assertEqual(self.product_version, product_input_image.product_version)

    def test_filter_prefix_not_specified(self):
        """Test filter_prefix property of ProductInputImage when not specified."""
        self.assertIsNone(self.product_input_image.filter_prefix)

    def test_filter_prefix_specified(self):
        """Test filter_prefix property of ProductInputImage when specified."""
        image = self.get_product_input_image(filter_prefix='other')
        self.assertEqual('other', image.filter_prefix)

    def test_filter_func_not_specified(self):
        """Test filter_func method of ProductInputImage when filter prefix not specified."""
        unfiltered_list = ['list', 'of', 'names']
        for item in unfiltered_list:
            self.assertTrue(self.product_input_image.filter_func(item))

    def test_filter_func_specified(self):
        """Test filter_func method of ProductInputImage when filter prefix specified."""
        image = self.get_product_input_image(filter_prefix='other')
        self.assertFalse(image.filter_func('item'))
        self.assertFalse(image.filter_func('another_item'))
        self.assertTrue(image.filter_func('other_item'))

    def test_filter_func_empty_string_prefix(self):
        """Test filter_func method of ProductInputImage when empty string filter prefix specified."""
        image = self.get_product_input_image(filter_prefix='')
        self.assertTrue(image.filter_func('item'))
        self.assertTrue(image.filter_func('another_item'))
        self.assertTrue(image.filter_func('other_item'))

    def test_base_description_no_version(self):
        """Test base_description property of ProductInputImage when no version specified."""
        self.product_version = None
        image = self.get_product_input_image()
        expected = f'{self.base_type} provided by latest version of product {self.product_name}'
        self.assertEqual(expected, image.base_description)

    def test_base_description_no_filter(self):
        """Test base_description property of ProductInputImage when no filter specified."""
        expected = f'{self.base_type} provided by version {self.product_version} of product {self.product_name}'
        self.assertEqual(expected, self.product_input_image.base_description)

    def test_base_description_with_filter(self):
        """Test base_description property of ProductInputImage when filter specified."""
        image = self.get_product_input_image(filter_prefix='other')
        expected = (f'{self.base_type} provided by version {self.product_version} '
                    f'of product {self.product_name} with name matching prefix "other"')
        self.assertEqual(expected, image.base_description)

    def test_installed_product(self):
        """Test installed_product property of ProductInputImage."""
        self.assertEqual(self.mock_installed_cos,
                         self.product_input_image.installed_product)

    def test_base_resource_id_no_filter_multiple_matches(self):
        """Test base_resource_id property of ProductInputImage with no filter and multiple matches"""
        err_regex = '^There exists more than one '
        with self.assertRaisesRegex(ImageCreateError, err_regex):
            _ = self.product_input_image.base_resource_id

    def test_base_resource_id_no_filter_one_match(self):
        """Test base_resource_id property of ProductInputImage with no filter and one match"""
        del self.cos_images[1]
        self.assertEqual(self.first_image_id, self.product_input_image.base_resource_id)

    def test_base_resource_id_with_filter_one_match(self):
        """Test base_resource_id property of ProductInputImage with filter and one match"""
        image = self.get_product_input_image(filter_prefix='other')
        self.assertEqual(self.second_image_id, image.base_resource_id)

    def test_base_resource_id_with_filter_multiple_matches(self):
        """Test base_resource_id property of ProductInputImage with filter and multiple matches"""
        self.cos_images.append({'id': '123456', 'name': 'other-other-image'})
        image = self.get_product_input_image(filter_prefix='other')
        err_regex = '^There exists more than one '
        with self.assertRaisesRegex(ImageCreateError, err_regex):
            _ = image.base_resource_id

    def test_base_resource_id_with_empty_string_filter_one_match(self):
        """Test base_resource_id property of ProductInputImage with empty string filter prefix and one match."""
        del self.cos_images[1]
        image = self.get_product_input_image(filter_prefix='')
        self.assertEqual(self.first_image_id, image.base_resource_id)


if __name__ == '__main__':
    unittest.main()
