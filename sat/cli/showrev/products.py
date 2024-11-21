#
# MIT License
#
# (C) Copyright 2020-2023, 2024 Hewlett Packard Enterprise Development LP
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
Module for obtaining product version information.
"""
import logging

from cray_product_catalog.query import ProductCatalog, ProductCatalogError
from sat.loose_version import LooseVersion


LOGGER = logging.getLogger(__name__)


def get_product_versions():
    """Gets the product versions from the 'cray-product-catalog' config map.

    Returns:
        A tuple of (headings, data_rows) where headings is a list of strings
        representing the headings for the data, and data_rows is a list of
        lists where each element is a list representing one row of data.

        The headings will be the product name, version, image name, and image
        recipe name. The rows will be the values of each of these fields for
        each product.

        If multiple versions of one product exist, then there will be one row
        for each product-version. If multiple images and/or recipes exist for
        one product-version, then each image or recipe will be printed as a
        newline-separated list within the same row. If no images and/or recipes
        exist for a product-version, then their values will be '-'.
    """
    product_key = 'product_name'
    version_key = 'product_version'
    image_key = 'images'
    recipe_key = 'image_recipes'
    headers = [product_key, version_key, image_key, recipe_key]

    try:
        product_catalog = ProductCatalog()
    except ProductCatalogError as err:
        LOGGER.error(f'Unable to obtain product version information from product catalog: {err}')
        return [], []

    products = []
    for product in product_catalog.products:
        images = '\n'.join(sorted(image['name'] for image in product.images)) or '-'
        recipes = '\n'.join(sorted(recipe['name'] for recipe in product.recipes)) or '-'
        products.append([product.name, LooseVersion(product.version), images, recipes])

    return headers, products
