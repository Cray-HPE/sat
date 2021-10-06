"""
Implements the creation of CFS configurations from the input file.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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

from abc import ABC, abstractmethod
import json
import logging
import os
import warnings

from kubernetes.client import ApiException, CoreV1Api
from kubernetes.config import ConfigException, load_kube_config
from pkg_resources import parse_version
import yaml
from yaml import YAMLError, YAMLLoadWarning

from sat.apiclient import APIError, CFSClient
from sat.cli.bootprep.errors import ConfigurationCreateError
from sat.cached_property import cached_property
from sat.session import SATSession
from sat.util import pester_choices

# This value is used to specify that the latest version of a product is desired
LATEST_VERSION_VALUE = 'latest'

LOGGER = logging.getLogger(__name__)


class CFSConfigurationLayer(ABC):
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

    def __init__(self, layer_data):
        """Create a new configuration layer."""
        self.layer_data = layer_data

    @property
    def playbook(self):
        """str or None: the playbook specified in the layer"""
        return self.layer_data.get('playbook')

    @property
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
            property_value = getattr(self, self_property)
            if property_value is not None:
                cfs_layer_data[cfs_property] = property_value

        return cfs_layer_data

    @staticmethod
    def get_configuration_layer(layer_data):
        """Get and return a new CFSConfigurationLayer for the given layer data.

        Args:
            layer_data (dict): The data for a layer, already validated against
                the bootprep input file schema.

        Raises:
            ValueError: if neither 'git' nor 'product' keys are present in the
                input `layer_data`. This will not happen if the input is
                properly validated against the schema.
        """
        if 'git' in layer_data:
            return GitCFSConfigurationLayer(layer_data)
        elif 'product' in layer_data:
            return ProductCFSConfigurationLayer(layer_data)
        else:
            raise ValueError('Unrecognized type of configuration layer')


class GitCFSConfigurationLayer(CFSConfigurationLayer):
    """
    A configuration layer that is defined with an explicit Git URL
    and a branch or a commit hash.
    """
    @property
    def clone_url(self):
        # The 'url' property is required by the schema
        return self.layer_data['git']['url']

    @property
    def branch(self):
        # The 'branch' property is optional
        return self.layer_data['git'].get('branch')

    @property
    def commit(self):
        # The 'commit' property is optional
        return self.layer_data['git'].get('commit')


class ProductCFSConfigurationLayer(CFSConfigurationLayer):
    """
    A configuration layer that is defined with the name of a product
    and the version or branch.
    """
    @cached_property
    def k8s_api(self):
        """kubernetes.client.CoreV1Api: a kubernetes core API client"""
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            raise ConfigurationCreateError(f'Failed to load Kubernetes config which is required '
                                           f'to read product catalog data: {err}')

        return CoreV1Api()

    @property
    def product_name(self):
        """str: the name of the product"""
        # The 'name' property is required
        return self.layer_data['product']['name']

    @property
    def product_version(self):
        """str or None: the version specified for the product"""
        # The 'version' property is optional. If not specified, assume latest
        return self.layer_data['product'].get('version', LATEST_VERSION_VALUE)

    @cached_property
    def product_version_data(self):
        """dict: the data for the given version of the product from the product catalog"""
        k8s_api = self.k8s_api
        try:
            response = k8s_api.read_namespaced_config_map('cray-product-catalog', 'services')
        except ApiException as err:
            raise ConfigurationCreateError(f'Failed to read Kubernetes ConfigMap '
                                           f'cray-product-catalog in services namespace: {err}')

        config_map_data = response.data or {}
        try:
            product_data = yaml.safe_load(config_map_data[self.product_name])
        except KeyError:
            raise ConfigurationCreateError(f'Product {self.product_name} not present in product '
                                           f'catalog')
        except YAMLError:
            raise ConfigurationCreateError(f'Product {self.product_name} data not in valid YAML '
                                           f'format in product catalog')

        if self.product_version == LATEST_VERSION_VALUE:
            latest_version = sorted(product_data.keys(), key=parse_version)[-1]
            LOGGER.info(f'Using latest version ({latest_version}) of product {self.product_name}')
            return product_data[latest_version]

        try:
            return product_data[self.product_version]
        except KeyError:
            raise ConfigurationCreateError(f'No match found for version {self.product_version} '
                                           f'of product {self.product_name} in product catalog')

    @cached_property
    def clone_url(self):
        try:
            return self.product_version_data['configuration']['clone_url']
        except KeyError as err:
            raise ConfigurationCreateError(f'No clone URL present for product {self.product_name}; '
                                           f'missing key: {err}')

    @cached_property
    def branch(self):
        # The 'branch' property is optional
        return self.layer_data['product'].get('branch')

    @cached_property
    def commit(self):
        # If branch is specified, no commit should be specified
        if self.branch is not None:
            return None

        # If no branch is specified get the commit from the product catalog
        try:
            return self.product_version_data['configuration']['commit']
        except KeyError as err:
            raise ConfigurationCreateError(f'No commit present for product {self.product_name}; '
                                           f'missing key: {err}')


class CFSConfiguration:
    """A CFS Configuration from a bootprep input file."""

    def __init__(self, configuration_data):
        """Create a new CFSConfiguration.

        Args:
            configuration_data (dict): The data for a configuration, already
                validated against the bootprep input file schema.

        Raises:
            ValueError: if any of the layers in the given `configuration_data`
                have neither 'git' nor 'product' keys in their data. This won't
                happen if the input is properly validated against the schema.
        """
        self.configuration_data = configuration_data
        # The 'layers' property is required and must be a list, but it can be empty
        self.layers = [CFSConfigurationLayer.get_configuration_layer(layer_data)
                       for layer_data in self.configuration_data['layers']]

    @property
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


def handle_existing_configs(cfs_client, input_configs, args):
    """Check for configs that already exist and return the configs to create.

    Args:
        cfs_client (CFSClient): The CFS API client
        input_configs (list of CFSConfiguration): The list of CFS configurations
            defined in the input instance.
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootprep subcommand.

    Returns:
         list of CFSConfiguration: the list of CFS configurations that should
            be created.

    Raises:
        ConfigurationCreateError: If unable to query CFS for existing configurations
            or if some configs already exist and user requested to abort.
    """
    try:
        cfs_config_names = set(config.get('name') for config in cfs_client.get_configurations())
    except APIError as err:
        raise ConfigurationCreateError(f'Failed to query CFS for existing configurations: {err}')

    existing_names = [config.name for config in input_configs
                      if config.name in cfs_config_names]

    verb = ('will be', 'would be')[args.dry_run]

    if not existing_names:
        return input_configs

    overwrite = args.overwrite_configs
    skip = args.skip_existing_configs

    if not overwrite and not skip:
        answer = pester_choices(f'The following CFS configurations already exist: '
                                f'{", ".join(existing_names)}. Would you like to skip, '
                                f'overwrite, or abort?', ('skip', 'overwrite', 'abort'))
        if answer == 'abort':
            raise ConfigurationCreateError('User chose to abort')
        skip = answer == 'skip'
        overwrite = answer == 'overwrite'

    msg_template = (f'The following CFS configurations already exist and '
                    f'{verb} %(action)s: {", ".join(existing_names)}')
    if overwrite:
        LOGGER.info(msg_template, {'action': 'overwritten'})
        return input_configs
    elif skip:
        LOGGER.info(msg_template, {'action': 'skipped'})
        # Create all configs that do not already exist
        return [config for config in input_configs if config.name not in existing_names]


def create_cfs_configurations(instance, args):
    """Create the CFS configurations defined in the given instance.

    Args:
        instance (dict): The full bootprep input dictionary loaded from the
            input file and already validated against the schema.
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootprep subcommand.

    Returns:
        None

    Raises:
        ConfigurationCreateError: if there was a failure to create any of the
            configurations defined in `instance`
    """

    # The 'configurations' key is optional in the instance
    input_configs = [CFSConfiguration(configuration)
                     for configuration in instance.get('configurations', [])]

    if not input_configs:
        LOGGER.info('Given input did not define any CFS configurations')
        return

    create_verb = ('Creating', 'Would create')[args.dry_run]

    LOGGER.info(f'{create_verb} {len(input_configs)} CFS configuration(s)')

    cfs_client = CFSClient(SATSession())
    configs_to_create = handle_existing_configs(cfs_client, input_configs, args)
    failed_configs = []

    if args.save_files and args.output_dir != '.':
        try:
            os.makedirs(args.output_dir, exist_ok=True)
        except OSError as err:
            LOGGER.warning(f'Failed to create output directory {args.output_dir}: {err}. '
                           f'Files will not be saved.')
            args.save_files = False

    for cfs_configuration in configs_to_create:
        config_name = cfs_configuration.name
        LOGGER.info(f'{create_verb} CFS configuration with name "{config_name}"')

        try:
            request_body = cfs_configuration.get_cfs_api_data()
        except ConfigurationCreateError as err:
            LOGGER.error(f'Failed to get data to create configuration {config_name}: {err}')
            failed_configs.append(cfs_configuration)
            continue

        if args.save_files:
            file_name = os.path.join(args.output_dir, f'cfs-config-{config_name}.json')
            LOGGER.info(f'Saving CFS config request body to {file_name}')

            try:
                with open(file_name, 'w') as f:
                    json.dump(request_body, f, indent=4)
            except OSError as err:
                LOGGER.warning(f'Failed to write CFS config request body to {file_name}: {err}')

        if not args.dry_run:
            try:
                # request_body guaranteed to have 'name' key, so no need to catch ValueError
                cfs_client.put_configuration(cfs_configuration.name, request_body)
            except APIError as err:
                LOGGER.error(f'Failed to create or update configuration '
                             f'{cfs_configuration.name}: {err}')
                failed_configs.append(cfs_configuration)

    if failed_configs:
        raise ConfigurationCreateError(f'Failed to create {len(failed_configs)} configuration(s)')
