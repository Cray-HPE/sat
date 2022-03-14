"""
Tests for output filtering mechanisms.

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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

from collections import OrderedDict
import copy
from functools import wraps
import os
import random
import time
from unittest import mock
import unittest

from parsec import ParseError

from sat import filtering


def with_filter(query_string, fields):
    """Decorator which passes a compiled query to a test case.

    Args:
       query_string: a query string which is to be compiled into a
           filter function.
    """
    filter_fn = filtering.parse_query_string(query_string, fields)

    def decorator(fn):
        @wraps(fn)
        def caller(*args, **kwargs):
            passed_args = list(args)
            passed_args.insert(1, filter_fn)
            fn(*passed_args, **kwargs)
        return caller
    return decorator


class TestFilterQueryStrings(unittest.TestCase):
    """Tests for ensuring query strings mark matches as expected."""

    @with_filter('foo = bar', ['foo'])
    def test_simple_query(self, filter_fn):
        """Test a simple equality query."""
        self.assertTrue(filter_fn({'foo': 'bar'}))

    @with_filter('foo = b*', ['foo'])
    def test_query_with_wildcard(self, filter_fn):
        """Test a query with a wildcard."""
        for b in ['bar', 'b', 'baz', 'bxx', 'boooooo']:
            self.assertTrue(filter_fn({'foo': b}))

        self.assertFalse(filter_fn({'foo': 'nothing'}))

    @with_filter('mem_cap = 192', ['memory_capacity'])
    def test_query_subseq_key(self, filter_fn):
        """Test querying against key subsequencing."""
        self.assertTrue(filter_fn({'memory_capacity': 192}))

    def test_query_numerical_value(self):
        """Test querying against a numerical value."""
        capacities = [2 ** x for x in range(8, 15)]  # 256 through 16384
        for comp_char in ['<', '<=']:
            filter_fn = filtering.parse_query_string('memory {} 192'.format(comp_char), ['memory'])
            for cap in capacities:
                self.assertFalse(filter_fn({'memory': cap}))

        for comp_char in ['>', '>=']:
            filter_fn = filtering.parse_query_string('memory {} 192'.format(comp_char), ['memory'])
            for cap in capacities:
                self.assertTrue(filter_fn({'memory': cap}))

    def test_bad_query_string(self):
        """Test giving a bad query string will throw ParseError."""
        for bad_query in ['foo =', 'foo = bar or', 'and', 'foo <> bar']:
            with self.assertRaises(ParseError):
                filtering.parse_query_string(bad_query, ['foo'])

    def test_missing_key(self):
        """Test KeyError thrown when filtering non-existent key."""
        filter_fn = filtering.parse_query_string('foo=bar', ['baz'])
        with self.assertRaises(KeyError):
            filter_fn({'baz': 'quux'})

    @with_filter('foo = spam', ['food', 'frobnicator'])
    def test_ambiguous_key(self, filter_fn):
        """Test first column match when filtering ambiguous key."""
        # 'foo' is a subsequence of both 'food' and 'frobnicator'.
        self.assertTrue(filter_fn({'food': 'spam', 'frobnicator': 'quuxify'}))

    @with_filter('foo > 20', ['foo'])
    def test_cant_compare_numbers_and_strings(self, filter_fn):
        """Test comparing numbers and strings will give an error."""
        with self.assertRaises(TypeError):
            filter_fn({'foo': 'bar'})

    @with_filter('foo = 20', ['foo'])
    def test_equality_with_numbers_and_strings(self, filter_fn):
        """Test comparing equality between numbers and strings works."""
        self.assertTrue(filter_fn({'foo': 20}))
        self.assertFalse(filter_fn({'foo': 'bar'}))

    @with_filter('foo = bar and baz = quu*', ['foo', 'baz'])
    def test_boolean_expression(self, filter_fn):
        self.assertTrue(filter_fn({'foo': 'bar', 'baz': 'quux'}))

    @with_filter('sernum = 2020*', ['name', 'serial_number'])
    def test_numerical_prefix_wildcard(self, filter_fn):
        self.assertTrue(filter_fn({'name': 'roy batty', 'serial_number': '2020m'}))
        self.assertTrue(filter_fn({'name': 'irmgard batty', 'serial_number': '2020f'}))

    @with_filter('sernum = "1999"', ['name', 'serial_number'])
    def test_numerical_string_equality(self, filter_fn):
        self.assertTrue(filter_fn({'name': 'prince rogers', 'serial_number': '1999'}))
        self.assertFalse(filter_fn({'name': 'rush', 'serial_number': '2112'}))

    @with_filter('fruit = "apple" and baskets = "2" or flower = "rose" and vases = "3"',
                 ['fruit', 'baskets', 'flower', 'vases'])
    def test_boolean_precedence(self, filter_fn):
        self.assertTrue(filter_fn({'fruit': 'apple', 'baskets': '2',
                                   'flower': 'petunia', 'vases': '1'}))
        self.assertTrue(filter_fn({'fruit': 'orange', 'baskets': '1',
                                   'flower': 'rose', 'vases': '3'}))
        self.assertFalse(filter_fn({'fruit': 'apple', 'baskets': '1',
                                    'flower': 'rose', 'vases': '2'}))

    def test_combined_filters(self):
        """Test composing filtering functions with boolean combinators."""
        always_true = filtering.CustomFilter(mock.MagicMock(return_value=True), {'some_field'})
        always_false = filtering.CustomFilter(mock.MagicMock(return_value=False), {'some_field'})

        fns = (always_true, always_false)
        true_fns = (always_true, always_true)
        false_fns = (always_false, always_false)
        val = mock.MagicMock()

        self.assertFalse(filtering.CombinedFilter(all, *fns)(val))
        self.assertTrue(filtering.CombinedFilter(all, *true_fns)(val))
        self.assertFalse(filtering.CombinedFilter(all, *false_fns)(val))

        self.assertTrue(filtering.CombinedFilter(any, *fns)(val))
        self.assertTrue(filtering.CombinedFilter(any, *true_fns)(val))
        self.assertFalse(filtering.CombinedFilter(any, *false_fns)(val))

    def test_custom_filters(self):
        """Test that custom filters filter rows according to their given filter function."""
        filter_result_cache = {}

        # A filter function that randomly filters the given row, and saves the
        # result of the filtering.
        def filter_fn(row):
            if row['num'] not in filter_result_cache:
                filter_result_cache[row['num']] = bool(random.randint(0, 1))
            return filter_result_cache[row['num']]

        custom_filter = filtering.CustomFilter(filter_fn, {'num'})
        for row in [{'num': i} for i in range(20)]:
            self.assertEqual(filter_fn(row), custom_filter(row))

    def test_get_cmpr_fn_value_error(self):
        """Test _get_cmpr_fn raises a ValueError for a non-comparator."""
        with self.assertRaises(ValueError):
            filtering._get_cmpr_fn('not a comparator')


class TestGetFilteredFields(unittest.TestCase):
    def test_get_filtered_fields_single_value(self):
        """Test FilterFunction.get_filtered_fields() with a single field."""
        fields = ['foo']
        filter_fn = filtering.parse_query_string('foo = bar', fields)
        self.assertEqual(filter_fn.get_filtered_fields(), set(fields))

    def test_get_filtered_fields_multiple_values(self):
        """Test FilterFunction.get_filtered_fields() with multiple fields."""
        fields = ['name', 'hometown', 'occupation']
        filter_fn = filtering.parse_query_string('name = "Laura" and hometown = "Twin Peaks"', fields)
        self.assertEqual(filter_fn.get_filtered_fields(), {"name", "hometown"})

    def test_get_filtered_fields_on_keyerror(self):
        """Test FilterFunction.get_filtered_fields() on a bad field."""
        fields = ['foo', 'bar']
        filter_fn = filtering.parse_query_string('baz = quux', fields)
        self.assertEqual(filter_fn.get_filtered_fields(), set())

    def test_custom_filter_fields(self):
        """Test that CustomFilter fields are collected properly when filter has no subfilters."""
        only_fields = {'foo', 'bar'}
        custom_filter = filtering.CustomFilter(None, only_fields)
        self.assertEqual(custom_filter.get_filtered_fields(), only_fields)

    def test_custom_filter_fields_children(self):
        """Test that CustomFilter fields are collected properly when filter has subfilters."""
        child_fields = {'baz'}
        child_filter = filtering.CustomFilter(None, child_fields)

        sibling_fields = {'baz', 'giblet'}
        sibling_filter = filtering.CustomFilter(None, sibling_fields)

        parent_fields = {'foo', 'bar'}
        parent_filter = filtering.CustomFilter(None, parent_fields, children=[child_filter, sibling_filter])

        self.assertEqual(parent_filter.get_filtered_fields(), child_fields | sibling_fields | parent_fields)


class TestComparisonFilterEquality(unittest.TestCase):
    """Tests for equality checking on ComparisonFilters."""
    def setUp(self):
        self.headings = ['foo', 'bar']

    def test_parsed_filter_equality_different_key(self):
        """Test that two parsed filters are not equal if they query on a different key."""
        foo_filter = filtering.parse_query_string('foo=val', self.headings)
        bar_filter = filtering.parse_query_string('bar=val', self.headings)

        self.assertNotEqual(foo_filter, bar_filter)

    def test_parsed_filter_equality_same_expanded_query_key(self):
        """Test that two parsed filters are equal if they query on the same key with subsequence"""
        foo_filter = filtering.parse_query_string('f=val', self.headings)
        bar_filter = filtering.parse_query_string('foo=val', self.headings)

        self.assertEqual(foo_filter, bar_filter)

    def test_parsed_filter_inequality_different_values(self):
        """Test that two parsed filters are not equal if they have different comparison values"""
        foo_filter = filtering.parse_query_string('foo=some_val', self.headings)
        bar_filter = filtering.parse_query_string('foo=different_val', self.headings)

        self.assertNotEqual(foo_filter, bar_filter)

    def test_parsed_filter_inequality_different_expanded_query_keys(self):
        """Test that two parsed filters are not equal if they query on different keys with subsequence"""
        foo_filter = filtering.parse_query_string('f=val', self.headings)
        bar_filter = filtering.parse_query_string('b=val', self.headings)

        self.assertNotEqual(foo_filter, bar_filter)

    def test_parsed_filter_inequality_different_comparators(self):
        """Test that two parsed filters are not equal if they use different comaprators"""
        foo_filter = filtering.parse_query_string('foo=val', self.headings)
        bar_filter = filtering.parse_query_string('foo>val', self.headings)

        self.assertNotEqual(foo_filter, bar_filter)


class TestParseMultipleStrings(unittest.TestCase):
    """Tests for the parse_multiple_query_strings() function"""
    def setUp(self):
        self.headings = ['foo', 'baz']

    def test_parsing_no_filters(self):
        """Test parse_multiple_query_strings with no strings passed"""
        self.assertIsNone(filtering.parse_multiple_query_strings([], self.headings))

    def test_parsing_single_comparison_filter_gives_single_filter(self):
        """Test that parsing a single filter returns just a simple filter function"""
        self.assertTrue(isinstance(filtering.parse_multiple_query_strings(['foo=bar'], ['foo']),
                                   filtering.ComparisonFilter))

    def test_parsing_multiple_filters_produces_combined_filter(self):
        """Test that parsing multiple filter functions produces a combined filter"""
        filters = ['foo=bar', 'baz=quux']
        compiled_filters = [filtering.parse_query_string(f, self.headings) for f in filters]
        combined_filter = filtering.parse_multiple_query_strings(filters, self.headings)

        for compiled_filter in compiled_filters:
            self.assertIn(compiled_filter, combined_filter.filter_fns)

    def test_parsing_just_custom_filters(self):
        """Test that custom filters are passed through if just one is given"""
        def rubber_stamp(_):
            return True
        custom_filter = filtering.CustomFilter(rubber_stamp, self.headings)
        parsed_filter = filtering.parse_multiple_query_strings([], self.headings, filter_fns=[custom_filter])
        self.assertTrue(parsed_filter is custom_filter)

    def test_parsing_multiple_custom_filters(self):
        """Test that multiple custom filters are combined"""
        def rubber_stamp(_):
            return True

        def irritable_bureaucrat(_):
            return False

        filter_fns = [
            filtering.CustomFilter(fn, self.headings)
            for fn in [rubber_stamp, irritable_bureaucrat]
        ]

        parsed_filter = filtering.parse_multiple_query_strings([], self.headings, filter_fns=filter_fns)
        self.assertTrue(all(fn in parsed_filter.filter_fns for fn in filter_fns))

    def test_parsing_strs_with_custom_filters(self):
        """Test that parsed filter strings are combined with custom filter functions"""
        def rubber_stamp(_):
            return True
        custom_filter = filtering.CustomFilter(rubber_stamp, self.headings)

        filter_strs = ['foo=bar', 'baz=quux']
        str_filters = [filtering.parse_query_string(s, self.headings) for s in filter_strs]
        combined_filter = filtering.parse_multiple_query_strings(
            filter_strs, self.headings,
            filter_fns=[custom_filter]
        )

        for test_filter in str_filters:
            self.assertIn(test_filter, combined_filter.filter_fns)
        self.assertIn(custom_filter, combined_filter.filter_fns)


class TestRemoveConstantValues(unittest.TestCase):
    """Test the remove_constant_values function."""

    def test_no_constant_values(self):
        """Test remove_constant_values with no constant values."""
        people = [
            {'first': 'Jim', 'last': 'Morrison'},
            {'first': 'Janis', 'last': 'Joplin'},
            {'first': 'Kurt', 'last': 'Cobain'},
            {'first': 'Jimi', 'last': 'Hendrix'}
        ]
        const_removed = filtering.remove_constant_values(people, 'Morrison')
        self.assertEqual(people, const_removed)

    def test_common_but_not_constant_values(self):
        """Test remove_constant_values with some common but not constant values."""
        people = [
            {'first': 'Jim', 'last': 'Morrison'},
            {'first': 'Toni', 'last': 'Morrison'},
            {'first': 'Janis', 'last': 'Joplin'},
            {'first': 'Kurt', 'last': 'Cobain'},
            {'first': 'Jimi', 'last': 'Hendrix'}
        ]
        const_removed = filtering.remove_constant_values(people, 'Morrison')
        self.assertEqual(people, const_removed)

    def test_constant_values(self):
        """Test remove_constant_values with one key having a constant value."""
        people = [
            {'first': 'Jim', 'last': 'Morrison'},
            {'first': 'Jim', 'last': 'Henson'},
            {'first': 'Jim', 'last': 'Carrey'},
            {'first': 'Jim', 'last': 'Halpert'}
        ]
        expected_result = [
            {'last': 'Morrison'},
            {'last': 'Henson'},
            {'last': 'Carrey'},
            {'last': 'Halpert'}
        ]
        const_removed = filtering.remove_constant_values(people, 'Jim')
        self.assertEqual(expected_result, const_removed)

    def test_all_constant_values(self):
        """Test remove_constant_values with all keys having the same constant value."""
        input_len = 5
        people = [{'first': 'Thomas', 'last': 'Thomas'}] * input_len
        expected_result = [dict()] * input_len
        const_removed = filtering.remove_constant_values(people, 'Thomas')
        self.assertEqual(expected_result, const_removed)

    def test_ordered_dict(self):
        """Test remove_constant_values with OrderedDicts and ensure type is preserved."""
        people = [
            OrderedDict([('first', 'Jim'), ('last', 'Morrison'),
                         ('first', 'Janis'), ('last', 'Joplin')])
        ]
        const_removed = filtering.remove_constant_values(people, 'Morrison')
        self.assertEqual(people, const_removed)

    def test_empty_list(self):
        """Test remove_constant_values with an empty list."""
        empty = []
        const_removed = filtering.remove_constant_values([], 'something')
        self.assertEqual(empty, const_removed)

    @unittest.skipIf(os.getenv('SAT_SKIP_PERF_TESTS'),
                     'SAT_SKIP_PERF_TESTS is set in environment')
    def test_performance(self):
        """Test the performance of remove_constant_values with a lot of data."""
        # Create a large list of people with combinations of first and last names
        first_names = ['Jim', 'Toni', 'Janis', 'Kurt']
        last_names = ['Morrison', 'Joplin', 'Cobain']
        hidden = 'HIDDEN'

        # This is how many DIMMs we would have in a 10-cabinet system
        # 16 DIMMs/node * 4 nodes/slot * 8 slots/chassis * 8 chassis/cab * 10 cabs
        num_people = 40960

        people = []
        expected_result = []
        for i in range(num_people):
            person = {
                'first': first_names[i % len(first_names)],
                'last': last_names[i % len(last_names)],
                'ssn': hidden,
                'bank_account_number': hidden,
            }
            expected_person = copy.deepcopy(person)
            expected_person.pop('ssn')
            expected_person.pop('bank_account_number')
            people.append(person)
            expected_result.append(expected_person)

        start_time = time.time()
        const_removed = filtering.remove_constant_values(people, hidden)
        end_time = time.time()
        duration = end_time - start_time

        # A reasonable expected duration
        expected_duration = 0.2
        self.assertLessEqual(duration, expected_duration,
                             "remove_constant_values took longer than {:0.2f} seconds "
                             "({:0.2f} seconds) for {:d} values".format(expected_duration,
                                                                        duration, num_people))
        self.assertEqual(expected_result, const_removed)
