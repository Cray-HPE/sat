"""
Unit tests for sat.cli.status

(C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP.

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

from sat.cli.status.main import group_dicts_by
from sat.constants import MISSING_VALUE
from sat.xname import XName


# a fake table row, representing a fake node
# all default values are compliant with Shasta API response schemas
def row(**kwargs):
    status = dict(ID='x4242c0s99b0n0', Type='Node', NID=1, State='Ready', Flag='OK',
                  Enabled=True, Arch='Others', Role='Application', SubRole='UAN',
                  NetType='OEM')
    status.update(kwargs)

    return status


def sample_nodes():
    return [row(ID='z0'), row(ID='aa0', NID=42),
            row(ID='q0', NID=9), row(ID='ab0', NID=20)]


@unittest.skip('See CRAYSAT-1356.')
class TestStatusBase(unittest.TestCase):

    def test_empty(self):
        """make_raw_table() with an empty list of nodes

        make_raw_table() should return an empty table when the list of nodes
        is empty
        """
        raw_table = make_raw_table([], COMMON_API_KEYS_TO_HEADERS)
        self.assertEqual(raw_table, [])

    def test_one(self):
        """make_raw_table() with a single node

        make_raw_table() should return a table with a single row and the same
        number of columns as there are column headers
        """
        raw_table = make_raw_table([row()], NODE_API_KEYS_TO_HEADERS)
        self.assertEqual(len(raw_table), 1)
        self.assertEqual(len(raw_table[0]), len(NODE_API_KEYS_TO_HEADERS))

    def test_many_default(self):
        """make_raw_table() with many nodes, default sorting

        make_raw_table() should return a table with the same number of rows
        as nodes, each row should have the same number of columns as the
        column headers.
        """
        nodes = sample_nodes()
        raw_table = make_raw_table(deepcopy(nodes), NODE_API_KEYS_TO_HEADERS)
        self.assertEqual(len(raw_table), len(nodes))

        self.assertTrue(all(len(row) == len(NODE_API_KEYS_TO_HEADERS) for row in raw_table))

    def test_missing_xname(self):
        """Test that make_raw_table handles missing 'ID' key."""
        nodes = sample_nodes()
        key_to_delete = 'ID'
        deleted_index = list(NODE_API_KEYS_TO_HEADERS).index(key_to_delete)
        for node in nodes:
            del node[key_to_delete]

        raw_table = make_raw_table(deepcopy(nodes), NODE_API_KEYS_TO_HEADERS)
        self.assertTrue(all(row[deleted_index] == MISSING_VALUE
                            for row in raw_table))
        self.assertTrue(all(len(row) == len(NODE_API_KEYS_TO_HEADERS) for row in raw_table))

    def test_missing_flag_key(self):
        """Test that make_raw_table handles a different missing key."""
        nodes = sample_nodes()
        key_to_delete = 'Flag'
        deleted_index = list(NODE_API_KEYS_TO_HEADERS).index(key_to_delete)
        for node in nodes:
            del node[key_to_delete]

        raw_table = make_raw_table(deepcopy(nodes), NODE_API_KEYS_TO_HEADERS)
        self.assertTrue(all(row[deleted_index] == MISSING_VALUE
                            for row in raw_table))
        self.assertTrue(all(len(row) == len(NODE_API_KEYS_TO_HEADERS) for row in raw_table))

    def test_missing_subrole_key_from_compute_node(self):
        """Test that make_raw_table treats a compute node's missing subrole as 'None'."""
        nodes = [row(ID='ab', Role='Compute'), row(ID='cd', Role='Compute')]
        key_to_delete = 'SubRole'
        deleted_index = list(NODE_API_KEYS_TO_HEADERS).index(key_to_delete)
        for node in nodes:
            del node[key_to_delete]

        raw_table = make_raw_table(deepcopy(nodes), NODE_API_KEYS_TO_HEADERS)
        self.assertTrue(all(row[deleted_index] == 'None'
                            for row in raw_table))
        self.assertTrue(all(len(row) == len(NODE_API_KEYS_TO_HEADERS) for row in raw_table))

    def test_missing_subrole_key_from_application_node(self):
        """Test that make_raw_table treats an application node's missing subrole as MISSING."""
        nodes = sample_nodes()
        key_to_delete = 'SubRole'
        deleted_index = list(NODE_API_KEYS_TO_HEADERS).index(key_to_delete)
        for node in nodes:
            del node[key_to_delete]

        raw_table = make_raw_table(deepcopy(nodes), NODE_API_KEYS_TO_HEADERS)
        self.assertTrue(all(row[deleted_index] == MISSING_VALUE
                            for row in raw_table))
        self.assertTrue(all(len(row) == len(NODE_API_KEYS_TO_HEADERS) for row in raw_table))

    def test_xname_conversion(self):
        """Test that make_raw_table converts the xname."""
        single_node = row()
        nodes = [single_node]
        raw_table = make_raw_table(deepcopy(nodes), NODE_API_KEYS_TO_HEADERS)
        self.assertIsInstance(raw_table[0][0], XName)
        self.assertEqual(raw_table[0][0], XName(single_node['ID']))
        self.assertTrue(all(len(row) == len(NODE_API_KEYS_TO_HEADERS) for row in raw_table))


