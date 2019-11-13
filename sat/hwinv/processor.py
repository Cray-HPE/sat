"""
Class to represent a processor object obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from sat.cached_property import cached_property
from sat.hwinv.component import BaseComponent
from sat.hwinv.constants import PROCESSOR_TYPE
from sat.hwinv.field import ComponentField


class Processor(BaseComponent):
    """Represents a processor in the system."""

    hsm_type = PROCESSOR_TYPE
    arg_name = 'proc'
    pretty_name = 'processor'

    fields = [
        ComponentField('xname'),
        # Allow summarization by manufacturer and model unlike in BaseComponent
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
