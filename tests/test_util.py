#
# MIT License
#
# (C) Copyright 2019-2024 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Unit tests for sat/util.py.
"""
import copy
from collections import OrderedDict
from itertools import combinations, repeat
import logging
import os
from textwrap import dedent
from unittest import mock
import unittest
from unittest.mock import call, patch

from sat import util
from tests.common import ExtendedTestCase

PT_BORDERS_ON = False
PT_ALIGN = 'l'
PT_L_PAD_WIDTH = 1
SORT_BY = 1


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

    def test_format_long_list(self):
        """Test the formatting of format_long_list."""
        max_len = 2
        short_list = ['hello', 'goodbye']
        long_list = ['hello'] * 20
        expected_short_list = f'{", ".join(short_list)}'
        expected_long_list = f'hello, hello ... and 18 more'
        self.assertEqual(util.format_long_list(short_list, max_len), expected_short_list)
        self.assertEqual(util.format_long_list(long_list, max_len), expected_long_list)

    def test_format_as_dense_list(self):
        """Test the formatting of format_as_dense_list."""

        triples = [
            (  # plain old printing. sanity check
                'the quick brown fox jumped over a lazy dog',
                {'max_width': 40},
                dedent("""\
                the       quick     brown     fox
                jumped    over      a         lazy
                dog"""),
            ),
            (  # defaults with short input
                'foo bar baz',
                {},
                'foo    bar    baz'
            ),
            (  # max_width < width of each string
                'foo bar baz',
                {'max_width': 2},
                dedent("""\
                foo
                bar
                baz""")
            ),
            (  # passed strange value to margin_width
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


class TestBytesToGibibytes(unittest.TestCase):
    """Test conversion of bytes to gibibytes"""
    def test_power_of_2(self):
        """Test conversion with powers of 2"""
        exponents = [28, 30, 32, 34, 40]
        for exponent in exponents:
            expected_gib = 2 ** (exponent - 30)
            self.assertEqual(util.bytes_to_gib(2 ** exponent), expected_gib)

    def test_fractional_power_of_2(self):
        """Test that rounding works with a fractional GiB value"""
        # 2^27 bytes should be 1/8 of a byte, which converts to 0.125
        bytes_val = 2 ** 27
        # Note that the underlying round function uses bankers' rounding where
        # numbers equidistant to two ints are rounded to the nearest even int
        self.assertEqual(util.bytes_to_gib(bytes_val), 0.12)
        self.assertEqual(util.bytes_to_gib(bytes_val, 3), 0.125)
        self.assertEqual(util.bytes_to_gib(bytes_val, 4), 0.125)

    def test_non_power_of_2(self):
        """Test a number that is not an even power of 2."""
        bytes_val = 2**35 + 2**27
        self.assertEqual(util.bytes_to_gib(bytes_val), 32.12)
        self.assertEqual(util.bytes_to_gib(bytes_val, 3), 32.125)

    def test_real_value(self):
        """Test a real value seen on a system."""
        bytes_val = 503424483328
        self.assertEqual(util.bytes_to_gib(bytes_val), 468.85)
        self.assertEqual(util.bytes_to_gib(bytes_val, 3), 468.851)
        self.assertEqual(util.bytes_to_gib(bytes_val, 4), 468.8506)


class TestGetValByPath(unittest.TestCase):
    """Test the get_val_by_path function."""

    def test_top_level_key(self):
        """Test get_val_by_path with a top-level key."""
        d = {'foo': 'bar'}
        self.assertEqual('bar', util.get_val_by_path(d, 'foo'))

    def test_non_existent_top_level_key(self):
        """Test get_val_by_path with a non-existent top-level key."""
        d = {'foo': 'bar'}
        self.assertEqual(None, util.get_val_by_path(d, 'nope'))
        self.assertEqual('DNE', util.get_val_by_path(d, 'nope', 'DNE'))

    def test_nested_keys(self):
        """Test get_val_by_path with nested keys."""
        d = {
            'foo': {
                'bar': {
                    'baz': 'bat'
                }
            }
        }
        self.assertEqual('bat', util.get_val_by_path(d, 'foo.bar.baz'))
        self.assertEqual(None, util.get_val_by_path(d, 'does.not.exist'))

    def test_nonetype_value(self):
        """Test getting a value when an intermediate value is None."""
        d = {
            'foo': None
        }
        self.assertIsNone(util.get_val_by_path(d, 'foo.bar'))


class TestSetValByPath(unittest.TestCase):
    """Tests for set_val_by_path"""

    def test_set_new_nested_value(self):
        """Test that set_val_by_path adds a new key in a nested dict."""
        current_value = {
            'price_is_right': {
                'host': {
                    'first_name': 'Bob'
                }
            }
        }
        expected_value = copy.deepcopy(current_value)
        expected_value['price_is_right']['host']['last_name'] = 'Barker'
        util.set_val_by_path(current_value, 'price_is_right.host.last_name', 'Barker')
        self.assertEqual(expected_value, current_value)

    def test_set_value_overwrite(self):
        """Test that set_val_by_path overwrites a non-dict value with a dict value."""
        current_value = {
            'price_is_right': {
                'host': 'Bob Barker',
                'genre': 'Game Show'
            }
        }
        expected_value = {
            'price_is_right': {
                'host': {
                    'first_name': 'Drew',
                    'last_name': 'Carey'
                },
                'genre': 'Game Show'
            }
        }
        util.set_val_by_path(current_value, 'price_is_right.host.first_name', 'Drew')
        util.set_val_by_path(current_value, 'price_is_right.host.last_name', 'Carey')
        self.assertEqual(expected_value, current_value)

    def test_existing_value(self):
        """Test that set_val_by_path overwrites an existing value and adds a new value."""
        current_value = {
            'price_is_right': {
                'host': 'Bob Barker'
            }
        }
        expected_value = {
            'price_is_right': {
                'host': 'Drew Carey',
                'genre': 'Game Show'
            }
        }
        util.set_val_by_path(current_value, 'price_is_right.host', 'Drew Carey')
        util.set_val_by_path(current_value, 'price_is_right.genre', 'Game Show')
        self.assertEqual(expected_value, current_value)


class TestDeepUpdateDict(unittest.TestCase):
    """Tests for deep_update_dict function."""

    def test_add_key_nested(self):
        """Test deep_update_dict adds a key in a nested dict."""
        original = {
            'cast': {
                'Joel': 'Jim Carrey'
            }
        }
        new = {
            'cast': {
                'Clementine': 'Kate Winslet'
            }
        }
        expected = {
            'cast': {
                'Joel': 'Jim Carrey',
                'Clementine': 'Kate Winslet'
            }
        }

        util.deep_update_dict(original, new)

        self.assertEqual(expected, original)

    def test_replace_non_dict_value(self):
        """Test deep_update_dict when a non-dict value in original is replaced by a dict."""
        original = {
            'garden': ['corn', 'tomatoes', 'zucchini'],
            'yard': ['red fescue', 'kentucky bluegrass']
        }
        new = {
            'garden': {
                'row1': ['corn'],
                'row2': ['tomatoes'],
                'row3': ['zucchini']
            }
        }
        expected = {
            'garden': {
                'row1': ['corn'],
                'row2': ['tomatoes'],
                'row3': ['zucchini']
            },
            'yard': ['red fescue', 'kentucky bluegrass']
        }

        util.deep_update_dict(original, new)

        self.assertEqual(expected, original)

    def test_replace_with_non_dict_value(self):
        """Test deep_update_dict when a dict value in original is replaced by a non-dict."""
        original = {
            'kitchen': {
                'cupboard': {
                    'top_shelf': 'cups',
                    'bottom_shelf': 'plates'
                }
            },
            'bathroom': {
                'closet': ['medicine', 'towels']
            }
        }
        new = {
            'kitchen': {
                'cupboard': ['cups', 'plates']
            }
        }
        expected = {
            'kitchen': {
                'cupboard': ['cups', 'plates']
            },
            'bathroom': {
                'closet': ['medicine', 'towels']
            }
        }

        util.deep_update_dict(original, new)

        self.assertEqual(expected, original)

    def test_update_dict_with_non_dict(self):
        """Test that a ValueError is raised if attempting to update a dict with a non-dict."""
        with self.assertRaises(TypeError):
            util.deep_update_dict({'name': 'updateme'}, 'newname')

    def test_update_non_dict_with_dict(self):
        """Test that a ValueError is raised if attempting to update a non-dict value."""
        with self.assertRaises(TypeError):
            util.deep_update_dict('mrducks', {'response': 'mrnotducks'})


class TestCollapseVariables(unittest.TestCase):
    """Tests for collapsing variable names"""

    def test_non_nested_variable(self):
        """Test that flat dicts are unaffected"""
        flat_dict = {'foo': 'bar'}
        self.assertEqual(util.collapse_keys(flat_dict), flat_dict)

    def test_single_nested(self):
        """Test collapsing a single level of nesting"""
        self.assertEqual(util.collapse_keys({'foo': {'bar': 'baz'}}),
                         {'foo.bar': 'baz'})

    def test_multiple_nested(self):
        """Test collapsing multiple levels of nesting"""
        self.assertEqual(util.collapse_keys({'foo': {'bar': {'baz': {'quux': 'znurt'}}}}),
                         {'foo.bar.baz.quux': 'znurt'})

    def test_nested_with_multiple_keys(self):
        """Test collapsing multiple levels of nesting with multiple keys at each level"""
        input_dict = {
            'foo': {
                'bar': {
                    'baz': 'quux',
                    'giblet': 'znurt'
                }
            },
            'spam': {
                'eggs': 'france'
            }
        }

        collapsed = {
            'foo.bar.baz': 'quux',
            'foo.bar.giblet': 'znurt',
            'spam.eggs': 'france'
        }

        self.assertEqual(util.collapse_keys(input_dict), collapsed)

    def test_conflicting_existing_key(self):
        """Test that conflicts with an existing key with a collapsed name are detected"""
        with self.assertRaises(ValueError):
            _ = util.collapse_keys({'foo': {'bar': 'baz'}, 'foo.bar': 'baz'})

    def test_conflicting_collapsed_key(self):
        """Test that conflicts with a collapsed name with an existing key are detected"""
        with self.assertRaises(ValueError):
            _ = util.collapse_keys({'foo.bar': 'baz', 'foo': {'bar': 'baz'}})


class TestGetNewOrderedDict(unittest.TestCase):
    """Test the get_new_ordered_dict function."""

    def setUp(self):
        """Set up a little nested dict for tests to use."""
        self.orig_dict = {
            'foo': 'bar',
            'baz': {
                'bat': 'tab'
            },
            'other_key': 'value'
        }

    def test_docstring_example(self):
        """Test get_new_ordered_dict with the example from its docstring"""
        new_dict = util.get_new_ordered_dict(self.orig_dict,
                                             ['foo', 'baz.bat', 'nope'])
        expected = OrderedDict([
            ('foo', 'bar'),
            ('bat', 'tab'),
            ('nope', None)
        ])
        self.assertEqual(expected, new_dict)

    def test_alternate_default(self):
        """Test get_new_ordered_dict with an alternate default value."""
        alt = 'alternate default'
        new_dict = util.get_new_ordered_dict(self.orig_dict, ['foo', 'dne'],
                                             default_value=alt)
        expected = OrderedDict([
            ('foo', 'bar'),
            ('dne', alt)
        ])
        self.assertEqual(expected, new_dict)

    def test_unstripped_path(self):
        """Test get_new_ordered_dict without stripping paths."""
        new_dict = util.get_new_ordered_dict(self.orig_dict, ['baz.bat'],
                                             strip_path=False)
        expected = OrderedDict([
            ('baz.bat', 'tab')
        ])
        self.assertEqual(expected, new_dict)

    def test_stripped_path_collision(self):
        """Test get_new_ordered_dict with paths that collide when stripped."""
        orig_dict = {
            'bar': 'top',
            'foo': {
                'bar': 'nested'
            }
        }
        self.assertEqual('top',
                         util.get_new_ordered_dict(orig_dict,
                                                   ['foo.bar', 'bar'])['bar'])
        self.assertEqual('nested',
                         util.get_new_ordered_dict(orig_dict,
                                                   ['bar', 'foo.bar'])['bar'])

    def test_example_cfs_data(self):
        """Test get_new_ordered_dict with some example CFS data."""
        orig_dict = {
            'name': 'cfs_session_name',
            'status': {
                'session': {
                    'status': 'complete'
                }
            }
        }
        # Throw in a path with multiple components where the first components
        # are in the dict, but the last one is not.
        new_dict = util.get_new_ordered_dict(orig_dict,
                                             ['name', 'status.session.status',
                                              'status.session.nope'])
        expected = OrderedDict([
            ('name', orig_dict['name']),
            ('status', orig_dict['status']['session']['status']),
            ('nope', None)
        ])
        self.assertEqual(expected, new_dict)


class TestPesterChoices(unittest.TestCase):
    """Test the pester_choices function."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_print = mock.patch('builtins.print').start()
        self.mock_input = mock.patch('builtins.input').start()

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_valid_answer(self):
        """Test pester_choices with a valid answer."""
        self.mock_input.return_value = 'yes'
        response = util.pester_choices('Continue?', ('yes', 'no'))
        self.mock_input.assert_called_once_with('Continue? [yes,no] ')
        self.assertEqual('yes', response)

    def test_eventual_valid_answer(self):
        """Test pester_choices with invalid answers and then a valid answer."""
        self.mock_input.side_effect = ['yarp', 'nope', 'nah', 'maybe']
        response = util.pester_choices('Do you agree? ', ('yes', 'no', 'maybe'))
        correction_msg = 'Input must be one of the following choices: yes, no, maybe'
        self.mock_print.assert_has_calls([mock.call(correction_msg)] * 3)
        self.assertEqual('maybe', response)

    def test_eof(self):
        """Test when interrupted by an EOFError."""
        self.mock_input.side_effect = ['no', 'maybe', EOFError]
        response = util.pester_choices('What is your favorite prog rock band?', ('yes',))
        correction_msg = 'Input must be one of the following choices: yes'
        self.mock_print.assert_has_calls([mock.call(correction_msg)] * 2)
        self.assertEqual(response, None)


