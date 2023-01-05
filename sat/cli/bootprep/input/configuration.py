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
Defines classes for configurations defined in the input file.
"""
from abc import ABC, abstractmethod
import logging
from urllib.parse import urlparse, urlunparse

from cray_product_catalog.query import ProductCatalogError
from csm_api_client.service.gateway import APIError
from csm_api_client.service.vcs import VCSError, VCSRepo

from sat.cached_property import cached_property
from sat.cli.bootprep.constants import LATEST_VERSION_VALUE
from sat.cli.bootprep.errors import InputItemCreateError
from sat.cli.bootprep.input.base import (
    BaseInputItem,
    BaseInputItemCollection,
    jinja_rendered,
)
from sat.config import get_config_value

LOGGER = logging.getLogger(__name__)


class InputConfigurationLayer(ABC):
    """A CFS configuration layer as defined in the bootprep input file"""

    # Mapping from CFS property name to class property name for required property
    REQUIRED_CFS_PROPERTIES = {
        'cloneUrl': 'clone_url'
    }
    # Mapping from CFS property name to class property name for optional properties
    # If the property value is None, the property will be omitted from the CFS layer
    OPTIONAL_CFS_PROPERTIES = {
        'branch': 'branch',
        'commit': 'commit',
        'name': 'name',
        'playbook': 'playbook'
    }

    # CRAYSAT-1174: Specifying a 'branch' in a CFS configuration layer is not
    # supported until CSM 1.2. Toggling this variable will change the behavior
    # for both GitCFSConfigurationLayers and ProductCFSConfigurationLayers.
    resolve_branches = True

    # The jinja_rendered properties here are only rendered at item creation time
    template_render_err = InputItemCreateError

    def __init__(self, layer_data, jinja_env):
        """Create a new configuration layer.

        Args:
            layer_data (dict): the layer data from the input instance
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
        """
        self.layer_data = layer_data
        self.jinja_env = jinja_env

    @property
    def playbook(self):
        """str or None: the playbook specified in the layer"""
        return self.layer_data.get('playbook')

    @property
    @jinja_rendered
    def name(self):
        """str or None: the name specified for the layer"""
        return self.layer_data.get('name')

    @property
    @abstractmethod
    def clone_url(self):
        """str: the git clone URL for this layer"""
        pass

    @property
    @abstractmethod
    def branch(self):
        """str or None: the branch for this layer"""
        pass

    @property
    @abstractmethod
    def commit(self):
        """str or None: the commit for this layer"""
        pass

    def get_cfs_api_data(self):
        """Get the data to pass to the CFS API to create this layer.

        Returns:
            dict: The dictionary of data to pass to the CFS API to create the
                layer.

        Raises:
            InputItemCreateError: if there was a failure to obtain the data
                needed to create the layer in CFS.
        """
        cfs_layer_data = {cfs_property: getattr(self, self_property)
                          for cfs_property, self_property in self.REQUIRED_CFS_PROPERTIES.items()}
        for cfs_property, self_property in self.OPTIONAL_CFS_PROPERTIES.items():
            # CRAYSAT-1174: Ignore branch property if not supported by CFS
            if self.resolve_branches and cfs_property == 'branch':
                continue

            property_value = getattr(self, self_property)
            if property_value is not None:
                cfs_layer_data[cfs_property] = property_value

        return cfs_layer_data

    @staticmethod
    def get_configuration_layer(layer_data, jinja_env, product_catalog):
        """Get and return a new InputConfigurationLayer for the given layer data.

        Args:
            layer_data (dict): The data for a layer, already validated against
                the bootprep input file schema.
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            product_catalog (cray_product_catalog.query.ProductCatalog):
                the product catalog object

        Raises:
            ValueError: if neither 'git' nor 'product' keys are present in the
                input `layer_data`. This will not happen if the input is
                properly validated against the schema.
        """
        if 'git' in layer_data:
            return GitInputConfigurationLayer(layer_data, jinja_env)
        elif 'product' in layer_data:
            return ProductInputConfigurationLayer(layer_data, jinja_env, product_catalog)
        else:
            raise ValueError('Unrecognized type of configuration layer')

    def resolve_commit_hash(self, branch):
        """Query VCS to determine the commit hash at the head of the branch.

        Args:
            branch (str): the name of the branch to look up

        Returns:
            str: the commit hash corresponding to the HEAD commit of the branch.

        Raises:
            InputItemCreateError: if there is no such branch on the remote
                repository.
        """
        try:
            commit_hash = VCSRepo(self.clone_url).get_commit_hash_for_branch(branch)
        except VCSError as err:
            raise InputItemCreateError(f'Could not query VCS to resolve branch name "{branch}": '
                                       f'{err}')

        if commit_hash is None:
            raise InputItemCreateError(f'Could not retrieve HEAD commit for branch "{branch}"; '
                                       'no matching branch was found on remote VCS repo.')
        return commit_hash


class GitInputConfigurationLayer(InputConfigurationLayer):
    """
    A configuration layer that is defined with an explicit Git URL
    and a branch or a commit hash.
    """
    @property
    def clone_url(self):
        # The 'url' property is required by the schema
        return self.layer_data['git']['url']

    @property
    @jinja_rendered
    def branch(self):
        # The 'branch' property is optional
        return self.layer_data['git'].get('branch')

    @property
    def commit(self):
        # The 'commit' property is optional
        if self.resolve_branches and self.branch is not None:
            # If given a branch, we can look up the commit dynamically.
            return self.resolve_commit_hash(self.branch)
        return self.layer_data['git'].get('commit')


class ProductInputConfigurationLayer(InputConfigurationLayer):
    """
    A configuration layer that is defined with the name of a product
    and the version or branch.
    """
    def __init__(self, layer_data, jinja_env, product_catalog):
        """Create a new ProductInputConfigurationLayer.

        Args:
            layer_data (dict): the layer data from the input instance
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            product_catalog (cray_product_catalog.query.ProductCatalog or None):
                the product catalog object
        """
        super().__init__(layer_data, jinja_env)
        self.product_catalog = product_catalog

    @property
    def product_name(self):
        """str: the name of the product"""
        # The 'name' property is required
        return self.layer_data['product']['name']

    @property
    @jinja_rendered
    def product_version(self):
        """str: the version specified for the product"""
        # The 'version' property is optional. If not specified, assume latest
        return self.layer_data['product'].get('version', LATEST_VERSION_VALUE)

    @cached_property
    def matching_product(self):
        """sat.software_inventory.products.InstalledProductVersion: the matching installed product"""
        if self.product_catalog is None:
            raise InputItemCreateError(f'Product catalog data is not available.')

        try:
            if self.product_version == LATEST_VERSION_VALUE:
                return self.product_catalog.get_product(self.product_name)
            return self.product_catalog.get_product(self.product_name, self.product_version)
        except ProductCatalogError as err:
            raise InputItemCreateError(f'Unable to get product data from product catalog: {err}')

    @staticmethod
    def substitute_url_hostname(url):
        """Substitute the hostname in a URL with the configured API gateway hostname.

        Args:
            url (str): The URL to substitute.

        Returns:
            str: The URL with the hostname portion replaced.
        """
        return urlunparse(urlparse(url)._replace(
            netloc=get_config_value('api_gateway.host')
        ))

    @cached_property
    def clone_url(self):
        if self.matching_product.clone_url is None:
            raise InputItemCreateError(f'No clone URL present for version {self.product_version} '
                                       f'of product {self.product_name}')
        return self.substitute_url_hostname(self.matching_product.clone_url)

    @cached_property
    @jinja_rendered
    def branch(self):
        # The 'branch' property is optional
        return self.layer_data['product'].get('branch')

    @cached_property
    def commit(self):
        # There are a few ways to determine the proper commit hash for a
        # layer, if necessary. Their precedence is as follows.
        #   1. If the commit for the product was specified explicitly in the
        #      input file, that should be returned.
        #   2. If a branch for the product was specified in the input file, the
        #      branch needs to be resolved to a commit hash, and that commit hash
        #      should be returned. If branch resolving is disabled (i.e. with
        #      --no-resolve-branches), then presumably CFS supports branch names,
        #      and so this property should be None in order for a branch name to
        #      be passed to CFS.
        #   3. If neither a commit nor a branch was specified, then consult the
        #      product catalog for the an associated commit hash and return
        #      that.

        input_commit = self.layer_data['product'].get('commit')
        if input_commit:
            return input_commit

        if self.branch is not None:
            if self.resolve_branches:
                return self.resolve_commit_hash(self.branch)
            return None

        if self.matching_product.commit is None:
            raise InputItemCreateError(f'No commit present for version {self.product_version} '
                                       f'of product {self.product_name}')
        return self.matching_product.commit


class InputConfiguration(BaseInputItem):
    """A CFS Configuration from a bootprep input file."""
    description = 'CFS configuration'

    def __init__(self, data, instance, index, jinja_env, cfs_client,
                 product_catalog, **kwargs):
        """Create a new InputConfiguration.

        Args:
            data (dict): the data defining the item from the input file, already
                validated by the bootprep schema.
            instance (sat.cli.bootprep.input.instance.InputInstance): a reference
                to the full instance loaded from the input file
            index (int): the index of the item in the collection in the instance
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            cfs_client (csm_api_client.service.cfs.CFSClient): the CFS API client
            product_catalog (cray_product_catalog.query.ProductCatalog):
                the product catalog object
            **kwargs: additional keyword arguments
        """
        super().__init__(data, instance, index, jinja_env, **kwargs)
        self.cfs_client = cfs_client
        self.product_catalog = product_catalog

        # Additional context to be used when rendering Jinja2 templated properties
        self.jinja_context = {}

        # The 'layers' property is required and must be a list, but it can be empty
        self.layers = [InputConfigurationLayer.get_configuration_layer(layer_data, jinja_env, product_catalog)
                       for layer_data in self.data['layers']]

    def get_create_item_data(self):
        """Get the data to pass to the CFS API to create this configuration.

        Returns:
            dict: The dictionary of data to pass to the CFS API to create the
                configuration.

        Raises:
            InputItemCreateError: if there was a failure to obtain the data
                needed to create the configuration in CFS.
        """
        cfs_api_data = {
            'layers': []
        }
        failed_layers = []
        for idx, layer in enumerate(self.layers):
            try:
                cfs_api_data['layers'].append(layer.get_cfs_api_data())
            except InputItemCreateError as err:
                LOGGER.error(f'Failed to create layers[{idx}] of configuration '
                             f'{self.name}: {err}')
                failed_layers.append(layer)

        if failed_layers:
            raise InputItemCreateError(f'Failed to create {len(failed_layers)} layer(s) '
                                       f'of configuration {self.name}')

        return cfs_api_data

    def create(self, payload):
        """Create the CFS configuration with a request to the CFS API.

        Args:
            payload (dict): the payload to pass to the CFS API to create the
                CFS configuration
        """
        try:
            # request_body guaranteed to have 'name' key, so no need to catch ValueError
            self.cfs_client.put_configuration(self.name, payload)
        except APIError as err:
            raise InputItemCreateError(f'Failed to create configuration: {err}')


class InputConfigurationCollection(BaseInputItemCollection):
    """The collection of CFS configurations defined in the input file."""

    item_class = InputConfiguration

    def __init__(self, items_data, instance, jinja_env, request_dumper, cfs_client, **kwargs):
        """Create a new InputConfigurationCollection.

        Args:
            items_data (list of dict): CFS configuration data from input file,
                already validated by schema
            instance (sat.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            request_dumper (sat.cli.bootprep.output.RequestDumper): the dumper
                for dumping request data to files.
            cfs_client (csm_api_client.service.cfs.CFSClient): the CFS API client
            **kwargs: additional keyword arguments
        """
        super().__init__(items_data, instance, jinja_env, request_dumper,
                         cfs_client=cfs_client, **kwargs)
        self.cfs_client = cfs_client

    def get_existing_items_by_name(self):
        """Get existing CFS configurations by name.

        See parent class for full docstring.
        """
        try:
            # TODO: Add a get_configurations method to cfs_client?
            configurations = self.cfs_client.get('configurations').json()
        except APIError as err:
            # TODO: Consider whether we need subclasses of InputItemCreateError
            raise InputItemCreateError(f'Unable to get existing CFS configurations: {err}')
        except ValueError as err:
            raise InputItemCreateError(f'Unable to parse response when getting existing CFS '
                                       f'configurations: {err}')

        # CFS configurations have unique names, so this is safe
        return {
            configuration.get('name'): [configuration]
            for configuration in configurations
        }