@unittest.skip('See CRAYSAT-1356.')
class TestGetComponentAliases(unittest.TestCase):
    """Tests for retrieving component aliases from SLS."""
    def setUp(self):
        self.sample_sls_response = [
            {
                "Parent": "x3000c0s17b1",
                "Xname": "x3000c0s17b1n0",
                "Type": "comptype_node",
                "Class": "River",
                "TypeString": "Node",
                "LastUpdated": 1620156675,
                "LastUpdatedTime": "2021-05-04 19:31:15.806794 +0000 +0000",
                "ExtraProperties": {
                    "Aliases": [
                        "nid000001"
                    ],
                    "NID": 1,
                    "Role": "Compute"
                }
            },
            {
                "Parent": "x3000c0s5b0",
                "Xname": "x3000c0s5b0n0",
                "Type": "comptype_node",
                "Class": "River",
                "TypeString": "Node",
                "LastUpdated": 1620156675,
                "LastUpdatedTime": "2021-05-04 19:31:15.806794 +0000 +0000",
                "ExtraProperties": {
                    "Aliases": [
                        "ncn-m003"
                    ],
                    "NID": 100003,
                    "Role": "Management",
                    "SubRole": "Master"
                }
            },
            {
                "Parent": "x3000c0w21",
                "Xname": "x3000c0w21j33",
                "Type": "comptype_mgmt_switch_connector",
                "Class": "River",
                "TypeString": "MgmtSwitchConnector",
                "LastUpdated": 1620156675,
                "LastUpdatedTime": "2021-05-04 19:31:15.806794 +0000 +0000",
                "ExtraProperties": {
                    "NodeNics": [
                        "x3000c0s17b2"
                    ],
                    "VendorName": "ethernet1/1/33"
                }
            }
        ]

    def test_get_component_aliases_returns_node_aliases(self):
        """Test the normal operation of get_component_aliases"""
        component_aliases = get_component_aliases(self.sample_sls_response)
        for xname in ['x3000c0s17b1n0', 'x3000c0s5b0n0']:
            with self.subTest(xname):
                self.assertIn(xname, component_aliases)

    def test_get_component_aliases_only_contains_nodes(self):
        """Test that components without aliases are not mapped to hostnames"""
        component_aliases = get_component_aliases(self.sample_sls_response)
        self.assertNotIn('x3000c0w21j33', component_aliases)

    def test_get_component_aliases_returns_correct_aliases(self):
        """Test that get_component_aliases returns the correct aliases for xnames"""
        correct_mapping = {
            'x3000c0s17b1n0': ['nid000001'],
            'x3000c0s5b0n0':  ['ncn-m003'],
        }
        self.assertEqual(get_component_aliases(self.sample_sls_response), correct_mapping)


class TestGroupDictsBy(unittest.TestCase):
    """Tests for grouping dicts by key."""
    def setUp(self):
        self.values = [
            {
                'name': 'Coca Cola',
                'type': 'soda'
            },
            {
                'name': 'Pepsi',
                'type': 'soda'
            },
            {
                'name': 'Monster',
                'type': 'energy'
            },
        ]
        self.group_by_attr = 'type'

    def test_grouping_values_have_same_type(self):
        """Test that grouped values all have the same value of the grouped attribute"""
        for attr_value, items in group_dicts_by(self.group_by_attr, self.values).items():
            for item in items:
                self.assertEqual(item[self.group_by_attr], attr_value)

    def test_all_values_grouped(self):
        """Test that no values are excluded after grouping"""
        grouped_items = set()
        for items in group_dicts_by(self.group_by_attr, self.values).values():
            grouped_items |= set(item['name'] for item in items)

        self.assertEqual(grouped_items, set(item['name'] for item in self.values))

    def test_valueerror_on_bad_attribute(self):
        """Test that ValueError is raised when grouped by a non-existent attribute"""
        with self.assertRaises(ValueError):
            group_dicts_by('bad_attribute', self.values)


if __name__ == '__main__':
    unittest.main()
