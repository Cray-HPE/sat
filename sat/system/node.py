#
# MIT License
#
# (C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP
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
Class to represent a node object obtained from Hardware State Manager (HSM).
"""
import logging

from sat.cached_property import cached_property
from sat.system.component import BaseComponent
from sat.system.constants import CAB_TYPE_C, CAB_TYPE_S, NODE_TYPE
from sat.system.drive import Drive
from sat.system.field import ComponentField
from sat.system.memory_module import MemoryModule
from sat.system.node_accel import NodeAccel
from sat.system.node_accel_riser import NodeAccelRiser
from sat.system.node_hsn_nic import NodeHsnNic
from sat.system.processor import Processor
from sat.util import bytes_to_gib

LOGGER = logging.getLogger(__name__)


class Node(BaseComponent):
    """A node in the system."""

    hsm_type = NODE_TYPE
    arg_name = 'node'
    pretty_name = 'node'
    default_show_xnames = True

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
        ComponentField('Accelerator Count', summarizable=True),
        ComponentField('Accelerator Riser Count', summarizable=True),
        ComponentField('HSN NIC Count', summarizable=True),
        ComponentField('Drive Count', summarizable=True),
        ComponentField('Total Drive Capacity (GiB)', summarizable=True),
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
        self.node_accels = {}
        self.node_accel_risers = {}
        self.node_hsn_nics = {}
        self.drives = {}

        self.children_by_type = {
            MemoryModule: self.memory_modules,
            Processor: self.processors,
            NodeAccel: self.node_accels,
            NodeAccelRiser: self.node_accel_risers,
            NodeHsnNic: self.node_hsn_nics,
            Drive: self.drives
        }

    @cached_property
    def cabinet_type(self):
        """str: The cabinet type this node is in."""
        # We currently identify whether a node is in a liquid-cooled cabinet (Mountain)
        # based on whether there is a corresponding chassis in the inventory.
        if self.chassis:
            return CAB_TYPE_C
        else:
            return CAB_TYPE_S

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
        return len(self.processors)

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
        megs = sum([mm.capacity_mib for mm in self.memory_modules.values()])
        gigs = megs / 1024
        return round(gigs, 2)

    @cached_property
    def memory_module_count(self):
        """int: The number of memory modules this node has."""
        return len(self.memory_modules)

    @cached_property
    def accelerator_count(self):
        """int: The number of node_accels this node has."""
        return len(self.node_accels)

    @cached_property
    def accelerator_riser_count(self):
        """int: The number of node_accel_risers this node has."""
        return len(self.node_accel_risers)

    @cached_property
    def hsn_nic_count(self):
        """int: The number of node_hsn_nics this node has."""
        return len(self.node_hsn_nics)

    @cached_property
    def drive_count(self):
        """int: The number of drives this node has."""
        return len(self.drives)

    @cached_property
    def total_drive_capacity_gib(self):
        """float: The total capacity in GiB of all drives in this node"""
        try:
            bytes = sum([drive.capacity_bytes for drive in self.drives.values()])
            return bytes_to_gib(bytes)
        except TypeError as err:
            LOGGER.warning("Unable to compute total drive capacity for node "
                           "'%s' due to non-numeric drive capacity values: %s",
                           self, err)
            return 0

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
