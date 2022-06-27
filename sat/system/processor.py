#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Class to represent a processor object obtained from Hardware State Manager (HSM).
"""

from sat.cached_property import cached_property
from sat.system.component import NodeComponent
from sat.system.constants import PROCESSOR_TYPE
from sat.system.field import ComponentField


class Processor(NodeComponent):
    """Represents a processor in the system."""

    hsm_type = PROCESSOR_TYPE
    arg_name = 'proc'
    pretty_name = 'processor'

    fields = [
        ComponentField('xname'),
        ComponentField('FRUID'),
        # Allow summary by manufacturer and model unlike in BaseComponent
        ComponentField('Manufacturer', summarizable=True),
        ComponentField('Model', summarizable=True),
        ComponentField('Part Number'),
        ComponentField('SKU'),
        ComponentField('Serial Number'),
        ComponentField('Total Cores', summarizable=True),
        ComponentField('Total Threads', summarizable=True),
        ComponentField('Max Speed (MHz)', summarizable=True)
    ]

    def __init__(self, raw_data):
        """Creates a processor with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the processor.
        """
        super().__init__(raw_data)

        # Links to objects that are ancestors of this component in the hierarchy
        self.node = None

    @cached_property
    def total_cores(self):
        """int: The number of cores this processor has."""
        return self.fru_info['TotalCores']

    @cached_property
    def total_threads(self):
        """int: The total number of threads this processor has."""
        return self.fru_info['TotalThreads']

    @cached_property
    def max_speed_mhz(self):
        """int: The maximum speed of the processor."""
        return self.fru_info['MaxSpeedMHz']
