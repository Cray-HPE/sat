"""
Unit tests for sat.system.node_hsn_nic.

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

from sat.system.node_hsn_nic import NodeHsnNic
from tests.system.component_data import NODE_HSN_NIC_XNAME, get_component_raw_data


class TestNodeHsnNic(unittest.TestCase):
    """Test the NodeHsnNic class."""

    def test_init(self):
        raw_data = get_component_raw_data(hsm_type='NodeHsnNic', xname=NODE_HSN_NIC_XNAME)
        node_hsn_nic = NodeHsnNic(raw_data)
        self.assertEqual(raw_data, node_hsn_nic.raw_data)
        self.assertEqual(node_hsn_nic.children_by_type, {})


if __name__ == '__main__':
    unittest.main()
