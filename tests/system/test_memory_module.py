"""
Unit tests for sat.system.memory_module.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest

from sat.system.memory_module import MemoryModule
from tests.system.component_data import MEMORY_MODULE_XNAME, get_component_raw_data

MEMORY_TYPE = 'DRAM'
MEMORY_DEVICE_TYPE = 'DDR4'
CAPACITY_MIB = 16384
OPERATING_SPEED_MHZ = 2666


def get_memory_module_raw_data(xname=MEMORY_MODULE_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='Memory', xname=xname, **kwargs)
    extra_fru_info = {
        'MemoryType': MEMORY_TYPE,
        'MemoryDeviceType': MEMORY_DEVICE_TYPE,
        'CapacityMiB': CAPACITY_MIB,
        'OperatingSpeedMhz': OPERATING_SPEED_MHZ
    }
    component_data['PopulatedFRU']['MemoryFRUInfo'].update(extra_fru_info)
    return component_data


class TestMemoryModule(unittest.TestCase):
    """Test the MemoryModule class."""

    def setUp(self):
        """Create a MemoryModule object to use in the tests."""
        self.raw_data = get_memory_module_raw_data()
        self.memory_module = MemoryModule(self.raw_data)

    def test_init(self):
        """Test initialization of a MemoryModule object."""
        self.assertEqual(self.raw_data, self.memory_module.raw_data)
        self.assertIsNone(self.memory_module.node)
        self.assertEqual(self.memory_module.children_by_type, {})

    def test_memory_type(self):
        """Test the memory_type property."""
        self.assertEqual(self.memory_module.memory_type, MEMORY_TYPE)

    def test_memory_device_type(self):
        """Test the device_type property."""
        self.assertEqual(self.memory_module.device_type, MEMORY_DEVICE_TYPE)

    def test_capacity_mib(self):
        """Test the capacity_mib property."""
        self.assertEqual(self.memory_module.capacity_mib, CAPACITY_MIB)

    def test_operating_speed_mhz(self):
        """Test the operating_speed_mhz property."""
        self.assertEqual(self.memory_module.operating_speed_mhz, OPERATING_SPEED_MHZ)


if __name__ == '__main__':
    unittest.main()
