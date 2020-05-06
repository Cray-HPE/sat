"""
Unit tests for sat.system.cmm_rectifier.

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
import unittest

from sat.constants import EMPTY_VALUE
from sat.system.cmm_rectifier import CMMRectifier
from tests.system.component_data import CMM_RECTIFIER_XNAME, get_component_raw_data

POWER_INPUT_WATTS = '5000'
POWER_OUTPUT_WATTS = '3000'
POWER_SUPPLY_TYPE = ''
FIRMWARE_VERSION = '1.2.3'


def get_cmm_rectifier_raw_data(xname=CMM_RECTIFIER_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='CMMRectifier', xname=xname, **kwargs)
    extra_fru_info = {
        'PowerInputWatts': POWER_INPUT_WATTS,
        'PowerOutputWatts': POWER_OUTPUT_WATTS,
        'PowerSupplyType': POWER_SUPPLY_TYPE,
    }
    extra_location_info = {
        'FirmwareVersion': FIRMWARE_VERSION
    }
    component_data['PopulatedFRU']['CMMRectifierFRUInfo'].update(extra_fru_info)
    component_data['CMMRectifierLocationInfo'].update(extra_location_info)
    return component_data


class TestCMMRectifier(unittest.TestCase):
    """Test the CMMRectifier class."""

    def setUp(self):
        """Create a CMMRectifier object to use in the tests."""
        self.raw_data = get_cmm_rectifier_raw_data()
        self.cmm_rectifier = CMMRectifier(self.raw_data)

    def test_init(self):
        """Test initialization of a CMMRectifier object."""
        self.assertEqual(self.raw_data, self.cmm_rectifier.raw_data)

    def test_power_input_watts(self):
        """Test the power_input_watts property."""
        self.assertEqual(self.cmm_rectifier.power_input_watts, POWER_INPUT_WATTS)

    def test_power_output_watts(self):
        """Test the power_output_watts property."""
        self.assertEqual(self.cmm_rectifier.power_output_watts, POWER_OUTPUT_WATTS)

    def test_power_supply_type(self):
        """Test the power_supply_type property."""
        self.assertEqual(self.cmm_rectifier.power_supply_type, EMPTY_VALUE)

    def test_firmware_version(self):
        """Test the firmware_version property."""
        self.assertEqual(self.cmm_rectifier.firmware_version, FIRMWARE_VERSION)


if __name__ == '__main__':
    unittest.main()
