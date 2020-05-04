"""
Class to represent a CMMRectifier object obtained from Hardware State Manager (HSM).

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
import logging

from sat.cached_property import cached_property
from sat.system.component import BaseComponent
from sat.system.constants import CMM_RECTIFIER_TYPE
from sat.system.field import ComponentField

LOGGER = logging.getLogger(__name__)


class CMMRectifier(BaseComponent):
    """A Chassis Management Module Rectifier (i.e. power supply) in the system."""

    hsm_type = CMM_RECTIFIER_TYPE
    arg_name = 'cmm_rectifier'
    pretty_name = 'CMM rectifier'

    fields = BaseComponent.fields + [
        ComponentField('Power Input Watts'),
        ComponentField('Power Output Watts'),
        ComponentField('Power Supply Type'),
        ComponentField('Firmware Version')
    ]

    @cached_property
    def power_input_watts(self):
        """str: the power input in watts"""
        return self.fru_info['PowerInputWatts']

    @cached_property
    def power_output_watts(self):
        """str: the power output in watts"""
        return self.fru_info['PowerOutputWatts']

    @cached_property
    def power_supply_type(self):
        """str: the power output in watts"""
        return self.fru_info['PowerSupplyType']

    @cached_property
    def firmware_version(self):
        """str: the firmware version"""
        return self.location_info['FirmwareVersion']