class TestPromptContinue(unittest.TestCase):
    """Test the prompt_continue function."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_print = mock.patch('builtins.print').start()
        self.mock_pester_choices = mock.patch('sat.util.pester_choices').start()

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_yes(self):
        """Test prompt_continue when user answers 'yes'."""
        self.mock_pester_choices.return_value = 'yes'
        action_msg = 'action'
        util.prompt_continue(action_msg)
        self.mock_print.assert_called_once_with('Proceeding with {}.'.format(action_msg))

    def test_no(self):
        """Test prompt_continue when user answers 'no'."""
        self.mock_pester_choices.return_value = 'no'
        action_msg = 'action'
        with self.assertRaises(SystemExit):
            util.prompt_continue(action_msg)
        self.mock_print.assert_called_once_with('Will not proceed with {}. '
                                                'Exiting.'.format(action_msg))

    def test_with_description(self):
        """Test prompt_continue with an optional description."""
        self.mock_pester_choices.return_value = 'yes'
        action_msg = 'action'
        description = 'description preceding the prompt'
        util.prompt_continue(action_msg, description)

        self.mock_print.assert_has_calls([
            call(description),
            call('Proceeding with {}.'.format(action_msg))
        ])


class TestGetS3Resource(ExtendedTestCase):
    """Test the get_s3_resource function"""
    def setUp(self):
        self.mock_boto3 = mock.patch('sat.util.boto3.resource').start()
        self.mock_read_config_value_file = mock.patch(
            'sat.util.read_config_value_file',
            side_effect=self.fake_read_config_value_file
        ).start()
        self.mock_get_config_value = mock.patch('sat.util.get_config_value').start()
        self.access_key = mock.Mock()
        self.secret_key = mock.Mock()
        self.fake_config = {
            's3': {
                'access_key_file': self.access_key,
                'secret_key_file': self.secret_key
            }
        }

    def fake_read_config_value_file(self, query_string):
        """Fake the behavior of read_config_value_file."""
        section, value = query_string.split('.')
        return self.fake_config[section][value]

    def test_get_s3_resource(self):
        """Test get_s3_resource in the successful case."""
        result = util.get_s3_resource()
        self.assertEqual([mock.call('s3.access_key_file'), mock.call('s3.secret_key_file')],
                         self.mock_read_config_value_file.mock_calls)
        self.mock_get_config_value.assert_any_call('s3.endpoint')
        self.mock_get_config_value.assert_any_call('s3.cert_verify')
        self.mock_boto3.assert_called_once_with(
            's3',
            endpoint_url=self.mock_get_config_value.return_value,
            aws_access_key_id=self.access_key,
            aws_secret_access_key=self.secret_key,
            region_name='',
            verify=self.mock_get_config_value.return_value
        )
        self.assertEqual(result, self.mock_boto3.return_value)

    def test_get_s3_resource_open_file_error(self):
        """Test get_s3_resource when opening a file fails"""
        self.mock_read_config_value_file.side_effect = OSError('Failed to open file')
        expected_err = 'Unable to load configuration: Failed to open file'
        with self.assertRaisesRegex(util.S3ResourceCreationError, expected_err):
            util.get_s3_resource()

    def test_get_s3_resource_value_error(self):
        """Test get_s3_resource creating the S3 ServiceResource"""
        self.mock_boto3.side_effect = ValueError('Bad URL value')
        expected_err = 'Unable to load S3 API: Bad URL value'
        with self.assertRaisesRegex(util.S3ResourceCreationError, expected_err):
            util.get_s3_resource()


class TestBeginEndLogger(ExtendedTestCase):
    """Test the BeginEndLogger context manager class."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_monotonic = mock.patch('time.monotonic').start()
        self.time_vals = [0, 10]
        self.mock_monotonic.side_effect = self.time_vals

    def tearDown(self):
        """Stop mock patching."""
        mock.patch.stopall()

    def test_logged_messages_and_duration(self):
        """Test the messages and duration logged by BeginEndLogger."""
        my_stage = 'the test'
        with self.assertLogs(level=logging.DEBUG) as cm:
            with util.BeginEndLogger(my_stage):
                pass  # NOSONAR

        self.assert_in_element(f'BEGIN: {my_stage}', cm.output)
        self.assert_in_element(f'END: {my_stage}. Duration: 0:00:10', cm.output)

    def test_logged_messages_custom_level(self):
        """Test the messages and duration logged by BeginEndLogger with custom level."""
        with self.assertLogs(level=logging.INFO) as cm:
            with util.BeginEndLogger('test', level=logging.INFO):
                pass  # NOSONAR

        self.assertEqual(2, len(cm.output))


