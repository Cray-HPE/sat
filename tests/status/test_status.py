"""
Unit tests for sat.status

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import unittest
from unittest import mock


import sat.status.main


# substitute for the parsed json API response
class FakeResponse:
    def __init__(self, rsp):
        self._rsp = dict(Components=rsp)

    def json(self):
        return self._rsp


# a fake table row, representing a fake node
# all default values are compliant with Shasta API response schemas
def row(**kwargs):
    status = dict(ID='x4242c0s99b0n0', NID=1, State='Ready', Flag='OK',
                  Enabled=True, Arch='Others', Role='Application', NetType='OEM')
    status.update(kwargs)

    return status


def sample_nodes():
    return (row(ID='z0'), row(ID='aa0', NID=42),
            row(ID='q0', NID=9), row(ID='ab0', NID=20))


def sample_nodes_sorted(sort_key='ID', reverse=False):
    return sorted(sample_nodes(), key=lambda x: x[sort_key], reverse=reverse)


# for testing parse_sortcol(), make_raw_table() tests use the "standard" headers
TEST_HDRS = ('abc', 'bcd', 'bde', 'xyz')


class TestStatusBase(unittest.TestCase):
    @mock.patch('sat.status.main.api_query', return_value=FakeResponse([]))
    def test_empty(self, _):
        """make_raw_table() with an empty list of nodes

        make_raw_table() should return an empty table when the list of nodes
        is empty
        """

        raw_table = sat.status.main.make_raw_table(0, False, {})
        self.assertEqual(raw_table, [])

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse([row()]))
    def test_one(self, _):
        """make_raw_table() with a single node

        make_raw_table() should return a table with a single row and the same
        number of columns as there are column headers
        """

        raw_table = sat.status.main.make_raw_table(0, False, {})
        self.assertEqual(len(raw_table), 1)
        self.assertEqual(len(raw_table[0]), len(sat.status.main.HEADERS))

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_many_default(self, _):
        """make_raw_table() with many nodes, default sorting

        make_raw_table() should return a table with the same number of rows as
        nodes, each row should have the same number of columns as the column
        headers, and sorted according to the first column, ascending order.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(0, False, {})

        self.assertEqual(len(raw_table), len(nodes))

        self.assertTrue(
            all((len(row) == len(sat.status.main.HEADERS) for row in raw_table)))

        self.assertEqual(tuple(zip(*raw_table))[0], tuple(
            [row['ID'] for row in sample_nodes_sorted()]))

        for node, row in zip(sample_nodes_sorted(), raw_table):
            for i, key in enumerate(sat.status.main.APIKEYS):
                self.assertEqual(node[key], row[i])

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_many_reverse(self, _):
        """make_raw_table() with many nodes, default sort column, reversed

        make_raw_table() should return a table with the same number of rows as
        nodes, each row should have the same number of columns as the column
        headers, and sorted according to the first column, descending order.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(0, True, {})

        self.assertEqual(len(raw_table), len(nodes))

        self.assertTrue(
            all((len(row) == len(sat.status.main.HEADERS) for row in raw_table)))

        self.assertEqual(tuple(zip(*raw_table))[0], tuple(
            [row['ID'] for row in sample_nodes_sorted(reverse=True)]))

        for node, row in zip(sample_nodes_sorted(reverse=True), raw_table):
            for i, key in enumerate(sat.status.main.APIKEYS):
                self.assertEqual(node[key], row[i])

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_many_sort_other(self, _):
        """make_raw_table() with many nodes, sort by NID

        make_raw_table() should return a table with the same number of rows as
        nodes, each row should have the same number of columns as the column
        headers, and sorted according to the second column, ascending order.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(1, False, {})

        self.assertEqual(len(raw_table), len(nodes))

        self.assertTrue(
            all((len(row) == len(sat.status.main.HEADERS) for row in raw_table)))

        self.assertEqual(tuple(zip(*raw_table))[1], tuple(
            [row['NID'] for row in sample_nodes_sorted(sort_key='NID')]))

        for node, row in zip(sample_nodes_sorted(sort_key='NID'), raw_table):
            for i, key in enumerate(sat.status.main.APIKEYS):
                self.assertEqual(node[key], row[i])

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_filter_no_match(self, _):
        """make_raw_table() filtered with no matches

        make_raw_table() should return an empty table.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(
            0, False, dict(ID=frozenset([('q', 99)])))

        self.assertEqual(len(raw_table), 0)

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_filter_xname(self, _):
        """make_raw_table() filtered by a single xname

        make_raw_table() should return a table with a single row matching the xname
        filter.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(
            0, False, dict(ID=frozenset([('q', 0)])))

        self.assertEqual(len(raw_table), 1)
        self.assertEqual(raw_table[0][0], 'q0')

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_filter_xnames(self, _):
        """make_raw_table() filtered by multiple xnames

        make_raw_table() should return a table with rows matching the xname
        filter.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(
            0, False, dict(ID=frozenset([('q', 0), ('aa', 0)])))

        self.assertEqual(len(raw_table), 2)

        self.assertEqual(
            frozenset(tuple(zip(*raw_table))[0]), frozenset(['aa0', 'q0']))

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_filter_nid(self, _):
        """make_raw_table() filtered by a single nid

        make_raw_table() should return a table with a single row matching the nid
        filter.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(
            0, False, dict(NID=frozenset(['42'])))

        self.assertEqual(len(raw_table), 1)
        self.assertEqual(raw_table[0][1], 42)

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_filter_nids(self, _):
        """make_raw_table() filtered by multiple nids

        make_raw_table() should return a table with rows matching the nid
        filter.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(
            0, False, dict(NID=frozenset(['42', '1'])))

        self.assertEqual(len(raw_table), 2)

        self.assertEqual(
            frozenset(tuple(zip(*raw_table))[1]), frozenset([1, 42]))

    @mock.patch('sat.status.main.api_query', return_value=FakeResponse(sample_nodes()))
    def test_filter_both(self, _):
        """make_raw_table() filtered by xname and nid

        make_raw_table() should return a table with a rows matching the xname
        and nid filters.
        """

        nodes = sample_nodes()
        raw_table = sat.status.main.make_raw_table(1, False, dict(
            ID=frozenset([('z', 0), ('aa', 0)]), NID=frozenset(['9', '42'])))

        self.assertEqual(len(raw_table), 3)

        self.assertEqual(
            frozenset(tuple(zip(*raw_table))[1]), frozenset([9, 42, 1]))

    def test_parse_sortcol_null(self):
        """parse_sortcol() should return 0 when passed an empty string
        """

        self.assertEqual(sat.status.main.parse_sortcol('', TEST_HDRS), 0)

    def test_parse_sortcol_int_ok(self):
        """parse_sortcol() with valid int-as-str arguments

        parse_sortcol() should return i-1 when passed the string representation
        of an integer, and that integer is within the range of 1 to the table
        width.
        """

        parse_sortcol = sat.status.main.parse_sortcol
        n = len(TEST_HDRS)

        self.assertEqual(parse_sortcol('1', TEST_HDRS), 0)
        self.assertEqual(parse_sortcol(str(n), TEST_HDRS), n-1)

    def test_parse_sortcol_int_bad(self):
        """parse_sortcol() with invalid int-as-str arguments

        parse_sortcol() raise UsageError when passed the string representation
        of an integer, and that integer is outside the range of 1 to the table
        width.
        """

        parse_sortcol = sat.status.main.parse_sortcol
        UsageError = sat.status.main.UsageError
        n = len(TEST_HDRS)

        with self.assertRaises(UsageError):
            parse_sortcol('0', TEST_HDRS)

        with self.assertRaises(UsageError):
            parse_sortcol(str(n+1), TEST_HDRS)

    def test_parse_sortcol_full(self):
        """parse_sortcol() with full-length, mixed-case column headers

        parse_sortcol() should return the zero-based index of a column header
        when passed a possibly mixed-case match for the full column header.
        """

        parse_sortcol = sat.status.main.parse_sortcol
        i = TEST_HDRS.index('bcd')

        self.assertEqual(parse_sortcol('bcd', TEST_HDRS), i)
        self.assertEqual(parse_sortcol('bCd', TEST_HDRS), i)
        self.assertEqual(parse_sortcol('BcD', TEST_HDRS), i)
        self.assertEqual(parse_sortcol('BCD', TEST_HDRS), i)

    def test_parse_sortcol_too_full(self):
        """parse_sortcol() fails if a column header with extra characters is passed

        parse_sortcol() should raise UsageError if there are remaining
        characters after a header is matched.
        """

        with self.assertRaises(sat.status.main.UsageError):
            sat.status.main.parse_sortcol('abcd', TEST_HDRS)

    def test_parse_sortcol_match_single(self):
        """parse_sortcol() match single character

        parse_sortcol() should return the index of the first matching column
        header when passed the first character of that header, regardless of
        case.
        """

        parse_sortcol = sat.status.main.parse_sortcol
        i = TEST_HDRS.index('bcd')

        self.assertEqual(parse_sortcol('b', TEST_HDRS), i)
        self.assertEqual(parse_sortcol('B', TEST_HDRS), i)

    def test_parse_sortcol_mismatch_single(self):
        """parse_sortcol() mismatch single character

        parse_sortcol() should raise UsageError when passed a minimal non-
        matching argument.
        """

        with self.assertRaises(sat.status.main.UsageError):
            sat.status.main.parse_sortcol('z', TEST_HDRS)

    def test_parse_sortcol_match_abbrev(self):
        """parse_sortcol() match an abbreviation

        parse_sortcol() should return the index of the first matching column
        header when passed an abbreviation of that header, regardless of case.
        """

        parse_sortcol = sat.status.main.parse_sortcol
        # this header requires two characters to match
        i = TEST_HDRS.index('bde')

        self.assertEqual(parse_sortcol('bd', TEST_HDRS), i)
        self.assertEqual(parse_sortcol('bD', TEST_HDRS), i)
        self.assertEqual(parse_sortcol('Bd', TEST_HDRS), i)
        self.assertEqual(parse_sortcol('BD', TEST_HDRS), i)

    def test_parse_sortcol_mismatch_abbrev(self):
        """parse_sortcol() mismatch single character

        parse_sortcol() should raise UsageError when passed a nonmatching
        abbreviation.
        """

        with self.assertRaises(sat.status.main.UsageError):
            sat.status.main.parse_sortcol('bz', TEST_HDRS)

    def test_xname_empty(self):
        """xname_tokenize() with empty input should return an empty tuple
        """
        self.assertEqual(sat.status.main.tokenize_xname(''), ())

    def test_xname_single(self):
        """xname_tokenize() with a single str/int pair
        """
        self.assertEqual(sat.status.main.tokenize_xname('x42'), ('x', 42))
        self.assertEqual(sat.status.main.tokenize_xname('x4'), ('x', 4))

    def test_xname_several(self):
        """xname_tokenize() with a normal, Shasta-compliant node xname.
        """
        self.assertEqual(sat.status.main.tokenize_xname('x3000c0s11b1n0'),
                         ('x', 3000, 'c', 0, 's', 11, 'b', 1, 'n', 0))

    def test_xname_several_zeros(self):
        """xname_tokenize() with a normal, Shasta-compliant node xname, with
        leading zeros in some integer parts
        """
        self.assertEqual(sat.status.main.tokenize_xname('x3000c00s11b01n0'),
                         ('x', 3000, 'c', 0, 's', 11, 'b', 1, 'n', 0))

    def test_xname_several_case(self):
        """xname_tokenize() should return lowercase for all string tokens
        """
        self.assertEqual(sat.status.main.tokenize_xname('x3000C00s11B01n0'),
                         ('x', 3000, 'c', 0, 's', 11, 'b', 1, 'n', 0))


if __name__ == '__main__':
    unittest.main()
