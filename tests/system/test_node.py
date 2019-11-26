"""
Unit tests for sat.system.node.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest
from unittest import mock

from sat.system.chassis import Chassis
from sat.system.constants import EX_1_C, EX_1_S
from sat.system.memory_module import MemoryModule
from sat.system.node import Node
from sat.system.processor import Processor
from tests.system.component_data import get_component_raw_data, CHASSIS_XNAME, NODE_XNAME

DEFAULT_PROCESSOR_COUNT = 2
DEFAULT_BIOS_VERSION = '2019.11.b'


def get_node_raw_data(xname=NODE_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='Node', xname=xname, **kwargs)
    component_data['NodeLocationInfo']['MemorySummary'] = {
        'TotalSystemMemoryGiB': 192
    }
    component_data['NodeLocationInfo']['ProcessorSummary'] = {
        'Count': DEFAULT_PROCESSOR_COUNT,
        'Model': 'Central Processor'
    }
    component_data['PopulatedFRU']['NodeFRUInfo']['BiosVersion'] = DEFAULT_BIOS_VERSION
    return component_data


class TestNode(unittest.TestCase):
    """Test the Node class.

    Most of the functionality of this class is covered by tests for the parent
    class, BaseComponent, so these tests use some mock objects.
    """

    def setUp(self):
        """Create a Node object to use in the tests."""
        self.raw_data = get_node_raw_data()
        self.node = Node(self.raw_data)

        self.mock_vals_method = mock.patch.object(Node, 'get_unique_child_vals_str').start()
        self.addCleanup(mock.patch.stopall)

    def add_fake_mem_modules(self):
        """Add some fake memory modules to `self.node`."""
        self.fake_mem_modules = []
        # Give each fake memory module 32 GiB capacity
        self.mem_module_capacity_gib = 32
        for i in range(4):
            fake_mem = mock.Mock()
            fake_mem.capacity_mib = self.mem_module_capacity_gib * 1024
            self.fake_mem_modules.append(fake_mem)
        # Set the memory modules in the node with some xnames beneath the node, not
        # that it should matter.
        self.node.memory_modules = {'{}d{}'.format(NODE_XNAME, index): mm
                                    for index, mm in enumerate(self.fake_mem_modules)}

    def test_init(self):
        """Test initialization of a Node object."""
        self.assertEqual(self.raw_data, self.node.raw_data)
        self.assertEqual({}, self.node.processors)
        self.assertEqual({}, self.node.memory_modules)
        self.assertIsNone(self.node.chassis)
        self.assertIn(Processor, self.node.children_by_type)
        self.assertIn(MemoryModule, self.node.children_by_type)

    def test_cabinet_type_with_chassis(self):
        """Test the cabinet_type property with a chassis."""
        self.node.chassis = Chassis(get_component_raw_data(hsm_type='Chassis',
                                                           xname=CHASSIS_XNAME))
        self.assertEqual(self.node.cabinet_type, EX_1_C)

    def test_cabinet_type_without_chassis(self):
        """Test the cabinet_type property without a chassis."""
        self.assertEqual(self.node.cabinet_type, EX_1_S)

    def test_processor_manufacturer(self):
        """Test the processor_manufacturer property."""
        processor_manufacturer = self.node.processor_manufacturer
        self.mock_vals_method.assert_called_once_with(Processor, 'manufacturer')
        self.assertEqual(processor_manufacturer, self.mock_vals_method.return_value)

    def test_processor_model(self):
        """Test the processor_model property."""
        processor_model = self.node.processor_model
        self.mock_vals_method.assert_called_once_with(Processor, 'model')
        self.assertEqual(processor_model, self.mock_vals_method.return_value)

    def test_processor_count(self):
        """Test the processor_count property."""
        self.assertEqual(DEFAULT_PROCESSOR_COUNT, self.node.processor_count)

    def test_memory_type(self):
        """Test the memory_type property."""
        memory_type = self.node.memory_type
        self.mock_vals_method.assert_called_once_with(MemoryModule, 'memory_type')
        self.assertEqual(memory_type, self.mock_vals_method.return_value)

    def test_memory_device_type(self):
        """Test the memory_device property."""
        memory_device_type = self.node.memory_device_type
        self.mock_vals_method.assert_called_once_with(MemoryModule, 'device_type')
        self.assertEqual(memory_device_type, self.mock_vals_method.return_value)

    def test_memory_manufacturer(self):
        """Test the memory_manufacturer property."""
        memory_manufacturer = self.node.memory_manufacturer
        self.mock_vals_method.assert_called_once_with(MemoryModule, 'manufacturer')
        self.assertEqual(memory_manufacturer, self.mock_vals_method.return_value)

    def test_memory_model(self):
        """Test the memory_model property."""
        memory_model = self.node.memory_model
        self.mock_vals_method.assert_called_once_with(MemoryModule, 'model')
        self.assertEqual(memory_model, self.mock_vals_method.return_value)

    def test_memory_size_gib(self):
        """Test the memory_size property."""
        self.add_fake_mem_modules()
        self.assertEqual(self.node.memory_size_gib,
                         len(self.fake_mem_modules) * self.mem_module_capacity_gib)

    def test_memory_module_count(self):
        """Test the memory_module_count property."""
        self.add_fake_mem_modules()
        self.assertEqual(self.node.memory_module_count, len(self.fake_mem_modules))

    def test_bios_version(self):
        """Test the bios_version property."""
        self.assertEqual(self.node.bios_version, DEFAULT_BIOS_VERSION)

    def test_card_xname(self):
        """Test the card_xname property."""
        with mock.patch.object(self.node.xname, 'get_direct_parent') as mock_parent:
            card_xname = self.node.card_xname
            self.assertEqual(card_xname, mock_parent.return_value)
            mock_parent.assert_called_once_with()

    def test_slot_xname(self):
        """Test the slot_xname property."""
        with mock.patch.object(self.node.xname, 'get_ancestor') as mock_ancestor:
            slot_xname = self.node.slot_xname
            self.assertEqual(slot_xname, mock_ancestor.return_value)
            mock_ancestor.assert_called_once_with(2)


if __name__ == '__main__':
    unittest.main()