class TestGetUsernameAndPasswordInteractively(ExtendedTestCase):
    def setUp(self):
        """Set up some mocks."""
        self.mock_input = mock.patch('sat.util.input').start()
        self.mock_getpass = mock.patch('sat.util.getpass').start()

    def tearDown(self):
        """Stop mock patching."""
        mock.patch.stopall()

    def test_get_username_and_password_default(self):
        """Test get_username_and_password_interactively prompts for username and password when needed."""
        username, password = util.get_username_and_password_interactively()
        self.mock_input.assert_called_once_with('Username: ')
        self.mock_getpass.assert_called_once_with('Password: ')
        self.assertEqual(username, self.mock_input.return_value)
        self.assertEqual(password, self.mock_getpass.return_value)

    def test_get_username_and_password_with_custom_prompts(self):
        """Test get_username_and_password_interactively prompts using custom prompts."""
        username, password = util.get_username_and_password_interactively(
            username_prompt='Admin Username', password_prompt='Admin Password'
        )
        self.mock_input.assert_called_once_with('Admin Username: ')
        self.mock_getpass.assert_called_once_with('Admin Password: ')
        self.assertEqual(username, self.mock_input.return_value)
        self.assertEqual(password, self.mock_getpass.return_value)

    def test_get_username_and_password_with_username(self):
        """Test get_username_and_password_interactively prompts only for password when a username is given."""
        username, password = util.get_username_and_password_interactively(username='crayadmin')
        self.mock_input.assert_not_called()
        self.mock_getpass.assert_called_once_with('Password: ')
        self.assertEqual(username, 'crayadmin')
        self.assertEqual(password, self.mock_getpass.return_value)

    def test_get_username_and_password_with_password(self):
        """Test get_username_and_password_interactively prompts only for username when a password is given."""
        username, password = util.get_username_and_password_interactively(password='crayadmin')
        self.mock_input.assert_called_once_with('Username: ')
        self.mock_getpass.assert_not_called()
        self.assertEqual(username, self.mock_input.return_value)
        self.assertEqual(password, 'crayadmin')

    def test_get_username_and_password_confirm_match(self):
        """Test get_username_and_password_interactively confirms password when requested and returns when they match."""
        self.mock_getpass.side_effect = ('PasswordA', 'PasswordA')
        username, password = util.get_username_and_password_interactively(confirm_password=True)
        self.mock_input.assert_called_once_with('Username: ')
        self.assertListEqual(
            [mock.call('Password: '), mock.call('Confirm Password: ')],
            self.mock_getpass.mock_calls
        )
        self.assertEqual(username, self.mock_input.return_value)
        self.assertEqual(password, 'PasswordA')

    def test_get_username_and_password_confirm_mismatch(self):
        """Test get_username_and_password_interactively confirms password and logs an error on a mismatch."""
        # Mock a situation in which the first attempt is a mismatch but the second attempt works.
        self.mock_getpass.side_effect = ('PasswordA', 'PasswordB', 'PasswordA', 'PasswordA')
        with self.assertLogs(level=logging.ERROR) as logs:
            username, password = util.get_username_and_password_interactively(confirm_password=True)
        self.mock_input.assert_called_once_with('Username: ')
        self.assertListEqual(
            [mock.call('Password: '), mock.call('Confirm Password: '),
             mock.call('Password: '), mock.call('Confirm Password: ')],
            self.mock_getpass.mock_calls
        )
        self.assertEqual(username, self.mock_input.return_value)
        self.assertEqual(password, 'PasswordA')
        self.assert_in_element('Passwords do not match', logs.output)


