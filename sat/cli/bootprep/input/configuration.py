#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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

from csm_api_client.service.gateway import APIError
from csm_api_client.service.cfs import CFSConfigurationError

from sat.cached_property import cached_property
from sat.cli.bootprep.constants import LATEST_VERSION_VALUE
from sat.cli.bootprep.errors import InputItemCreateError
from sat.cli.bootprep.input.base import (
    BaseInputItem,
    BaseInputItemCollection,
    jinja_rendered,
)
from sat.config import get_config_value
from sat.util import get_val_by_path

LOGGER = logging.getLogger(__name__)


class InputConfigurationLayerBase(ABC):
    """An object representing data in common between layers and additional inventory"""

    # CRAYSAT-1174: Specifying a 'branch' in a CFS configuration layer is not
    # supported until CSM 1.2. Toggling this variable will change the behavior
    # for both GitCFSConfigurationLayers and ProductCFSConfigurationLayers.
    resolve_branches = True

    # The jinja_rendered properties here are only rendered at item creation time
    template_render_err = InputItemCreateError

    def __init__(self, layer_data, jinja_env, cfs_client):
        """Create a new configuration layer.

        Args:
            layer_data (dict): the layer data from the input instance
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API
                client to use when creating the layer in CFS
        """
        self.layer_data = layer_data
        self.jinja_env = jinja_env
        self.cfs_client = cfs_client

    @property
    @jinja_rendered
    def name(self):
        """str or None: the name specified for the layer"""
        return self.layer_data.get('name')

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

    @abstractmethod
    def get_cfs_api_data(self):
        """Get the data to pass to the CFS API to create this layer.

        Returns:
            dict: The dictionary of data to pass to the CFS API to create the
                layer.

        Raises:
            InputItemCreateError: if there was a failure to obtain the data
                needed to create the layer in CFS.
        """
        pass


class InputConfigurationLayer(InputConfigurationLayerBase, ABC):
    """A CFS configuration layer as defined in the bootprep input file"""

    @property
    @jinja_rendered
    def playbook(self):
        """str: the playbook specified in the layer"""
        # playbook is now required by the schema
        return self.layer_data['playbook']

    @property
    def ims_require_dkms(self):
        """str or None: whether to enable DKMS when this layer customizes an IMS image"""
        return get_val_by_path(self.layer_data, 'special_parameters.ims_require_dkms')

    @staticmethod
    def get_configuration_layer(layer_data, jinja_env, cfs_client, product_catalog):
        """Get and return a new InputConfigurationLayer for the given layer data.

        Args:
            layer_data (dict): The data for a layer, already validated against
                the bootprep input file schema.
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API
                client to use when creating the layer in CFS
            product_catalog (cray_product_catalog.query.ProductCatalog):
                the product catalog object

        Raises:
            ValueError: if neither 'git' nor 'product' keys are present in the
                input `layer_data`. This will not happen if the input is
                properly validated against the schema.
        """
        if 'git' in layer_data:
            return GitInputConfigurationLayer(layer_data, jinja_env, cfs_client)
        elif 'product' in layer_data:
            return ProductInputConfigurationLayer(layer_data, jinja_env, cfs_client, product_catalog)
        else:
            raise ValueError('Unrecognized type of configuration layer')


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
        return self.layer_data['git'].get('commit')

    def get_cfs_api_data(self):
        """Get the data to pass to the CFS API to create this layer.

        Returns:
            dict: The dictionary of data to pass to the CFS API to create the
                layer.

        Raises:
            InputItemCreateError: if there was a failure to obtain the data
                needed to create the layer in CFS.
        """
        layer_cls = self.cfs_client.configuration_cls.cfs_config_layer_cls
        try:
            layer = layer_cls.from_clone_url(
                clone_url=self.clone_url, branch=self.branch, commit=self.commit,
                name=self.name, playbook=self.playbook, ims_require_dkms=self.ims_require_dkms
            )
        except ValueError as err:
            raise InputItemCreateError(str(err))

        if self.resolve_branches:
            try:
                layer.resolve_branch_to_commit_hash()
            except CFSConfigurationError as err:
                raise InputItemCreateError(str(err))

        return layer.req_payload


