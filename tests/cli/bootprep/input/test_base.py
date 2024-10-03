#
# MIT License
#
# (C) Copyright 2022-2024 Hewlett Packard Enterprise Development LP
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
Tests for functionality in the BaseInputItem classes
"""

import unittest
from jinja2 import Template

from sat.cli.bootprep.input.base import BaseInputItem
from sat.constants import MISSING_VALUE


def create_input_item_cls(cls_report_attrs):

    class SomeTestItem(BaseInputItem):
        """A mock concrete BaseInputItem class"""
        description = 'some input item'
        report_attrs = cls_report_attrs

        def __init__(self, data):
            # Since the test input item class doesn't need access
            # to the input instance, we can just ignore it here.
            # As a consequence, other methods on this class won't
            # work as expected.
            self.data = data

        def __getattr__(self, item):
            if item in cls_report_attrs:
                try:
                    return self.data[item]
                except KeyError as err:
                    raise AttributeError(str(err))

        def get_create_item_data(self):
            return

        def create(self, payload):
            return

        def render_jinja_template(self, template_str):
            """Render a Jinja template with provided data."""
            template = Template(template_str)
            return template.render(**self.data)

    return SomeTestItem


class TestBaseInputItem(unittest.TestCase):
    def test_report_rows_have_correct_attrs(self):
        """Test that report rows are generated for input items"""
        row_headings = ['name', 'type']
        row_vals = ['foo', 'configuration']
        item_cls = create_input_item_cls(row_headings)
        self.assertEqual(item_cls(dict(zip(row_headings, row_vals))).report_row(),
                         row_vals)

    def test_report_rows_excluded(self):
        """Test that report rows are not included if not present in report_attrs"""
        item_cls = create_input_item_cls(['name'])
        self.assertEqual(item_cls({'name': 'foo', 'something_else': 'another_thing'}).report_row(), ['foo'])

    def test_missing_report_attrs_are_missing(self):
        """Test that missing report attrs are reported as MISSING"""
        row_headings = ['name', 'type', 'one_more_thing']
        row_vals = ['foo', 'configuration', 'columbo']
        item_cls = create_input_item_cls(row_headings)  # Cut off last report attr
        data = dict(zip(row_headings[:-1], row_vals[:-1]))

        report_row = item_cls(data).report_row()
        self.assertEqual(len(report_row), len(row_headings))
        self.assertEqual(report_row[-1], MISSING_VALUE)

    def test_jinja_template_rendering(self):
        """Test Jinja template rendering with data from the input item."""
        item_cls = create_input_item_cls(['name', 'type'])
        data = {'name': 'foo', 'type': 'configuration'}
        item = item_cls(data)

        template_str = "name: {{name}} and type: {{type}}"
        rendered_output = item.render_jinja_template(template_str)
        expected_output = "name: foo and type: configuration"
        self.assertEqual(rendered_output, expected_output)
