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
Unit tests for sat.system.node_bmc.
"""
import unittest

from sat.constants import EMPTY_VALUE
from sat.system.node_bmc import NodeBMC
from tests.system.component_data import NODE_BMC_XNAME, get_component_raw_data

MANAGER_TYPE = ''
FIRMWARE_VERSION = '1.2.3'


def get_node_bmc_raw_data(xname=NODE_BMC_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='NodeBMC', xname=xname, **kwargs)
    extra_fru_info = {
        'ManagerType': MANAGER_TYPE,
    }
    extra_location_info = {
        'FirmwareVersion': FIRMWARE_VERSION
    }
    component_data['PopulatedFRU']['NodeBMCFRUInfo'].update(extra_fru_info)
    component_data['NodeBMCLocationInfo'].update(extra_location_info)
    return component_data


class TestNodeBMC(unittest.TestCase):
    """Test the NodeBMC class."""

    def setUp(self):
        """Create a NodeBMC object to use in the tests."""
        self.raw_data = get_node_bmc_raw_data()
        self.node_bmc = NodeBMC(self.raw_data)

    def test_init(self):
        """Test initialization of a NodeBMC object."""
        self.assertEqual(self.raw_data, self.node_bmc.raw_data)

    def test_manager_type(self):
        """Test the manager_type property."""
        self.assertEqual(self.node_bmc.manager_type, EMPTY_VALUE)

    def test_firmware_version(self):
        """Test the firmware_version property."""
        self.assertEqual(self.node_bmc.firmware_version, FIRMWARE_VERSION)


if __name__ == '__main__':
    unittest.main()
