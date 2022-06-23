#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
import functools
import logging
from urllib.parse import urlparse, urlunparse

from cray_product_catalog.query import ProductCatalogError
from jinja2 import Template, TemplateError

from sat.apiclient.vcs import VCSError, VCSRepo
from sat.cached_property import cached_property
from sat.cli.bootprep.constants import LATEST_VERSION_VALUE
from sat.cli.bootprep.errors import ConfigurationCreateError
from sat.config import get_config_value

LOGGER = logging.getLogger(__name__)


def render_template(func):
    """Wrapper function to handle Jinja templates with variables stored in object.

    This should be used to wrap instance methods which return content from the
    InputInstance that may contain Jinja2 template content to be rendered.

    This wrapper assumes the instance has a `var_context` attribute of type
    `VariableContext` that should be used for rendering templates.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        unrendered_result = func(self, *args, **kwargs)

        # If the value is `None`, it was not specified by the user.
        if unrendered_result is None:
            return unrendered_result

        try:
            return Template(unrendered_result).render(self.var_context.vars)
        except TemplateError as err:
            raise ConfigurationCreateError(f'Failed to render Jinja2 template {unrendered_result} '
                                           f'for value {func.__name__}: {err}')

    return wrapper


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

    def __init__(self, layer_data, var_context):
        """Create a new configuration layer.

        Args:
            layer_data (dict): the layer data from the input instance
            var_context (sat.cli.bootprep.vars.VariableContext): the variables
                to use for variable substitution in input instance.
        """
        self.layer_data = layer_data
        self.var_context = var_context

    @property
    def playbook(self):
        """str or None: the playbook specified in the layer"""
        return self.layer_data.get('playbook')

    @property
    @render_template
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
            ConfigurationCreateError: if there was a failure to obtain the data
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
    def get_configuration_layer(layer_data, var_context, product_catalog):
        """Get and return a new InputConfigurationLayer for the given layer data.

        Args:
            layer_data (dict): The data for a layer, already validated against
                the bootprep input file schema.
            var_context (sat.cli.bootprep.vars.VariableContext): the variables
                to use for variable substitution in input instance.
            product_catalog (cray_product_catalog.query.ProductCatalog):
                the product catalog object

        Raises:
            ValueError: if neither 'git' nor 'product' keys are present in the
                input `layer_data`. This will not happen if the input is
                properly validated against the schema.
        """
        if 'git' in layer_data:
            return GitInputConfigurationLayer(layer_data, var_context)
        elif 'product' in layer_data:
            return ProductInputConfigurationLayer(layer_data, var_context, product_catalog)
        else:
            raise ValueError('Unrecognized type of configuration layer')

    def resolve_commit_hash(self, branch):
        """Query VCS to determine the commit hash at the head of the branch.

        Args:
            branch (str): the name of the branch to look up

        Returns:
            str: the commit hash corresponding to the HEAD commit of the branch.

        Raises:
            ConfigurationCreateError: if there is no such branch on the remote
                repository.
        """
        try:
            commit_hash = VCSRepo(self.clone_url).get_commit_hash_for_branch(branch)
        except VCSError as err:
            raise ConfigurationCreateError(f'Could not query VCS to resolve branch name "{branch}": '
                                           f'{err}')

        if commit_hash is None:
            raise ConfigurationCreateError(f'Could not retrieve HEAD commit for branch "{branch}"; '
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
    @render_template
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
    def __init__(self, layer_data, var_context, product_catalog):
        """Create a new ProductInputConfigurationLayer.

        Args:
            layer_data (dict): the layer data from the input instance
            var_context (sat.cli.bootprep.vars.VariableContext): the variables
                to use for variable substitution in input instance.
            product_catalog (cray_product_catalog.query.ProductCatalog or None):
                the product catalog object
        """
        super().__init__(layer_data, var_context)
        self.product_catalog = product_catalog

    @property
    def product_name(self):
        """str: the name of the product"""
        # The 'name' property is required
        return self.layer_data['product']['name']

    @property
    @render_template
    def product_version(self):
        """str: the version specified for the product"""
        # The 'version' property is optional. If not specified, assume latest
        return self.layer_data['product'].get('version', LATEST_VERSION_VALUE)

    @cached_property
    def matching_product(self):
        """sat.software_inventory.products.InstalledProductVersion: the matching installed product"""
        if self.product_catalog is None:
            raise ConfigurationCreateError(f'Product catalog data is not available.')

        try:
            if self.product_version == LATEST_VERSION_VALUE:
                return self.product_catalog.get_product(self.product_name)
            return self.product_catalog.get_product(self.product_name, self.product_version)
        except ProductCatalogError as err:
            raise ConfigurationCreateError(f'Unable to get product data from product catalog: {err}')

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
            raise ConfigurationCreateError(f'No clone URL present for version {self.product_version} '
                                           f'of product {self.product_name}')
        return self.substitute_url_hostname(self.matching_product.clone_url)

    @cached_property
    @render_template
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
            raise ConfigurationCreateError(f'No commit present for version {self.product_version} '
                                           f'of product {self.product_name}')
        return self.matching_product.commit


class InputConfiguration:
    """A CFS Configuration from a bootprep input file."""

    def __init__(self, configuration_data, var_context, product_catalog):
        """Create a new InputConfiguration.

        Args:
            configuration_data (dict): The data for a configuration, already
                validated against the bootprep input file schema.
            var_context (sat.cli.bootprep.vars.VariableContext): the variables
                to use for variable substitution in input instance.
            product_catalog (cray_product_catalog.query.ProductCatalog):
                the product catalog object

        Raises:
            ValueError: if any of the layers in the given `configuration_data`
                have neither 'git' nor 'product' keys in their data. This won't
                happen if the input is properly validated against the schema.
        """
        self.configuration_data = configuration_data
        self.var_context = var_context
        # The 'layers' property is required and must be a list, but it can be empty
        self.layers = [InputConfigurationLayer.get_configuration_layer(layer_data, var_context, product_catalog)
                       for layer_data in self.configuration_data['layers']]

    @property
    @render_template
    def name(self):
        """The name of the CFS configuration."""
        # The 'name' property is required
        return self.configuration_data['name']

    def get_cfs_api_data(self):
        """Get the data to pass to the CFS API to create this configuration.

        Returns:
            dict: The dictionary of data to pass to the CFS API to create the
                configuration.

        Raises:
            ConfigurationCreateError: if there was a failure to obtain the data
                needed to create the configuration in CFS.
        """
        cfs_api_data = {
            'layers': []
        }
        failed_layers = []
        for idx, layer in enumerate(self.layers):
            try:
                cfs_api_data['layers'].append(layer.get_cfs_api_data())
            except ConfigurationCreateError as err:
                LOGGER.error(f'Failed to create layers[{idx}] of configuration '
                             f'{self.name}: {err}')
                failed_layers.append(layer)

        if failed_layers:
            raise ConfigurationCreateError(f'Failed to create {len(failed_layers)} layer(s) '
                                           f'of configuration {self.name}')

        return cfs_api_data
