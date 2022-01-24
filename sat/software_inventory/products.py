"""
Defines classes for querying for information about the installed products.

(C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP.

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
import logging
from pkg_resources import parse_version
import warnings

from cray_product_catalog.schema.validate import validate
from jsonschema.exceptions import ValidationError
from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException
from kubernetes.config import load_kube_config, ConfigException
from urllib3.exceptions import MaxRetryError
from yaml import safe_load, YAMLError, YAMLLoadWarning

from sat.software_inventory.constants import (
    COMPONENT_DOCKER_KEY,
    COMPONENT_REPOS_KEY,
    COMPONENT_VERSIONS_PRODUCT_MAP_KEY,
    PRODUCT_CATALOG_CONFIG_MAP_NAME,
    PRODUCT_CATALOG_CONFIG_MAP_NAMESPACE,
    LATEST_VERSION_STRING
)

LOGGER = logging.getLogger(__name__)


class SoftwareInventoryError(Exception):
    """An error occurred reading or manipulating product installs."""
    pass


class ProductCatalog:
    """A collection of installed product versions.

    Attributes:
        name: The product catalog Kubernetes config map name.
        namespace: The product catalog Kubernetes config map namespace.
        products ([InstalledProductVersion]): A list of installed product
            versions.
    """
    @staticmethod
    def _get_k8s_api():
        """Load a Kubernetes CoreV1Api and return it.

        Returns:
            CoreV1Api: The Kubernetes API.

        Raises:
            SoftwareInventoryError: if there was an error loading the
                Kubernetes configuration.
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
            return CoreV1Api()
        except ConfigException as err:
            raise SoftwareInventoryError(f'Unable to load kubernetes configuration: {err}.')

    def __init__(self, name=PRODUCT_CATALOG_CONFIG_MAP_NAME, namespace=PRODUCT_CATALOG_CONFIG_MAP_NAMESPACE):
        """Create the ProductCatalog object.

        Args:
            name (str): The name of the product catalog Kubernetes config map.
            namespace (str): The namespace of the product catalog Kubernetes
                config map.

        Raises:
            SoftwareInventoryError: if reading the config map failed.
        """
        self.name = name
        self.namespace = namespace
        self.k8s_client = self._get_k8s_api()
        try:
            config_map = self.k8s_client.read_namespaced_config_map(name, namespace)
        except MaxRetryError as err:
            raise SoftwareInventoryError(
                f'Unable to connect to Kubernetes to read {namespace}/{name} ConfigMap: {err}'
            )
        except ApiException as err:
            # The full string representation of ApiException is very long, so just log err.reason.
            raise SoftwareInventoryError(
                f'Error reading {namespace}/{name} ConfigMap: {err.reason}'
            )

        if config_map.data is None:
            raise SoftwareInventoryError(
                f'No data found in {namespace}/{name} ConfigMap.'
            )

        try:
            self.products = [
                InstalledProductVersion(product_name, product_version, product_version_data)
                for product_name, product_versions in config_map.data.items()
                for product_version, product_version_data in safe_load(product_versions).items()
            ]
        except YAMLError as err:
            raise SoftwareInventoryError(
                f'Failed to load ConfigMap data: {err}'
            )

        invalid_products = [
            str(p) for p in self.products if not p.is_valid
        ]
        if invalid_products:
            LOGGER.debug(
                f'The following products have product catalog data that '
                f'is not valid against the expected schema: {", ".join(invalid_products)}'
            )

        self.products = [
            p for p in self.products if p.is_valid
        ]

    def get_product(self, name, version):
        """Get the InstalledProductVersion matching the given name/version.

        Args:
            name (str): The product name.
            version (str): The product version. If this is the special value
                `LATEST_VERSION_STRING`, then get the latest installed version.

        Returns:
            An InstalledProductVersion with the given name and version.

        Raises:
            SoftwareInventoryError: If there is more than one matching
                InstalledProductVersion, or if there are none.
        """
        if version == LATEST_VERSION_STRING:
            matching_name_products = [product for product in self.products if product.name == name]
            if not matching_name_products:
                raise SoftwareInventoryError(f'No installed products with name {name}.')
            latest = sorted(matching_name_products,
                            key=lambda p: parse_version(p.version))[-1]
            LOGGER.info(f'Using latest version ({latest.version}) of product {name}')
            return latest

        matching_products = [
            product for product in self.products
            if product.name == name and product.version == version
        ]
        if not matching_products:
            raise SoftwareInventoryError(
                f'No installed products with name {name} and version {version}.'
            )
        elif len(matching_products) > 1:
            raise SoftwareInventoryError(
                f'Multiple installed products with name {name} and version {version}.'
            )

        return matching_products[0]


