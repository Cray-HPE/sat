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
        ComponentField('Memory Device Type', summarizable=True),
        ComponentField('Memory Manufacturer', summarizable=True),
        ComponentField('Memory Model', summarizable=True),
        ComponentField('Memory Size (GiB)', summarizable=True),
        ComponentField('Memory Module Count', summarizable=True),
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

    @cached_property
    def processor_manufacturer(self):
        """str: The manufacturer(s) of this node's processors as a comma-separated list."""
        return self.get_unique_child_vals_str(Processor, 'manufacturer')

    @cached_property
    def processor_model(self):
        """str: The model(s) of this node's processors as a comma-separated list."""
        return self.get_unique_child_vals_str(Processor, 'model')

    @cached_property
    def processor_count(self):
        """int: The number of CPUs on this node."""
        # Use information from location info for now until Mountain processors show up in HSM
        return self.location_info.get('ProcessorSummary', {}).get('Count', 0)

    @cached_property
    def memory_type(self):
        """str: The memory type(s) of this node's memory as a comma-separated list."""
        return self.get_unique_child_vals_str(MemoryModule, 'memory_type')

    @cached_property
    def memory_device_type(self):
        """str: The device type(s) of this node's memory as a comma-separated list."""
        return self.get_unique_child_vals_str(MemoryModule, 'device_type')

    @cached_property
    def memory_manufacturer(self):
        """str: The manufacturer(s) of this node's memory as a comma-separated list."""
        return self.get_unique_child_vals_str(MemoryModule, 'manufacturer')

    @cached_property
    def memory_model(self):
        """str: The model(s) of this node's memory as a comma-separated list."""
        return self.get_unique_child_vals_str(MemoryModule, 'model')

    @cached_property
    def memory_size_gib(self):
        """float: The total memory size (in GiB) of this node."""
        return sum([mm.capacity_mib for mm in self.memory_modules.values()]) / 1024

    @cached_property
    def memory_module_count(self):
        """int: The number of memory modules this node has."""
        return len(self.memory_modules)

    @cached_property
    def bios_version(self):
        """str: The BIOS version for this node."""
        return self.fru_info['BiosVersion']

    @cached_property
    def card_xname(self):
        """sat.xname.XName: The xname of this node's node card"""
        return self.xname.get_direct_parent()

    @cached_property
    def slot_xname(self):
        """sat.xname.XName: The xname of this node's slot"""
        return self.xname.get_ancestor(2)
