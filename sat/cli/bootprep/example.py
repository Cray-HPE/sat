"""
Generate example input file by gathering info from the product catalog.

(C) Copyright 2022 Hewlett Packard Enterprise Development LP.

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
from collections import namedtuple
import logging

from sat.software_inventory.products import (
    LATEST_VERSION_STRING,
    ProductCatalog,
    SoftwareInventoryError
)

LOGGER = logging.getLogger(__name__)

ExampleConfigLayer = namedtuple('ExampleConfigLayer', ('product_name', 'branch', 'playbook'))

SITE_PLAYBOOK_NAME = 'site.yml'

EXAMPLE_COS_CONFIG_NAME = 'cos-config'
EXAMPLE_COS_CONFIG_LAYERS = [
    ExampleConfigLayer('cos', 'integration', SITE_PLAYBOOK_NAME),
    ExampleConfigLayer('cpe', 'integration', 'pe_deploy.yml'),
    ExampleConfigLayer('slurm', 'master', SITE_PLAYBOOK_NAME),
    ExampleConfigLayer('analytics', 'integration', SITE_PLAYBOOK_NAME)
]

EXAMPLE_UAN_CONFIG_NAME = 'uan-config'
EXAMPLE_UAN_CONFIG_LAYERS = [
    ExampleConfigLayer('uan', 'integration', SITE_PLAYBOOK_NAME),
    ExampleConfigLayer('cpe', 'integration', 'pe_deploy.yml'),
    ExampleConfigLayer('slurm', 'master', SITE_PLAYBOOK_NAME),
    ExampleConfigLayer('analytics', 'integration', SITE_PLAYBOOK_NAME)
]

EXAMPLE_CONFIGS = {
    EXAMPLE_COS_CONFIG_NAME: EXAMPLE_COS_CONFIG_LAYERS,
    EXAMPLE_UAN_CONFIG_NAME: EXAMPLE_UAN_CONFIG_LAYERS
}


class BootprepExampleError(Exception):
    """A fatal error occurred while generating bootprep example data."""
    pass


def get_example_input_config_data(product_catalog, config_name, example_layers):
    """Get the input data for an example CFS configuration.

    For each given example layer, this queries the product catalog to get the
    latest version of the product for that example layer and adds the layer
    data to the returned example input data.

    Args:
        product_catalog (sat.software_inventory.products.ProductCatalog): the
            product catalog used to query for product data
        config_name (str): the name of the configuration to create
        example_layers (list of ExampleConfigLayer): the list of example layers
            that should be added in order
    """
    input_data = {
        'name': config_name,
        'layers': []
    }

    for example_layer in example_layers:
        try:
            product = product_catalog.get_product(example_layer.product_name,
                                                  LATEST_VERSION_STRING)
        except SoftwareInventoryError as err:
            LOGGER.warning(f'Unable to determine latest version of product '
                           f'{example_layer.product_name}: {err}')
            product_version = 'latest'
        else:
            product_version = product.version

        input_data['layers'].append({
            'name': f'{example_layer.product_name}-{example_layer.branch}-{product_version}',
            'playbook': example_layer.playbook,
            'product': {
                'name': example_layer.product_name,
                'version': product_version,
                'branch': example_layer.branch
            }
        })

    return input_data


def get_example_cos_and_uan_configs(product_catalog):
    """Get input data for example COS and UAN CFS configurations.

    Args:
        product_catalog (sat.software_inventory.products.ProductCatalog): the
            product catalog used to query for product data

    Returns:
        list of dict: the list of example input data for a COS CFS configuration
            and a UAN CFS configuration.
    """
    return [get_example_input_config_data(product_catalog, config_name, config_layers)
            for config_name, config_layers in EXAMPLE_CONFIGS.items()]


def get_product_recipe_names(product_catalog, product_name):
    """Get the recipes provided by the given product.

    Args:
        product_catalog (sat.software_inventory.products.ProductCatalog): the
            product catalog used to query for product data
        product_name (str): the name of the product for which to get recipes

    Returns:
        list of str: list of recipe names provided by the given product
    """
    try:
        product = product_catalog.get_product(product_name, LATEST_VERSION_STRING)
    except SoftwareInventoryError as err:
        LOGGER.warning(f'Unable to find latest version of product {product_name} '
                       f'to find its image recipes: {err}')
        return []

    return [recipe['name'] for recipe in product.recipes]


def get_example_image_data(recipe_names, config_name, config_group):
    """Get example image input data from given recipe names.

    Args:
        recipe_names (list of str): the names of the recipes for which to create
            example input image data
        config_name (str): the name of the configuration to apply to the image
        config_group (str): the group name to use when applying the configuration

    Returns:
        list of dict: list of example images
    """
    return [
        {
            'name': recipe_name,
            'ims': {
                'is_recipe': True,
                'name': recipe_name
            },
            'configuration': config_name,
            'configuration_group_names': [config_group]
        }
        for recipe_name in recipe_names
    ]


def get_example_session_template_data(image_names, config_name, target_role):
    """Get example session template input data using the specified images.

    Args:
        image_names (list of str): the names of images for which to create
            example input session template data
        config_name (str): the name of the configuration for the session template
        target_role (str): a targeted node role for the session template

    Returns:
        list of dict: list of example session templates
    """
    return [
        {
            'name': image_name,
            'image': image_name,
            'configuration': config_name,
            'bos_parameters': {
                'boot_sets': {
                    target_role.lower(): {
                        'kernel_parameters': 'ip=dhcp quiet spire_join_token=${SPIRE_JOIN_TOKEN}',
                        'node_roles_groups': [target_role]
                    }
                }
            }
        }
        for image_name in image_names
    ]


def get_example_images_and_templates(product_catalog, product_name, config_name, config_group, target_role):
    """Get example image and session template data for a given product

    Args:
        product_catalog (sat.software_inventory.products.ProductCatalog): the
            product catalog used to query for product data
        product_name (str): the name of the product to query for recipes from
            which to construct example image and session template input data
        config_name (str): the name of the configuration to apply to each image
            and session template
        config_group (str): the group to target during image configuration
        target_role (str): the role to target with the session template

    Returns:
        A tuple of:
            image_data (list of dict): a list of example image input data
            session_template_data (list of dict): a list of example session
                template data
    """
    recipe_names = get_product_recipe_names(product_catalog, product_name)
    if not recipe_names:
        LOGGER.warning(f'Found no recipes from which to create example images '
                       f'and session templates for product {product_name}.')
        return [], []

    example_images = get_example_image_data(recipe_names, config_name, config_group)
    example_image_names = [image['name'] for image in example_images]
    example_session_templates = get_example_session_template_data(example_image_names,
                                                                  config_name, target_role)
    return example_images, example_session_templates


def get_example_cos_and_uan_images_session_templates(product_catalog):
    """Get input data for example COS and UAN images and session templates.

    Args:
        product_catalog (sat.software_inventory.products.ProductCatalog): the
            product catalog used to query for product data

    Returns:
        list of dict: the list of example input data for COS and UAN images
    """
    params_by_product = {
        'cos': (EXAMPLE_COS_CONFIG_NAME, 'Compute', 'Compute'),
        'uan': (EXAMPLE_UAN_CONFIG_NAME, 'Application', 'Application')
    }

    images = []
    session_templates = []

    for product_name, params in params_by_product.items():
        product_images, product_templates = get_example_images_and_templates(product_catalog, product_name, *params)
        images.extend(product_images)
        session_templates.extend(product_templates)

    return images, session_templates


def get_example_cos_and_uan_data():
    """Get example input data for cos and uan images and configs.

    The example input data will contain a configuration, image, and session
    template for both COS and UAN, generated using some hard-coded knowledge
    about which products provide configuration layers and images along with
    data from the product catalog about those images.

    Returns:
        dict: the data for an example InputInstance

    Raises:
        BootprepExampleError: if unable to read product catalog data required to
            generate example input data
    """
    try:
        product_catalog = ProductCatalog()
    except SoftwareInventoryError as err:
        raise BootprepExampleError(f'Failed to query product catalog to generate example data: {err}')

    configurations = get_example_cos_and_uan_configs(product_catalog)
    images, session_templates = get_example_cos_and_uan_images_session_templates(product_catalog)
    return {
        'configurations': configurations,
        'images': images,
        'session_templates': session_templates
    }
