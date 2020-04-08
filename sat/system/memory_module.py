"""
Class to represent a memory module object obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from sat.cached_property import cached_property
from sat.system.component import NodeComponent
from sat.system.constants import MEMORY_TYPE
from sat.system.field import ComponentField


class MemoryModule(NodeComponent):
    """A memory module in the system."""

    hsm_type = MEMORY_TYPE
    arg_name = 'mem'
    pretty_name = 'memory module'

    fields = [
        ComponentField('xname'),
        # Allow summary by manufacturer and model unlike in BaseComponent
        ComponentField('Manufacturer', summarizable=True),
        ComponentField('Model', summarizable=True),
        ComponentField('Part Number'),
        ComponentField('SKU'),
        ComponentField('Serial Number'),
        ComponentField('Memory Type', summarizable=True),
        ComponentField('Device Type', summarizable=True),
        ComponentField('Capacity (MiB)', summarizable=True),
        ComponentField('Operating Speed (MHz)', summarizable=True)
    ]

    def __init__(self, raw_data):
        """Creates a memory module with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the memory module.
        """
        super().__init__(raw_data)

        # Links to parent Node object
        self.node = None

    @cached_property
    def memory_type(self):
        """str: The memory type of the memory module."""
        return self.fru_info['MemoryType']

    @cached_property
    def device_type(self):
        """str: The device type of the memory module."""
        return self.fru_info['MemoryDeviceType']

    @cached_property
    def capacity_mib(self):
        """str: The capacity of the memory module in MiB."""
        return self.fru_info['CapacityMiB']

    @cached_property
    def operating_speed_mhz(self):
        """str: The operating speed of the memory module."""
        return self.fru_info['OperatingSpeedMhz']
