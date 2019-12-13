"""
Unit tests for the sat.sat.cli.linkhealth.main functions.

Copyright 2019 Cray Inc. All Rights Reserved.
"""


import os
import unittest
from unittest import mock

import sat.cli.linkhealth.main


class TestLinkhealth(unittest.TestCase):

    def test_get_matches_exact(self):
        """Basic positive test case for get_matches.
        """
        filters = ['hello', 'not here']
        elems = ['hello', 'there']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual({'hello'}, used)
        self.assertEqual({'not here'}, unused)
        self.assertEqual({'hello'}, matches)
        self.assertEqual({'there'}, no_matches)

    def test_get_matches_sub(self):
        """Elements should match if they contain a filter.
        """
        filters = ['hello']
        elems = ['hellosers']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual({'hello'}, used)
        self.assertEqual(set(), unused)
        self.assertEqual({'hellosers'}, matches)
        self.assertEqual(set(), no_matches)

    def test_get_matches_empty_filters(self):
        """It should return empty matches if no filters present.
        """
        filters = []
        elems = ['hello', 'there']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual(set(), used)
        self.assertEqual(set(), unused)
        self.assertEqual(set(), matches)
        self.assertEqual(set(elems), no_matches)

    def test_get_matches_empty_elems(self):
        """It should not fail if provided empty elems.
        """
        filters = ['hello']
        elems = []
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual(set(), used)
        self.assertEqual(set(filters), unused)
        self.assertEqual(set(), matches)
        self.assertEqual(set(), no_matches)

    def test_get_matches_unique_answers(self):
        """The returned values should only contain unique entries.
        """
        filters = ['hello', 'hello', 'there', 'there', 'unused', 'unused']
        elems = ['hello', 'hello']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)

        self.assertEqual(1, len(used))
        self.assertEqual(2, len(unused))
        self.assertEqual(1, len(matches))
        self.assertEqual(0, len(no_matches))


if __name__ == '__main__':
    unittest.main()
