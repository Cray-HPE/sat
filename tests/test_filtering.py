"""
Tests for output filtering mechanisms.

Copyright 2019-2020 Cray Inc. All Rights Reserved.
"""

from functools import wraps
import itertools
from unittest import mock
import unittest

from sat import filtering


def with_filter(query_string):
    """Decorator which passes a compiled query to a test case.

    Args:
       query_string: a query string which is to be compiled into a
           filter function.
    """
    filter_fn = filtering.parse_query_string(query_string)

    def decorator(fn):
        @wraps(fn)
        def caller(*args, **kwargs):
            passed_args = list(args)
            passed_args.insert(1, filter_fn)
            fn(*passed_args, **kwargs)
        return caller
    return decorator


class TestSubsequenceMatching(unittest.TestCase):
    """Tests for helper functions for filtering and matching."""
    def test_is_subsequence(self):
        """Test subsequence matching."""
        test_str = 'spamneggs'
        for l in range(len(test_str) + 1):
            for subseq in itertools.combinations(test_str, l):
                self.assertTrue(filtering.is_subsequence(''.join(subseq), test_str))

    def test_trivial_subsequence(self):
        """Test empty string is a subsequence."""
        self.assertTrue(filtering.is_subsequence('', 'foo'))

    def test_subseq_of_empty(self):
        """Test subsequences of the empty string."""
        self.assertFalse(filtering.is_subsequence('foo', ''))
        self.assertTrue(filtering.is_subsequence('', ''))

    def test_is_not_subsequence(self):
        """Test subsequence misses."""
        haystack = 'foobarbaz'
        for needle in ['zabraboof', 'nothing', 'ofoarbazb',
                       'foobarbax', 'bff', 'egads']:
            self.assertFalse(filtering.is_subsequence(needle, haystack))

    def test_combine_filter_fns(self):
        """Test composing filtering functions with boolean combinators."""
        always_true = mock.MagicMock(return_value=True)
        always_false = mock.MagicMock(return_value=False)
        fns = (always_true, always_false)
        true_fns = (always_true, always_true)
        false_fns = (always_false, always_false)
        val = mock.MagicMock()

        self.assertFalse(filtering.combine_filter_fns(fns)(val))
        self.assertTrue(filtering.combine_filter_fns(true_fns)(val))
        self.assertFalse(filtering.combine_filter_fns(false_fns)(val))
        self.assertTrue(filtering.combine_filter_fns(fns, combine_fn=any)(val))
        self.assertTrue(filtering.combine_filter_fns(true_fns, combine_fn=any)(val))
        self.assertFalse(filtering.combine_filter_fns(false_fns, combine_fn=any)(val))

    def test_get_cmpr_fn_value_error(self):
        """Test _get_cmpr_fn raises a ValueError for a non-comparator."""
        with self.assertRaises(ValueError):
            filtering._get_cmpr_fn('not a comparator')


