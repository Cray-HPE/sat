#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
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
from copy import deepcopy
import unittest
from unittest.mock import Mock, patch

from cray_product_catalog.query import InstalledProductVersion, ProductCatalog
from csm_api_client.service.cfs import CFSClientBase
from jinja2 import Environment

from sat.apiclient.ims import IMSClient
from sat.cli.bootprep.errors import ImageCreateError
from sat.cli.bootprep.input.image import IMSInputImageV2, ProductInputImage
from sat.cli.bootprep.input.instance import InputInstance


class TestIMSInputImageV2(unittest.TestCase):
    """Tests for IMSInputImageV2"""
    def setUp(self):
        self.mock_input_instance = Mock(spec=InputInstance)
        self.mock_product_catalog = Mock(spec=ProductCatalog)
        self.mock_cfs_client = Mock(spec=CFSClientBase)
        self.mock_ims_client = Mock(spec=IMSClient)
        self.jinja_env = Environment()

    def test_ims_data(self):
        """Test the ims_data property of IMSInputImageV2"""
        base_type = 'image'
        image_id = 'abcdef12'
        input_data = {
            'name': 'my-image',
            'base': {
                'ims': {
                    'type': base_type,
                    'id': image_id
                }
            }
        }
        ims_input_image = IMSInputImageV2(input_data, 0, self.mock_input_instance, self.jinja_env,
                                          self.mock_product_catalog, self.mock_ims_client,
                                          self.mock_cfs_client)
        self.assertEqual({'type': base_type, 'id': image_id}, ims_input_image.ims_data)

    def test_ims_data_jinja_rendered(self):
        """Test the ims_data property of IMSInputImageV2 when it uses variable substitution"""
        image_id = '1234abcd'
        base_type = 'recipe'
        self.jinja_env.globals['test'] = {
            'id': image_id,
            'type': base_type
        }
        input_data = {
            'name': 'my-image',
            'base': {
                'ims': {
                    'type': '{{test.type}}',
                    'id': '{{test.id}}'
                }
            }
        }
        ims_input_image = IMSInputImageV2(input_data, 0, self.mock_input_instance, self.jinja_env,
                                          self.mock_product_catalog, self.mock_ims_client,
                                          self.mock_cfs_client)
        self.assertEqual({'type': base_type, 'id': image_id}, ims_input_image.ims_data)