class ProductInputConfigurationLayer(InputConfigurationLayer):
    """
    A configuration layer that is defined with the name of a product
    and the version or branch.
    """
    def __init__(self, layer_data, jinja_env, cfs_client, product_catalog):
        """Create a new ProductInputConfigurationLayer.

        Args:
            layer_data (dict): the layer data from the input instance
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API
                client to use when creating the layer in CFS
            product_catalog (cray_product_catalog.query.ProductCatalog or None):
                the product catalog object
        """
        super().__init__(layer_data, jinja_env, cfs_client)
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
        # The 'version' property is optional
        return self.layer_data['product'].get('version')

    @cached_property
    @jinja_rendered
    def branch(self):
        # The 'branch' property is optional
        return self.layer_data['product'].get('branch')

    @cached_property
    def commit(self):
        # The 'commit' property is optional
        return self.layer_data['product'].get('commit')

    def get_cfs_api_data(self):
        """Get the data to pass to the CFS API to create this layer.

        Returns:
            dict: The dictionary of data to pass to the CFS API to create the
                layer.

        Raises:
            InputItemCreateError: if there was a failure to obtain the data
                needed to create the layer in CFS.
        """
        layer_cls = self.cfs_client.configuration_cls.cfs_config_layer_cls

        try:
            layer = layer_cls.from_product_catalog(
                product_name=self.product_name, api_gw_host=get_config_value('api_gateway.host'),
                product_version=self.product_version, commit=self.commit, branch=self.branch,
                name=self.name, playbook=self.playbook, ims_require_dkms=self.ims_require_dkms,
                product_catalog=self.product_catalog
            )
            if self.resolve_branches:
                layer.resolve_branch_to_commit_hash()
        except (ValueError, CFSConfigurationError) as err:
            raise InputItemCreateError(str(err))

        return layer.req_payload


class AdditionalInventory(InputConfigurationLayerBase):
    """Additional inventory data for a CFS configuration"""

    @property
    def clone_url(self):
        """str: the clone URL for the additional inventory"""
        return self.layer_data['url']

    @property
    def commit(self):
        """str or None: the commit hash or None if branch was specified instead"""
        return self.layer_data.get('commit')

    @property
    def branch(self):
        """str or None: the branch or None if commit was specified instead"""
        return self.layer_data.get('branch')

    @property
    def name(self):
        """str or None: the optional name of the additional inventory"""
        return self.layer_data.get('name')

    def get_cfs_api_data(self):
        """Get the data to pass to the CFS API to create this layer.

        Returns:
            dict: The dictionary of data to pass to the CFS API to create the
                layer.

        Raises:
            InputItemCreateError: if there was a failure to obtain the data
                needed to create the layer in CFS.
        """
        layer_cls = self.cfs_client.configuration_cls.cfs_additional_inventory_cls

        try:
            layer = layer_cls.from_clone_url(clone_url=self.clone_url, name=self.name,
                                             branch=self.branch, commit=self.commit)
        except ValueError as err:
            raise InputItemCreateError(str(err))
        try:
            if self.resolve_branches:
                layer.resolve_branch_to_commit_hash()
        except CFSConfigurationError as err:
            raise InputItemCreateError(str(err))

        return layer.req_payload


class InputConfiguration(BaseInputItem):
    """A CFS Configuration from a bootprep input file."""
    description = 'CFS configuration'

    report_attrs = ['name']

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
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API client
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
        self.layers = [InputConfigurationLayer.get_configuration_layer(layer_data, jinja_env,
                                                                       cfs_client, product_catalog)
                       for layer_data in self.data['layers']]

        self.additional_inventory = None
        if 'additional_inventory' in self.data:
            self.additional_inventory = AdditionalInventory(self.data['additional_inventory'], jinja_env,
                                                            cfs_client)

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

        failed_inventory = False
        if self.additional_inventory:
            try:
                cfs_api_data['additional_inventory'] = self.additional_inventory.get_cfs_api_data()
            except InputItemCreateError as err:
                LOGGER.error(f'Failed to resolve additional_inventory of '
                             f'configuration {self.name}: {err}')
                failed_inventory = True

        failed_layers = []
        for idx, layer in enumerate(self.layers):
            try:
                cfs_api_data['layers'].append(layer.get_cfs_api_data())
            except InputItemCreateError as err:
                LOGGER.error(f'Failed to create layers[{idx}] of configuration '
                             f'{self.name}: {err}')
                failed_layers.append(layer)

        if failed_layers or failed_inventory:
            failure_causes = []
            if failed_layers:
                failure_causes.append(f'failure to create {len(failed_layers)} layer(s)')
            if failed_inventory:
                failure_causes.append('failure to resolve additional_inventory')
            raise InputItemCreateError(f'Failed to create configuration {self.name} '
                                       f'due to {" and ".join(failure_causes)}')

        return cfs_api_data

    def create(self, payload):
        """Create the CFS configuration with a request to the CFS API.

        Args:
            payload (dict): the payload to pass to the CFS API to create the
                CFS configuration
        """
        # TODO: Consider using a method of the CFSConfiguration class from csm_api_client
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
            cfs_client (csm_api_client.service.cfs.CFSClientBase): the CFS API client
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
