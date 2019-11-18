"""
Class to represent a node object obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging

from sat.cached_property import cached_property
from sat.system.component import BaseComponent
from sat.system.constants import EX_1_C, EX_1_S, NODE_TYPE, MISSING_VALUE
from sat.system.field import ComponentField
from sat.system.memory_module import MemoryModule
from sat.system.processor import Processor

LOGGER = logging.getLogger(__name__)


class Node(BaseComponent):
    """A node in the system."""

    hsm_type = NODE_TYPE
    arg_name = 'node'
    pretty_name = 'node'

    fields = BaseComponent.fields + [
        ComponentField('Cabinet Type', summarizable=True),
        ComponentField('Memory Type', summarizable=True),
        ComponentField('Memory Manufacturer', summarizable=True),
        ComponentField('Memory Model', summarizable=True),
        ComponentField('Memory Size (GiB)', summarizable=True),
        ComponentField('Processor Count'),
        ComponentField('Processor Manufacturer', summarizable=True),
        ComponentField('Processor Model', summarizable=True),
        ComponentField('BIOS Version'),
    ]

    def __init__(self, raw_data):
        """Creates a node with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the node.
        """
        super().__init__(raw_data)

        # Link to parent Chassis object
        self.chassis = None

        # Dicts mapping from xnames to MemoryModule and Processor objects that
        # are children of this node.
        self.memory_modules = {}
        self.processors = {}

        self.children_by_type = {
            MemoryModule: self.memory_modules,
            Processor: self.processors
        }

    @cached_property
    def cabinet_type(self):
        """str: The cabinet type this node is in."""
        # We currently identify whether a node is in a liquid-cooled cabinet (Mountain)
        # based on whether there is a corresponding chassis in the inventory.
        if self.chassis:
            return EX_1_C
        else:
            return EX_1_S

    @staticmethod
    def get_unique_child_vals(children, field_name):
        """Gets the unique values of the given `field_name` from the children.

        Args:
            children (dict): A dictionary of children to get values from
            field_name (str): The name of the field to get from children.

        Returns:
            A comma-separated list of unique values for the given field_name.
        """
        if not children:
            return MISSING_VALUE
        else:
            return ','.join(set(getattr(child, field_name)
                                for child in children.values()))

    @cached_property
    def processor_manufacturer(self):
        """str: The manufacturer(s) of this node's processors as a comma-separated list."""
        return self.get_unique_child_vals(self.processors, 'manufacturer')

    @cached_property
    def processor_model(self):
        """str: The model(s) of this node's processors as a comma-separated list."""
        return self.get_unique_child_vals(self.processors, 'model')

    @cached_property
    def processor_count(self):
        """int: The number of CPUs on this node."""
        # Use information from location info for now until Mountain processors show up in HSM
        return self.location_info.get("ProcessorSummary", {}).get("Count", 0)

    @cached_property
    def memory_type(self):
        """str: The type(s) of this node's memory as a comma-separated list."""
        return self.get_unique_child_vals(self.memory_modules, 'ddr_type')

    @cached_property
    def memory_manufacturer(self):
        """str: The manufacturer(s) of this node's memory as a comma-separated list."""
        return self.get_unique_child_vals(self.memory_modules, 'manufacturer')

    @cached_property
    def memory_model(self):
        """str: The model(s) of this node's memory as a comma-separated list."""
        return self.get_unique_child_vals(self.memory_modules, 'model')

    @cached_property
    def memory_size_gib(self):
        """float: The total memory size (in GiB) of this node."""
        return sum([mm.capacity_mib for mm in self.memory_modules.values()]) / 1024

    @cached_property
    def bios_version(self):
        """str: The BIOS version for this node."""
        return self.fru_info['BiosVersion']
