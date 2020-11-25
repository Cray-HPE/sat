"""
Unit tests for sat.system.node.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
from unittest import mock

from sat.system.chassis import Chassis
from sat.system.constants import CAB_TYPE_C, CAB_TYPE_S
from sat.system.memory_module import MemoryModule
from sat.system.node import Node
from sat.system.processor import Processor
from tests.system.component_data import get_component_raw_data, CHASSIS_XNAME, NODE_XNAME

DEFAULT_PROCESSOR_COUNT = 2
DEFAULT_NODE_ACCEL_COUNT = 1
DEFAULT_NODE_ACCEL_RISER_COUNT = 1
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
        for _ in range(4):
            fake_mem = mock.Mock()
            fake_mem.capacity_mib = self.mem_module_capacity_gib * 1024
            self.fake_mem_modules.append(fake_mem)
        # Set the memory modules in the node with some xnames beneath the node, not
        # that it should matter.
        self.node.memory_modules = {'{}d{}'.format(NODE_XNAME, index): mm
                                    for index, mm in enumerate(self.fake_mem_modules)}

    def add_fake_processors(self):
        """Add some fake processors to `self.node`."""
        self.fake_processors = []
        # Make the number of processors match the number in LocationInfo, just
        # for the sake of consistency.
        for _ in range(DEFAULT_PROCESSOR_COUNT):
            fake_proc = mock.Mock()
            self.fake_processors.append(fake_proc)
        # Set the processors in the node with some xnames beneath the node, not
        # that it should matter.
        self.node.processors = {'{}p{}'.format(NODE_XNAME, index): proc
                                for index, proc in enumerate(self.fake_processors)}

    def add_fake_node_accels(self):
        """Add some fake node accelerators to `self.node`."""
        self.fake_node_accels = []
        for _ in range(DEFAULT_NODE_ACCEL_COUNT):
            fake_node_accel = mock.Mock()
            self.fake_node_accels.append(fake_node_accel)
        # Set the node accelerators in the node with some xnames beneath the node, not
        # that it should matter.
        self.node.node_accels = {'{}a{}'.format(NODE_XNAME, index): node_accel
                                 for index, node_accel in enumerate(self.fake_node_accels)}

    def add_fake_node_accel_risers(self):
        """Add some fake node accelerator risers to `self.node`."""
        self.fake_node_accel_risers = []
        for _ in range(DEFAULT_NODE_ACCEL_RISER_COUNT):
            fake_node_accel_riser = mock.Mock()
            self.fake_node_accel_risers.append(fake_node_accel_riser)
        # Set the node accelerator risers in the node with some xnames beneath the node, not
        # that it should matter.
        self.node.node_accel_risers = {'{}r{}'.format(NODE_XNAME, index): node_accel_riser
                                       for index, node_accel_riser in enumerate(self.fake_node_accel_risers)}

    def add_fake_drives(self):
        """Add some fake drives to `self.node`."""
        self.fake_drives = []
        # Give each fake drive a 500 GiB capacity
        self.drive_capacity_gib = 500
        for _ in range(4):
            fake_drive = mock.Mock()
            fake_drive.capacity_bytes = 500 * 2**30
            self.fake_drives.append(fake_drive)
        # Set the drives in the node with some xnames beneath the node, not
        # that it should matter.
        self.node.drives = {'{}g1k{}'.format(NODE_XNAME, index): drive
                            for index, drive in enumerate(self.fake_drives)}

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
        self.assertEqual(self.node.cabinet_type, CAB_TYPE_C)

    def test_cabinet_type_without_chassis(self):
        """Test the cabinet_type property without a chassis."""
        self.assertEqual(self.node.cabinet_type, CAB_TYPE_S)

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
        self.add_fake_processors()
        self.assertEqual(DEFAULT_PROCESSOR_COUNT, self.node.processor_count)

    def test_accelerator_count(self):
        """Test the accelerator_count property."""
        self.add_fake_node_accels()
        self.assertEqual(DEFAULT_NODE_ACCEL_COUNT, self.node.accelerator_count)

    def test_accelerator_riser_count(self):
        """Test the accelerator_riser_count property."""
        self.add_fake_node_accel_risers()
        self.assertEqual(DEFAULT_NODE_ACCEL_RISER_COUNT, self.node.accelerator_riser_count)

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

    def test_total_drive_capacity_gib(self):
        """Test the total_drive_capacity_gib property."""
        self.add_fake_drives()
        self.assertEqual(self.node.total_drive_capacity_gib,
                         len(self.fake_drives) * self.drive_capacity_gib)

    def test_drive_count(self):
        """Test the drive_count property."""
        self.add_fake_drives()
        self.assertEqual(self.node.drive_count, len(self.fake_drives))

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
