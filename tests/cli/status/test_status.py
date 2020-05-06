"""
Unit tests for sat.cli.status

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
from copy import deepcopy

import unittest

from sat.cli.status.main import API_KEYS, HEADERS, make_raw_table
from sat.constants import MISSING_VALUE
from sat.xname import XName


# a fake table row, representing a fake node
# all default values are compliant with Shasta API response schemas
def row(**kwargs):
    status = dict(ID='x4242c0s99b0n0', Type='Node', NID=1, State='Ready', Flag='OK',
                  Enabled=True, Arch='Others', Role='Application', NetType='OEM')
    status.update(kwargs)

    return status


def sample_nodes():
    return [row(ID='z0'), row(ID='aa0', NID=42),
            row(ID='q0', NID=9), row(ID='ab0', NID=20)]


class TestStatusBase(unittest.TestCase):

    def test_empty(self):
        """make_raw_table() with an empty list of nodes

        make_raw_table() should return an empty table when the list of nodes
        is empty
        """
        raw_table = make_raw_table([])
        self.assertEqual(raw_table, [])

    def test_one(self):
        """make_raw_table() with a single node

        make_raw_table() should return a table with a single row and the same
        number of columns as there are column headers
        """
        raw_table = make_raw_table([row()])
        self.assertEqual(len(raw_table), 1)
        self.assertEqual(len(raw_table[0]), len(HEADERS))

    def test_many_default(self):
        """make_raw_table() with many nodes, default sorting

        make_raw_table() should return a table with the same number of rows
        as nodes, each row should have the same number of columns as the
        column headers.
        """
        nodes = sample_nodes()
        raw_table = make_raw_table(deepcopy(nodes))
        self.assertEqual(len(raw_table), len(nodes))

        self.assertTrue(all(len(row) == len(HEADERS) for row in raw_table))

    def test_missing_xname(self):
        """Test that make_raw_table handles missing 'ID' key."""
        nodes = sample_nodes()
        key_to_delete = 'ID'
        deleted_index = API_KEYS.index(key_to_delete)
        for node in nodes:
            del node[key_to_delete]

        raw_table = make_raw_table(deepcopy(nodes))
        self.assertTrue(all(row[deleted_index] == MISSING_VALUE
                            for row in raw_table))
        self.assertTrue(all(len(row) == len(HEADERS) for row in raw_table))

    def test_missing_key(self):
        """Test that make_raw_table handles other missing key."""
        nodes = sample_nodes()
        key_to_delete = 'Flag'
        deleted_index = API_KEYS.index(key_to_delete)
        for node in nodes:
            del node[key_to_delete]

        raw_table = make_raw_table(deepcopy(nodes))
        self.assertTrue(all(row[deleted_index] == MISSING_VALUE
                            for row in raw_table))
        self.assertTrue(all(len(row) == len(HEADERS) for row in raw_table))

    def test_xname_conversion(self):
        """Test that make_raw_table converts the xname."""
        single_node = row()
        nodes = [single_node]
        raw_table = make_raw_table(deepcopy(nodes))
        self.assertIsInstance(raw_table[0][0], XName)
        self.assertEqual(raw_table[0][0], XName(single_node['ID']))
        self.assertTrue(all(len(row) == len(HEADERS) for row in raw_table))


if __name__ == '__main__':
    unittest.main()
