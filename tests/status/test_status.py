"""
Unit tests for sat.cli.status

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from copy import deepcopy

import unittest

import sat.cli.status.main
from sat.xname import XName


# a fake table row, representing a fake node
# all default values are compliant with Shasta API response schemas
def row(**kwargs):
    status = dict(ID='x4242c0s99b0n0', NID=1, State='Ready', Flag='OK',
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
        raw_table = sat.cli.status.main.make_raw_table([], {})
        self.assertEqual(raw_table, [])

    def test_one(self):
        """make_raw_table() with a single node

        make_raw_table() should return a table with a single row and the same
        number of columns as there are column headers
        """
        raw_table = sat.cli.status.main.make_raw_table([row()], {})
        self.assertEqual(len(raw_table), 1)
        self.assertEqual(len(raw_table[0]), len(sat.cli.status.main.HEADERS))

    def test_many_default(self):
        """make_raw_table() with many nodes, default sorting

        make_raw_table() should return a table with the same number of rows
        as nodes, each row should have the same number of columns as the
        column headers.
        """
        nodes = sample_nodes()
        raw_table = sat.cli.status.main.make_raw_table(deepcopy(nodes), {})
        self.assertEqual(len(raw_table), len(nodes))

        self.assertTrue(
            all(len(row) == len(sat.cli.status.main.HEADERS) for row in raw_table))

    def test_filter_no_match(self):
        """make_raw_table() filtered with no matches

        make_raw_table() should return an empty table.
        """
        raw_table = sat.cli.status.main.make_raw_table(
            sample_nodes(), dict(ID=frozenset([XName('q99')])))

        self.assertEqual(len(raw_table), 0)

    def test_filter_xname(self):
        """make_raw_table() filtered by a single xname

        make_raw_table() should return a table with a single row matching
        the xname filter.
        """
        raw_table = sat.cli.status.main.make_raw_table(
            sample_nodes(), dict(ID=frozenset([XName('q0')])))

        self.assertEqual(len(raw_table), 1)
        self.assertEqual(raw_table[0][0], 'q0')

    def test_filter_xnames(self):
        """make_raw_table() filtered by multiple xnames

        make_raw_table() should return a table with rows matching the xname
        filter.
        """
        raw_table = sat.cli.status.main.make_raw_table(
            sample_nodes(),
            dict(ID=frozenset([XName('q0'), XName('aa0')])))

        self.assertEqual(len(raw_table), 2)

        self.assertEqual(
            frozenset(tuple(zip(*raw_table))[0]), frozenset(['aa0', 'q0']))

    def test_filter_nid(self):
        """make_raw_table() filtered by a single nid

        make_raw_table() should return a table with a single row matching
        the nid filter.
        """
        raw_table = sat.cli.status.main.make_raw_table(
            sample_nodes(), dict(NID=frozenset(['42'])))

        self.assertEqual(len(raw_table), 1)
        self.assertEqual(raw_table[0][1], 42)

    def test_filter_nids(self):
        """make_raw_table() filtered by multiple nids

        make_raw_table() should return a table with rows matching the nid
        filter.
        """

        raw_table = sat.cli.status.main.make_raw_table(
            sample_nodes(), dict(NID=frozenset(['42', '1'])))

        self.assertEqual(len(raw_table), 2)

        self.assertEqual(
            frozenset(tuple(zip(*raw_table))[1]), frozenset([1, 42]))

    def test_filter_both(self):
        """make_raw_table() filtered by xname and nid

        make_raw_table() should return a table with a rows matching the xname
        and nid filters.
        """

        raw_table = sat.cli.status.main.make_raw_table(
            sample_nodes(),
            dict(ID=frozenset([XName('z0'), XName('aa0')]), NID=frozenset(['9', '42'])))

        self.assertEqual(len(raw_table), 3)

        self.assertEqual(
            frozenset(tuple(zip(*raw_table))[1]), frozenset([9, 42, 1]))


if __name__ == '__main__':
    unittest.main()
