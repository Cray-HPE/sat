"""
Class to represent a memory module object obtained from Hardware State Manager (HSM).

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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
        ComponentField('FRUID'),
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
