"""
Class to represent a drive object obtained from Hardware State Manager (HSM).

Copyright 2020 Cray Inc. All Rights Reserved.
"""
import logging

from sat.cached_property import cached_property
from sat.system.component import NodeComponent
from sat.system.constants import DRIVE_TYPE
from sat.system.field import ComponentField
from sat.util import bytes_to_gib

LOGGER = logging.getLogger(__name__)


class Drive(NodeComponent):
    """A drive in the system."""

    hsm_type = DRIVE_TYPE
    arg_name = 'drive'
    pretty_name = 'drive'

    fields = NodeComponent.fields + [
        ComponentField('Media Type'),
        ComponentField('Capacity (GiB)'),
        ComponentField('Percent Life Left')
    ]

    @cached_property
    def media_type(self):
        """str: the media type (e.g. HDD or SSD)"""
        return self.fru_info['MediaType']

    @cached_property
    def capacity_bytes(self):
        """int: the capacity of the drive in bytes"""
        return self.fru_info['CapacityBytes']

    @cached_property
    def capacity_gib(self):
        """float: the capacity of the drive in GiB, rounded to two decimal points"""
        # The value of CapacityBytes should be numeric, but check for robustness
        try:
            capacity_bytes = float(self.capacity_bytes)
        except ValueError:
            LOGGER.warning("Found non-numeric value for CapacityBytes of drive '%s': %s",
                           self, self.capacity_bytes)
            return self.capacity_bytes
        return bytes_to_gib(capacity_bytes)

    @cached_property
    def percent_life_left(self):
        """int: The predicted percentage of life left in the drive."""
        return self.fru_info['PredictedMediaLifeLeftPercent']
