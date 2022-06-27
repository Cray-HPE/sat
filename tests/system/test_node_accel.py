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
Unit tests for sat.system.node_accel.
"""
import unittest

from sat.system.node_accel import NodeAccel
from tests.system.component_data import NODE_ACCEL_XNAME, get_component_raw_data

LOCATION_NAME = 'NVIDIA HGX-3'


def get_node_accel_raw_data(xname=NODE_ACCEL_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='NodeAccel', xname=xname, **kwargs)
    extra_location_info = {
        'Name': LOCATION_NAME,
    }
    component_data['NodeAccelLocationInfo'].update(extra_location_info)
    return component_data


class TestNodeAccel(unittest.TestCase):
    """Test the NodeAccel class."""

    def setUp(self):
        """Create a NodeAccel object to use in the tests."""
        self.raw_data = get_node_accel_raw_data()
        self.node_accel = NodeAccel(self.raw_data)

    def test_init(self):
        self.assertEqual(self.raw_data, self.node_accel.raw_data)
        self.assertEqual(self.node_accel.children_by_type, {})

    def test_location_name(self):
        """Test the location_name property."""
        self.assertEqual(self.node_accel.location_name, LOCATION_NAME)


if __name__ == '__main__':
    unittest.main()
