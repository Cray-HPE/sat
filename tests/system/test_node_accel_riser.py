#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.system.node_accel_riser.
"""
import unittest

from sat.system.node_accel_riser import NodeAccelRiser
from tests.system.component_data import NODE_ACCEL_RISER_XNAME, get_component_raw_data

PRODUCER = 'NVIDIA'
ENGINEERING_CHANGE_LEVEL = 'A00'
PCB_SERIAL_NUMBER = '1572620530162'


def get_riser_raw_data(xname=NODE_ACCEL_RISER_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='NodeAccelRiser', xname=xname, **kwargs)
    extra_fru_info = {
        'Producer': PRODUCER,
        'EngineeringChangeLevel': ENGINEERING_CHANGE_LEVEL,
        'Oem': {
            'PCBSerialNumber': PCB_SERIAL_NUMBER
        }
    }
    component_data['PopulatedFRU']['NodeAccelRiserFRUInfo'].update(extra_fru_info)
    return component_data


class TestNodeAccelRiser(unittest.TestCase):
    """Test the NodeAccelRiser class."""

    def setUp(self):
        """Create a NodeAccelRiser object to use in the tests."""
        self.raw_data = get_riser_raw_data()
        self.node_accel_riser = NodeAccelRiser(self.raw_data)

    def test_init(self):
        """Test initialization of a NodeAccelRiser object."""
        self.assertEqual(self.raw_data, self.node_accel_riser.raw_data)
        self.assertIsNone(self.node_accel_riser.node)
        self.assertEqual(self.node_accel_riser.children_by_type, {})

    def test_producer(self):
        """Test the producer property."""
        self.assertEqual(self.node_accel_riser.producer, PRODUCER)

    def test_engineering_change_level(self):
        """Test the engineering_change_level property."""
        self.assertEqual(self.node_accel_riser.engineering_change_level, ENGINEERING_CHANGE_LEVEL)

    def test_pcb_serial_number(self):
        """Test the pcb_serial_number property."""
        self.assertEqual(self.node_accel_riser.pcb_serial_number, PCB_SERIAL_NUMBER)


if __name__ == '__main__':
    unittest.main()