class InstalledProductVersion:
    """A representation of a version of a product that is currently installed.

    Attributes:
        name: The product name.
        version: The product version.
        data: A dictionary representing the data within a given product and
              version in the product catalog, which is expected to contain a
              'component_versions' key that will point to the respective
              versions of product components, e.g. Docker images.
    """
    def __init__(self, name, version, data):
        self.name = name
        self.version = version
        self.data = data

    def __str__(self):
        return f'{self.name}-{self.version}'

    @property
    def is_valid(self):
        """bool: True if this product's version data fits the schema."""
        try:
            validate(self.data)
            return True
        except ValidationError:
            return False

    @property
    def component_data(self):
        """dict: a mapping from types of components to lists of components"""
        return self.data.get(COMPONENT_VERSIONS_PRODUCT_MAP_KEY, {})

    @property
    def docker_images(self):
        """Get Docker images associated with this InstalledProductVersion.

        Returns:
            A list of tuples of (image_name, image_version)
        """
        # If there is no 'docker' key under the component data, assume that there
        # is a single docker image named cray/cray-PRODUCT whose version is the
        # value of the PRODUCT key under component_versions.
        if COMPONENT_DOCKER_KEY not in self.component_data:
            return [(self._deprecated_docker_image_name, self._deprecated_docker_image_version)]

        return [(component['name'], component['version'])
                for component in self.component_data.get(COMPONENT_DOCKER_KEY) or []]

    @property
    def _deprecated_docker_image_version(self):
        """str: The Docker image version associated with this product version, or None.

        Note: this assumes that the 'component_versions' data is structured as follows:
        component_versions:
            product_name: docker_image_version

        Newer versions will structure the 'component_versions' data as follows:
        component_versions:
            product_name:
                docker:
                    docker_image_name_1: docker_image_version
                    docker_image_name_2: docker_image_version

        This method should only be used if the installed version does not have a
        component_versions->product_name->docker key.
        """
        return self.component_data.get(self.name)

    @property
    def _deprecated_docker_image_name(self):
        """str: The Docker image name associated with this product version.

        Note: this assumes that the 'component_versions' data is structured as follows:
        component_versions:
            product_name: docker_image_version

        It also assumes that the name of the singular docker image is
        'cray/cray-<product_name'.

        Newer versions will structure the 'component_versions' data as follows:
        component_versions:
            product_name:
                docker:
                    docker_image_name_1: docker_image_version
                    docker_image_name_2: docker_image_version

        This method should only be used if the installed version does not have a
        component_versions->product_name->docker key.
        """
        return f'cray/cray-{self.name}'

    @property
    def repositories(self):
        """list of dict: the repositories for this product version."""
        return self.component_data.get(COMPONENT_REPOS_KEY, [])

    @property
    def group_repositories(self):
        """list of dict: the group-type repositories for this product version."""
        return [repo for repo in self.repositories if repo.get('type') == 'group']

    @property
    def hosted_repositories(self):
        """list of dict: the hosted-type repositories for this product version."""
        return [repo for repo in self.repositories if repo.get('type') == 'hosted']

    @property
    def hosted_and_member_repo_names(self):
        """set of str: all hosted repository names for this product version

        This includes all explicitly listed hosted repos plus any hosted repos
        which are listed only as members of any of the group repos
        """
        # Get all hosted repositories, plus any repos that might be under a group repo's "members" list.
        repository_names = set(repo.get('name') for repo in self.hosted_repositories)
        for group_repo in self.group_repositories:
            repository_names |= set(group_repo.get('members'))

        return repository_names

    @property
    def configuration(self):
        """dict: information about the config management repo for the product"""
        return self.data.get('configuration', {})

    @property
    def clone_url(self):
        """str or None: the clone url of the config repo for the product, if available."""
        return self.configuration.get('clone_url')

    @property
    def commit(self):
        """str or None: the commit hash of the config repo for the product, if available."""
        return self.configuration.get('commit')

    @property
    def import_branch(self):
        """str or None: the branch name of the config repo for the product, if available."""
        return self.configuration.get('import_branch')

    def _get_ims_resources(self, ims_resource_type):
        """Get IMS resources (images or recipes) provided by the product

        Args:
            ims_resource_type (str): Either 'images' or 'recipes'

        Returns:
            list of dict: the IMS resources of the given type provided by the
                product. Each has a 'name' and 'id' key.

        Raises:
            ValueError: if given an unrecognized `ims_resource_type`
        """
        if ims_resource_type not in ('recipes', 'images'):
            raise ValueError(f'Unrecognized IMS resource type "{ims_resource_type}"')

        ims_resource_data = self.data.get(ims_resource_type) or {}

        return [
            {'name': resource_name, 'id': resource_data.get('id')}
            for resource_name, resource_data in ims_resource_data.items()
        ]

    @property
    def images(self):
        """list of dict: the list of images provided by this product"""
        return self._get_ims_resources('images')

    @property
    def recipes(self):
        return self._get_ims_resources('recipes')
