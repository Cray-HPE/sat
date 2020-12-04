"""
Unit tests for sat.system.node_enclosure_power_supply.

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

from sat.system.node_enclosure_power_supply import NodeEnclosurePowerSupply
from tests.system.component_data import NODE_ENCLOSURE_POWER_SUPPLY_XNAME, get_component_raw_data


class TestNodeEnclosurePowerSupply(unittest.TestCase):
    """Test the NodeEnclosurePowerSupply class."""

    def test_init(self):
        raw_data = get_component_raw_data(hsm_type='NodeEnclosurePowerSupply', xname=NODE_ENCLOSURE_POWER_SUPPLY_XNAME)
        node_enclosure_power_supply = NodeEnclosurePowerSupply(raw_data)
        self.assertEqual(raw_data, node_enclosure_power_supply.raw_data)
        self.assertEqual(node_enclosure_power_supply.children_by_type, {})


if __name__ == '__main__':
    unittest.main()