class TestFilterQueryStrings(unittest.TestCase):
    """Tests for ensuring query strings mark matches as expected."""

    @with_filter('foo = bar')
    def test_simple_query(self, filter_fn):
        """Test a simple equality query."""
        self.assertTrue(filter_fn({'foo': 'bar'}))

    @with_filter('foo = b*')
    def test_query_with_wildcard(self, filter_fn):
        """Test a query with a wildcard."""
        for b in ['bar', 'b', 'baz', 'bxx', 'boooooo']:
            self.assertTrue(filter_fn({'foo': b}))

        self.assertFalse(filter_fn({'foo': 'nothing'}))

    @with_filter('mem_cap = 192')
    def test_query_subseq_key(self, filter_fn):
        """Test querying against key subsequencing."""
        self.assertTrue(filter_fn({'memory_capacity': 192}))

    def test_query_numerical_value(self):
        """Test querying against a numerical value."""
        capacities = [2 ** x for x in range(8, 15)]  # 256 through 16384
        for comp_char in ['<', '<=']:
            filter_fn = filtering.parse_query_string('memory {} 192'.format(comp_char))
            for cap in capacities:
                self.assertFalse(filter_fn({'memory': cap}))

        for comp_char in ['>', '>=']:
            filter_fn = filtering.parse_query_string('memory {} 192'.format(comp_char))
            for cap in capacities:
                self.assertTrue(filter_fn({'memory': cap}))

    def test_bad_query_string(self):
        """Test giving a bad query string will throw ParseError."""
        for bad_query in ['foo =', 'foo = bar or', 'and', 'foo <> bar']:
            with self.assertRaises(filtering.ParseError):
                filtering.parse_query_string(bad_query)

    @with_filter('foo = bar')
    def test_missing_key(self, filter_fn):
        """Test KeyError thrown when filtering non-existent key."""
        with self.assertRaises(KeyError):
            filter_fn({'baz': 'quux'})

    @with_filter('foo = bar')
    def test_ambiguous_key(self, filter_fn):
        """Test KeyError thrown when filtering ambiguous key."""
        with self.assertRaises(KeyError):
            # 'foo' is a subsequence of both 'food' and 'frobnicator'.
            filter_fn({'food': 'spam', 'frobnicator': 'quuxify'})

    @with_filter('foo > 20')
    def test_cant_compare_numbers_and_strings(self, filter_fn):
        """Test comparing numbers and strings will give an error."""
        with self.assertRaises(TypeError):
            filter_fn({'foo': 'bar'})

    @with_filter('foo = 20')
    def test_equality_with_numbers_and_strings(self, filter_fn):
        """Test comparing equality between numbers and strings works."""
        self.assertTrue(filter_fn({'foo': 20}))
        self.assertFalse(filter_fn({'foo': 'bar'}))

    @with_filter('foo = bar and baz = quu*')
    def test_boolean_expression(self, filter_fn):
        self.assertTrue(filter_fn({'foo': 'bar', 'baz': 'quux'}))

    @with_filter('sernum = 2020*')
    def test_numerical_prefix_wildcard(self, filter_fn):
        self.assertTrue(filter_fn({'name': 'roy batty', 'serial_number': '2020m'}))
        self.assertTrue(filter_fn({'name': 'irmgard batty', 'serial_number': '2020f'}))

    @with_filter('sernum = "1999"')
    def test_numerical_string_equality(self, filter_fn):
        self.assertTrue(filter_fn({'name': 'prince rogers', 'serial_number': '1999'}))
        self.assertFalse(filter_fn({'name': 'rush', 'serial_number': '2112'}))

    @with_filter('fruit = "apple" and baskets = "2" or flower = "rose" and vases = "3"')
    def test_boolean_precedence(self, filter_fn):
        self.assertTrue(filter_fn({'fruit': 'apple', 'baskets': '2',
                                   'flower': 'petunia', 'vases': '1'}))
        self.assertTrue(filter_fn({'fruit': 'orange', 'baskets': '1',
                                   'flower': 'rose', 'vases': '3'}))
        self.assertFalse(filter_fn({'fruit': 'apple', 'baskets': '1',
                                    'flower': 'rose', 'vases': '2'}))


class TestFilterList(unittest.TestCase):
    """Tests for filtering lists of dicts."""
    def setUp(self):
        self.query_strings = ['foo=bar']

    def test_filter_list(self):
        """Test basic list filtering."""
        items = [{'foo': 'bar'}, {'foo': 'baz'}, {'foo': 'quux'}]
        first, rest = items[0], items[1:]
        filtered = filtering.filter_list(items, self.query_strings)
        self.assertIn(first, filtered)
        self.assertTrue(all(item not in filtered for item in rest))

    def test_filtering_empty_list(self):
        """Test filtering an empty list."""
        self.assertEqual(filtering.filter_list([], self.query_strings),
                         [])

    def test_filtering_with_no_filters(self):
        """Test filtering against an empty set of filters."""
        items = [{'name': 'garfield'}, {'name': 'odie'},
                 {'name': 'jon arbuckle'}]
        self.assertEqual(filtering.filter_list(items, []),
                         items)

    def test_invalid_input_list(self):
        """Test filtering a list with inconsistent headings (i.e. keys)."""
        with self.assertRaises(ValueError):
            filtering.filter_list([{'foo': 'bar'}, {'baz': 'quux'}],
                                  self.query_strings)

    def test_mixed_values(self):
        """Nonsensical comparisons should be omitted."""
        items = [
            {'speed': 'Not found'},
            {'speed': None},
            {'speed': 10},
            {'speed': 11},
            {'speed': 12},
        ]

        filtered = filtering.filter_list(items, ['speed<12'])
        self.assertEqual(2, len(filtered))
        self.assertEqual({'speed': 10}, filtered[0])
        self.assertEqual({'speed': 11}, filtered[1])