class TestSubsequenceMatching(unittest.TestCase):
    """Tests for helper functions for filtering and matching."""
    def test_is_subsequence(self):
        """Test subsequence matching."""
        test_str = 'spamneggs'
        for str_len in range(len(test_str) + 1):
            for subseq in combinations(test_str, str_len):
                self.assertTrue(util.is_subsequence(''.join(subseq), test_str))

    def test_trivial_subsequence(self):
        """Test empty string is a subsequence."""
        self.assertTrue(util.is_subsequence('', 'foo'))

    def test_subseq_of_empty(self):
        """Test subsequences of the empty string."""
        self.assertFalse(util.is_subsequence('foo', ''))
        self.assertTrue(util.is_subsequence('', ''))

    def test_is_not_subsequence(self):
        """Test subsequence misses."""
        haystack = 'foobarbaz'
        for needle in ['zabraboof', 'nothing', 'ofoarbazb',
                       'foobarbax', 'bff', 'egads']:
            self.assertFalse(util.is_subsequence(needle, haystack))


class TestEnsurePermissions(unittest.TestCase):
    """Tests for the ensure_permissions() function"""
    def setUp(self):
        self.mock_chmod = patch('sat.util.os.chmod').start()

        def mock_is_file(path):
            return path == self.path
        self.mock_is_file = patch('sat.util.os.path.isfile',
                                  side_effect=mock_is_file).start()

        def mock_is_dir(path):
            return path == self.dirname
        self.mock_is_dir = patch('sat.util.os.path.isdir',
                                 side_effect=mock_is_dir).start()

        self.dirname = '/foo/bar/baz'
        self.filename = 'quux.toml'
        self.path = os.path.join(self.dirname, self.filename)

    def tearDown(self):
        patch.stopall()

    def test_file_and_dir_chmodded(self):
        """Test that the target file and containing directory are chmodded"""
        util.ensure_permissions(self.path)
        self.mock_chmod.assert_any_call(self.dirname, 0o700)
        self.mock_chmod.assert_any_call(self.path, 0o600)

    def test_directory_chmodded_when_file_missing(self):
        """Test that the containing directory is chmodded when the file is missing"""
        # Using `side_effect = repeat(...)` is essentially the same as using
        # `return_value`, but since `side_effect` is set in `setUp()`, it
        # overrides `return_value`.
        self.mock_is_file.side_effect = repeat(False)

        util.ensure_permissions(self.path)
        self.mock_chmod.assert_called_once_with(self.dirname, 0o700)

    def test_nothing_chmodded_when_directory_missing(self):
        """Test that chmod() is not called when file and directory are missing"""
        self.mock_is_file.side_effect = repeat(False)
        self.mock_is_dir.side_effect = repeat(False)
        util.ensure_permissions(self.path)
        self.mock_chmod.assert_not_called()

    def test_directory_chmod_when_path_is_dir(self):
        """Test changing the permissions on a directory path"""
        self.mock_is_file.side_effect = repeat(False)
        util.ensure_permissions(self.dirname)
        self.mock_chmod.assert_called_once_with(self.dirname, 0o700)


if __name__ == '__main__':
    unittest.main()
