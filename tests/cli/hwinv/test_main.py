#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.cli.hwinv.main.
"""

from functools import wraps
import unittest
from unittest.mock import MagicMock, patch

import sat.cli.hwinv.main
from sat.cli.hwinv.main import get_display_fields


# TODO: Add actual tests of code in sat.cli.hwinv.main. See SAT-224.
# Having this test file that imports sat.cli.hwinv.main forces the coverage
# module to report coverage on that file.
class TestHwinvMain(unittest.TestCase):

    def test_something(self):
        self.assertTrue(True)


def list_and_summary(fn):
    """Helper function to run test cases for both list and summary operations"""
    @wraps(fn)
    def inner(*args, **kwargs):
        for op in ['list', 'summary']:
            new_args = list(args)
            new_args.append(op)
            fn(*new_args, **kwargs)

    return inner


class TestGettingFields(unittest.TestCase):
    def setUp(self):
        self.args = MagicMock()
        self.object_type = MagicMock(pretty_name='Test Object', arg_name='test_object')
        self.object_type.get_listable_fields.side_effect = lambda x: x
        self.object_type.get_summary_fields.side_effect = lambda x: x
        self.all_fields = ['foo', 'bar', 'baz']

    def tearDown(self):
        patch.stopall()

    def configureTest(self, general_fields, specific_fields, operation):
        self.args.fields = general_fields
        if operation == 'list':
            self.args.test_object_fields = specific_fields
        elif operation == 'summary':
            self.args.test_object_summary_fields = specific_fields

        self.operation = operation

    @list_and_summary
    def test_getting_fields_with_only_specifics(self, op):
        """Test getting fields with only specific fields"""
        self.configureTest([], ['foo', 'bar'], op)
        display_fields = get_display_fields(self.args, self.object_type, self.operation)
        self.assertEqual(display_fields, ['foo', 'bar'])

    @list_and_summary
    def test_getting_fields_with_only_generals(self, op):
        """Test getting fields with only general fields"""
        self.configureTest(['foo', 'bar'], [], op)
        display_fields = get_display_fields(self.args, self.object_type, self.operation)
        self.assertEqual(display_fields, ['foo', 'bar'])

    @list_and_summary
    def test_specific_fields_override_general(self, op):
        """Test that specific fields override general listable fields."""
        general = ['foo', 'bar']
        specific = ['foo']
        self.configureTest(general, specific, op)
        with self.assertLogs(level='WARNING'):
            # Ensure that a warning is logged here, since the user should be
            # notified which fields are being used.
            display_fields = get_display_fields(self.args, self.object_type, self.operation)
        self.assertEqual(display_fields, specific)

    @list_and_summary
    def test_returning_all_fields_when_none_specified(self, op):
        """Test that all fields are returned when neither specific nor general are given."""
        self.configureTest([], [], op)
        self.object_type.get_listable_fields.side_effect = None
        self.object_type.get_summary_fields.side_effect = None

        self.object_type.get_listable_fields.return_value = self.all_fields
        self.object_type.get_summary_fields.return_value = self.all_fields

        display_fields = get_display_fields(self.args, self.object_type, self.operation)
        self.assertEqual(display_fields, self.all_fields)


if __name__ == '__main__':
    unittest.main()