class TestProductInputImage(unittest.TestCase):
    """Tests for ProductInputImage"""

    def setUp(self):
        self.mock_input_instance = Mock(spec=InputInstance)

        # Set up a mock product catalog with some mock data for a cos product
        self.product_name = 'cos'
        self.product_version = '2.5.99'
        self.base_type = 'image'
        self.cos_product_catalog_recipes = [
            {'id': 'abcd1234', 'name': 'cos-recipe-x86_64'},
            {'id': '6789dcba', 'name': 'cos-recipe-aarch64'}
        ]
        self.first_image_id = '424242'
        self.second_image_id = 'ababab'
        self.cos_product_catalog_images = [
            {'id': self.first_image_id, 'name': 'cos-image-x86_64'},
            {'id': self.second_image_id, 'name': 'cos-image-aarch64'}
        ]

        self.mock_installed_cos = Mock(spec=InstalledProductVersion)
        self.mock_installed_cos.recipes = self.cos_product_catalog_recipes
        self.mock_installed_cos.images = self.cos_product_catalog_images
        self.mock_product_catalog = Mock(spec=ProductCatalog)
        self.mock_product_catalog.get_product.return_value = self.mock_installed_cos

        self.jinja_env = Environment()
        self.jinja_env.globals = {self.product_name: {'version': self.product_version}}
        self.mock_cfs_client = Mock(spec=CFSClientBase)
        self.mock_ims_client = Mock(spec=IMSClient)

        # The IMS resources should have the same info as in the product catalog entries
        # but with additional IMS resource data
        self.cos_ims_recipes = deepcopy(self.cos_product_catalog_recipes)
        self.cos_ims_images = deepcopy(self.cos_product_catalog_images)
        # Add arch, which is the last dash-separated component of the name in the test data
        for ims_resources in [self.cos_ims_recipes, self.cos_ims_images]:
            for ims_resource in ims_resources:
                ims_resource['arch'] = ims_resource['name'].rsplit('-', 1)[-1]

        def mock_ims_get_matching_resources(resource_type, resource_id):
            if resource_type == 'recipe':
                resource_list = self.cos_ims_recipes
            elif resource_type == 'image':
                resource_list = self.cos_ims_images
            else:
                raise ValueError(f'Unrecognized resource type: {resource_type}')

            return [resource for resource in resource_list
                    if resource['id'] == resource_id]

        self.mock_ims_client.get_matching_resources.side_effect = mock_ims_get_matching_resources

        self.product_input_image = self.get_product_input_image()

    def tearDown(self):
        patch.stopall()

    def get_product_input_image_data(self, base_type=None, filter_prefix=None, filter_wildcard=None, filter_arch=None):
        data = {
            'name': 'configured-{{ base.name }}',
            'base': {
                'product': {
                    'name': self.product_name,
                    'type': base_type or self.base_type
                }
            }
        }
        if self.product_version is not None:
            data['base']['product']['version'] = self.product_version

        # Add filter value if any is specified
        filter_dict = {}
        if filter_prefix is not None:
            filter_dict['prefix'] = filter_prefix
        if filter_wildcard is not None:
            filter_dict['wildcard'] = filter_wildcard
        if filter_arch is not None:
            filter_dict['arch'] = filter_arch

        if filter_dict:
            data['base']['product']['filter'] = filter_dict
        return data

    def get_product_input_image(self, data=None, index=0, base_type=None,
                                filter_prefix=None, filter_wildcard=None, filter_arch=None):
        if not data:
            data = self.get_product_input_image_data(base_type, filter_prefix, filter_wildcard, filter_arch)
        return ProductInputImage(data, index, self.mock_input_instance, self.jinja_env,
                                 self.mock_product_catalog, self.mock_ims_client, self.mock_cfs_client)

    @staticmethod
    def get_ims_resource(name='ims_image', arch=None):
        """Get an example IMS resource for testing the filter function.

        Args:
            name (str): the name of the IMS image or recipe
            arch (str, Optional): the architecture of the image or recipe.
                Omitted if not specified, which is possible per the IMS OpenAPI spec.
        """
        resource = {'name': name}
        if arch:
            resource['arch'] = arch
        return resource

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

    def test_filter_wildcard_not_specified(self):
        """Test filter_wildcard property of ProductInputImage when not specified."""
        self.assertIsNone(self.product_input_image.filter_wildcard)

    def test_filter_wildcard_specified(self):
        """Test filter_wildcard property of ProductInputImage whcn specified"""
        image = self.get_product_input_image(filter_wildcard='other*')
        self.assertEqual('other*', image.filter_wildcard)

    def test_filter_func_not_specified(self):
        """Test filter_func method of ProductInputImage when filter prefix not specified."""
        unfiltered_list = ['list', 'of', 'names']
        for name in unfiltered_list:
            self.assertTrue(self.product_input_image.filter_func(self.get_ims_resource(name)))

    def test_filter_func_specified(self):
        """Test filter_func method of ProductInputImage when filter prefix specified."""
        image = self.get_product_input_image(filter_prefix='other')
        self.assertFalse(image.filter_func(self.get_ims_resource('item')))
        self.assertFalse(image.filter_func(self.get_ims_resource('another_item')))
        self.assertTrue(image.filter_func(self.get_ims_resource('other_item')))

    def test_filter_func_empty_string_prefix(self):
        """Test filter_func method of ProductInputImage when empty string filter prefix specified."""
        image = self.get_product_input_image(filter_prefix='')
        self.assertTrue(image.filter_func(self.get_ims_resource('item')))
        self.assertTrue(image.filter_func(self.get_ims_resource('another_item')))
        self.assertTrue(image.filter_func(self.get_ims_resource('other_item')))

    def test_filter_func_wildcard_specified_matches(self):
        """Test filter_func method of ProductInputImage when a wildcard is specified"""
        patterns_and_matches = {
            'prefix*': ['prefix', 'prefix_matching', 'prefix_with_lots_of_text'],
            '*suffix': ['suffix', 'matching_suffix', 'longer_text_with_suffix'],
            '*infix*': ['infix', 'matching_infix', 'infix_matching', 'foo_infix_foo'],
            'surr*ound': ['surround', 'surrrrrround', 'surr_oun_ound'],
            'single?': ['singled', 'singles'],
        }
        for pattern, matches in patterns_and_matches.items():
            for match in matches:
                image = self.get_product_input_image(filter_wildcard=pattern)
                self.assertTrue(image.filter_func(self.get_ims_resource(match)))

    def test_filter_func_wildcard_not_matching(self):
        """Test filter_func method of ProductInputImage when a specified wildcard does not match."""
        image = self.get_product_input_image(filter_wildcard='*doesnotmatch*')
        self.assertFalse(image.filter_func(self.get_ims_resource('some-image')))

    def test_filter_func_arch_specified_images_without_arch(self):
        """Test filter_func method of ProductInputImage when an arch is specified to filter on but not in image

        IMS treats images and recipes without an arch field as being for the
        x86_64 architecture, so a filter arch of x86_64 should match while a
        filter arch of aarch64 should not.
        """
        input_image_x86_64 = self.get_product_input_image(filter_arch='x86_64')
        # No arch specified in the IMS resource
        ims_image_x86_64 = self.get_ims_resource()
        self.assertTrue(input_image_x86_64.filter_func(ims_image_x86_64))

        input_image_aarch64 = self.get_product_input_image(filter_arch='aarch64')
        ims_image_aarch64 = self.get_ims_resource()
        self.assertFalse(input_image_aarch64.filter_func(ims_image_aarch64))

    def test_filter_func_arch_specified_does_not_match(self):
        """Test filter_func method of ProductInputImage when an arch is specified and it does not match"""
        ims_image = self.get_ims_resource('cos-image', arch='x86_64')
        input_image = self.get_product_input_image(filter_arch='aarch64')
        self.assertFalse(input_image.filter_func(ims_image))

    def test_filter_func_arch_specified_matches(self):
        """Test filter_func method of ProductInputImage when an arch is specified and it matches"""
        ims_image = self.get_ims_resource('cos-image', arch='aarch64')
        input_image = self.get_product_input_image(filter_arch='aarch64')
        self.assertTrue(input_image.filter_func(ims_image))

    def test_filter_func_multiple_filters(self):
        ims_image = self.get_ims_resource('cos-2.5.100', arch='aarch64')
        filters_and_results = [
            ({'filter_prefix': 'cos', 'filter_wildcard': '*2.5*', 'filter_arch': 'aarch64'}, True),
            ({'filter_prefix': 'cos', 'filter_arch': 'aarch64'}, True),
            ({'filter_wildcard': '*2.5*', 'filter_arch': 'aarch64'}, True),
            ({'filter_prefix': 'cos', 'filter_wildcard': '*2.5*'}, True),
            # Arch does not match
            ({'filter_prefix': 'cos', 'filter_wildcard': '*2.5*', 'filter_arch': 'x86_64'}, False),
            # Prefix does not match
            ({'filter_prefix': 'csm', 'filter_wildcard': '*2.5*', 'filter_arch': 'aarch64'}, False),
            # Wildcard does not match
            ({'filter_prefix': 'cos', 'filter_wildcard': '*2.4*', 'filter_arch': 'aarch64'}, False),
        ]

        for filter_params, expected_result in filters_and_results:
            input_image = self.get_product_input_image(**filter_params)
            actual_result = input_image.filter_func(ims_image)
            if expected_result:
                self.assertTrue(actual_result)
            else:
                self.assertFalse(actual_result)

    def test_base_description_no_version(self):
        """Test base_description property of ProductInputImage when no version is specified"""
        self.product_version = None
        image = self.get_product_input_image()
        expected = f'{self.base_type} provided by latest version of product {self.product_name}'
        self.assertEqual(expected, image.base_description)

    def test_base_description_no_filter(self):
        """Test base_description property of ProductInputImage when no filter specified."""
        expected = f'{self.base_type} provided by version {self.product_version} of product {self.product_name}'
        self.assertEqual(expected, self.product_input_image.base_description)

    def test_base_description_with_filter_prefix(self):
        """Test base_description property of ProductInputImage when filter prefix is specified"""
        product_input_image = self.get_product_input_image(filter_prefix='other')
        expected = (f'{self.base_type} provided by version {self.product_version} '
                    f'of product {self.product_name} with name matching prefix "other"')
        self.assertEqual(expected, product_input_image.base_description)

    def test_base_description_with_filter_wildcard(self):
        """Test base_description property of ProductInputImage when filter wildcard is specified"""
        product_input_image = self.get_product_input_image(filter_wildcard='*x86_64*')
        expected = (f'{self.base_type} provided by version {self.product_version} '
                    f'of product {self.product_name} with name matching wildcard "*x86_64*"')
        self.assertEqual(expected, product_input_image.base_description)

    def test_base_description_with_filter_arch(self):
        """Test base_description property of ProductInputImage when filter arch is specified"""
        product_input_image = self.get_product_input_image(filter_arch='aarch64')
        expected = (f'{self.base_type} provided by version {self.product_version} '
                    f'of product {self.product_name} with arch matching "aarch64"')
        self.assertEqual(expected, product_input_image.base_description)

    def test_base_description_with_multiple_filters(self):
        """Test base_description property of ProductInputImage when multiple filters are specified"""
        product_input_image = self.get_product_input_image(filter_prefix='cos',
                                                           filter_wildcard='*image*',
                                                           filter_arch='aarch64')
        expected = (f'{self.base_type} provided by version {self.product_version} '
                    f'of product {self.product_name} with name matching prefix "cos", '
                    f'name matching wildcard "*image*", and arch matching "aarch64"')
        self.assertEqual(expected, product_input_image.base_description)

    def test_installed_product(self):
        """Test installed_product property of ProductInputImage."""
        self.assertEqual(self.mock_installed_cos,
                         self.product_input_image.installed_product)

    def test_product_base_resource_ids_images_present(self):
        """Test product_base_resource_ids property of ProductInputImage with images in product catalog"""
        self.assertEqual([cos_image['id'] for cos_image in self.cos_product_catalog_images],
                         self.product_input_image.product_base_resource_ids)

    def test_product_base_resource_ids_recipes_present(self):
        """Test product_base_resource_ids property of ProductInputImage with recipes in product catalog"""
        product_input_image = self.get_product_input_image(base_type='recipe')
        self.assertEqual([cos_recipe['id'] for cos_recipe in self.cos_product_catalog_recipes],
                         product_input_image.product_base_resource_ids)

    def test_product_base_resource_ids_none_present(self):
        """Test product_base_resource_ids property of ProductInputImage with no images in product catalog"""
        self.mock_installed_cos.images = []
        self.assertEqual([], self.product_input_image.product_base_resource_ids)

    def test_product_base_resource_ids_no_recipes_present(self):
        """Test product_base_resource_ids property of ProductInputImage with no recipes in product catalog"""
        self.mock_installed_cos.recipes = []
        product_input_image = self.get_product_input_image(base_type='recipe')
        self.assertEqual([], product_input_image.product_base_resource_ids)

    def test_ims_base_image_no_match(self):
        """Test ims_base property with no matching images from product"""
        self.mock_installed_cos.images = []
        err_regex = '^There is no image provided by'
        with self.assertRaisesRegex(ImageCreateError, err_regex):
            _ = self.product_input_image.ims_base

    def test_ims_base_recipe_no_match(self):
        """Test ims_base property with no matching recipes from product"""
        self.mock_installed_cos.recipes = []
        product_input_image = self.get_product_input_image(base_type='recipe')
        err_regex = '^There is no recipe provided by'
        with self.assertRaisesRegex(ImageCreateError, err_regex):
            _ = product_input_image.ims_base

    def test_ims_base_image_one_match_no_filter(self):
        """Test ims_base property with one match from the product catalog and no filter"""
        del self.cos_product_catalog_images[1]
        self.assertEqual(self.cos_ims_images[0], self.product_input_image.ims_base)

    def test_ims_base_image_multiple_matches_no_filter(self):
        """Test ims_base property with multiple matches and no filter"""
        err_regex = '^Found 2 matches for '
        with self.assertRaisesRegex(ImageCreateError, err_regex):
            _ = self.product_input_image.ims_base

    def test_ims_base_image_multiple_matches_filter_prefix(self):
        """Test ims_base property with multiple matches for a prefix filter"""
        product_input_image = self.get_product_input_image(filter_prefix='cos')
        err_regex = '^Found 2 matches for '
        with self.assertRaisesRegex(ImageCreateError, err_regex):
            _ = product_input_image.ims_base

    def test_ims_base_image_multiple_matches_empty_filter_prefix(self):
        """Test ims_base property with multiple matches for a prefix filter"""
        product_input_image = self.get_product_input_image(filter_prefix='')
        err_regex = '^Found 2 matches for '
        with self.assertRaisesRegex(ImageCreateError, err_regex):
            _ = product_input_image.ims_base

    def test_ims_base_image_one_match_filter_prefix(self):
        """Test ims_base property with multiple matches for a prefix filter"""
        product_input_image = self.get_product_input_image(filter_prefix='cos-image-x86')
        self.assertEqual(self.cos_ims_images[0], product_input_image.ims_base)

    def test_ims_base_image_one_match_filter_wildcard(self):
        """Test ims_base property with one match for a wildcard filter"""
        product_input_image = self.get_product_input_image(filter_wildcard='*aarch*')
        self.assertEqual(self.cos_ims_images[1], product_input_image.ims_base)

    def test_ims_base_image_one_match_filter_arch(self):
        """Test ims_base property with one match for an arch filter"""
        product_input_image = self.get_product_input_image(filter_arch='aarch64')
        self.assertEqual(self.cos_ims_images[1], product_input_image.ims_base)

    def test_ims_base_image_missing_arch_filter_arch(self):
        """Test ims_base property when IMS record has no arch and filtering on arch"""
        # Remove the arch from the first image's IMS record
        del self.cos_ims_images[0]['arch']
        # Remove the aarch64 image from the product catalog entry
        del self.mock_installed_cos.images[1]

        product_input_image_x86_64 = self.get_product_input_image(filter_arch='x86_64')
        product_input_image_aarch64 = self.get_product_input_image(filter_arch='aarch64')

        # IMS image with no arch defaults to "x86_64" arch, so this should find a match ...
        self.assertEqual(self.cos_ims_images[0], product_input_image_x86_64.ims_base)
        # ... while this should not find a match
        with self.assertRaisesRegex(ImageCreateError, '^Found no matches in IMS '):
            _ = product_input_image_aarch64.ims_base


if __name__ == '__main__':
    unittest.main()
