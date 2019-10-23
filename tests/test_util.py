"""
Unit tests for sat/util.py .

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from itertools import product
import os
from textwrap import dedent
from unittest import mock
import unittest

from sat import util

PT_BORDERS_ON = False
PT_ALIGN = 'l'
PT_L_PAD_WIDTH = 0
SORT_BY = 1

class TestPrettyPrinters(unittest.TestCase):
    """Tests for functions that do pretty printing."""

    def test_get_pretty_printed_dict(self):
        """Test a plain dict is output properly."""
        test_dict = {
            'fox': 'quick, brown',
            'dog': 'lazy',
            'action': 'jump',
            'fox_speed': 100
        }
        pretty_printed = util.get_pretty_printed_dict(test_dict)
        self.assertEqual(pretty_printed, dedent("""\
                         fox:       quick, brown
                         dog:       lazy
                         action:    jump
                         fox_speed: 100"""))

class TestPrettyTables(unittest.TestCase):
    def setUp(self):
        self.headings = ['ingredient', 'amount']
        self.rows = [['flour', '3 cups'],
                     ['white sugar', '1 cup'],
                     ['brown sugar', '1 cup'],
                     ['softened butter', '1 cup'],
                     ['eggs', '2'],
                     ['vanilla', '2 tsp'],
                     ['baking soda', '1 tsp'],
                     ['chocolate chips', '2 cups']]

        self.add_row_mock = mock.patch('sat.util.PrettyTable.add_row').start()

    def tearDown(self):
        mock.patch.stopall()

    def test_get_pretty_table_default_args(self):
        """Test a PrettyTable can be printed without headings, unsorted."""
        pt = util.get_pretty_table(self.rows)

        self.assertEqual(pt.border, PT_BORDERS_ON)
        self.assertEqual(pt.left_padding_width, PT_L_PAD_WIDTH)
        self.assertFalse(pt.header)
        self.assertEqual(pt.field_names, self.rows[0])
        self.assertIsNone(pt.sortby)

        self.add_row_mock.assert_has_calls(mock.call(row) for row in self.rows)
        self.assertTrue(all(pt.align[x] == PT_ALIGN for x in pt.align))

    def test_get_pretty_table_with_headings_no_sort(self):
        """Test a PrettyTable can be printed without headings, unsorted."""
        pt = util.get_pretty_table(self.rows, headings=self.headings)

        self.assertEqual(pt.border, PT_BORDERS_ON)
        self.assertEqual(pt.left_padding_width, PT_L_PAD_WIDTH)
        self.assertTrue(pt.header)
        self.assertEqual(pt.field_names, self.headings)
        self.assertIsNone(pt.sortby)

        self.add_row_mock.assert_has_calls(mock.call(row) for row in self.rows)
        self.assertTrue(all(pt.align[x] == PT_ALIGN for x in pt.align))

    def test_get_pretty_table_with_headings_sorted(self):
        """Test a PrettyTable can be printed with headings, sorted."""
        pt = util.get_pretty_table(self.rows, headings=self.headings,
                                   sort_by=SORT_BY)

        self.assertEqual(pt.border, PT_BORDERS_ON)
        self.assertEqual(pt.left_padding_width, PT_L_PAD_WIDTH)
        self.assertTrue(pt.header)
        self.assertEqual(pt.field_names, self.headings)
        self.assertEqual(pt.sortby, self.headings[SORT_BY])

        self.add_row_mock.assert_has_calls(mock.call(row) for row in self.rows)
        self.assertTrue(all(pt.align[x] == PT_ALIGN for x in pt.align))

    def test_get_pretty_table_without_headings_sorted(self):
        """Test a PrettyTable can be printed without headings, unsorted."""
        pt = util.get_pretty_table(self.rows, sort_by=SORT_BY)

        self.assertEqual(pt.border, PT_BORDERS_ON)
        self.assertEqual(pt.left_padding_width, PT_L_PAD_WIDTH)
        self.assertFalse(pt.header)
        self.assertEqual(pt.field_names, self.rows[0])
        self.assertEqual(pt.sortby, self.rows[0][SORT_BY])

        self.add_row_mock.assert_has_calls(mock.call(row) for row in self.rows)
        self.assertTrue(all(pt.align[x] == PT_ALIGN for x in pt.align))

    @mock.patch('sat.util.get_pretty_table')
    def test_pretty_print_list(self, mock_get_pretty_table):
        """Test the pretty-printed result is always equal to what we expect."""
        for args in product((self.rows,), (None, self.headings), range(len(self.headings))):
            self.assertEqual(util.get_pretty_printed_list(*args),
                             str(mock_get_pretty_table.return_value))

class TestMiscFormatters(unittest.TestCase):
    def test_get_rst_header(self):
        """Test the header string for the given header level is correct."""
        MIN_LEN = 80
        HEADER = 'Camelot'

        for level, char in zip(range(1, 6), ['#', '=', '-', '^', '"']):
            lines = util.get_rst_header(HEADER, header_level=level,
                                        min_len=MIN_LEN).split('\n')

            self.assertIn(char * MIN_LEN, lines)
            self.assertIn(HEADER, lines)

    def test_format_as_dense_list(self):
        """Test the formatting of format_as_dense_list."""

        triples = [
            ( # plain old printing. sanity check
                'the quick brown fox jumped over a lazy dog',
                {'max_width': 40},
                dedent("""\
                the       quick     brown     fox
                jumped    over      a         lazy
                dog"""),
            ),
            ( # defaults with short input
                'foo bar baz',
                {},
                'foo    bar    baz'
            ),
            ( # max_width < width of each string
                'foo bar baz',
                {'max_width': 2},
                dedent("""\
                foo
                bar
                baz""")
            ),
            ( # passed strange value to margin_width
                'foo bar baz',
                {'margin_width': -1},
                'foo    bar    baz'
            )
        ]

        for string, kwargs, result in triples:
            dense_list = util.format_as_dense_list(
                string.split(), **kwargs)
            self.assertEqual('\n'.join(line.strip() for line in dense_list.split('\n')).strip(),
                             result)

class TestMiscUtils(unittest.TestCase):
    """Test miscellaneous utility functions"""
    def setUp(self):
        self.mkdir_mock = mock.patch('sat.util.os.makedirs').start()
        self.resource = 'cool_thing'
        self.home = '/home/foo'
        self.path = '/home/foo/.config/sat/.'

    def tearDown(self):
        mock.patch.stopall()

    def test_get_resource_filename(self):
        """Test getting paths to resources."""
        with mock.patch.dict('sat.util.os.environ', {'HOME': self.home}):
            self.assertEqual(util.get_resource_filename(self.resource),
                             os.path.join(self.path, self.resource))
            self.mkdir_mock.assert_called_with(self.path, exist_ok=True)

    def test_exit_if_cant_make_resource_dir(self):
        """Test whether the program exits if the resource directory can't be opened."""
        self.mkdir_mock.side_effect = FileNotFoundError('Couldn\'t open it...')
        with self.assertRaises(SystemExit):
            util.get_resource_filename(self.resource)
