#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.system.mgmt_switch.
"""
import unittest

from sat.constants import EMPTY_VALUE
from sat.system.mgmt_switch import MgmtSwitch
from tests.system.component_data import MGMT_SWITCH_XNAME, get_component_raw_data

CHASSIS_TYPE = ''


def get_mgmt_switch_raw_data(xname=MGMT_SWITCH_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='MgmtSwitch', xname=xname, **kwargs)
    extra_fru_info = {
        'ChassisType': CHASSIS_TYPE,
    }
    component_data['PopulatedFRU']['MgmtSwitchFRUInfo'].update(extra_fru_info)
    return component_data


class TestMgmtSwitch(unittest.TestCase):
    """Test the MgmtSwitch class."""

    def setUp(self):
        """Create a MgmtSwitch object to use in the tests."""
        self.raw_data = get_mgmt_switch_raw_data()
        self.mgmt_switch = MgmtSwitch(self.raw_data)

    def test_init(self):
        """Test initialization of a MgmtSwitch object."""
        self.assertEqual(self.raw_data, self.mgmt_switch.raw_data)

    def test_chassis_type(self):
        """Test the chassis_type property."""
        self.assertEqual(self.mgmt_switch.chassis_type, EMPTY_VALUE)


if __name__ == '__main__':
    unittest.main()
