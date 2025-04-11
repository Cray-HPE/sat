#
# MIT License
#
# (C) Copyright 2022-2025 Hewlett Packard Enterprise Development LP
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
from unittest.mock import MagicMock

from jinja2.sandbox import SandboxedEnvironment

from sat.cli.bootprep.input.base import BaseInputItem, jinja_rendered
from sat.cli.bootprep.input.instance import InputInstance
from sat.constants import MISSING_VALUE


def create_input_item_cls():

    class SomeTestItem(BaseInputItem):
        """A mock concrete BaseInputItem class"""
        description = 'some test item'
        report_attrs = ['name', 'type', 'complex_data']

        def get_create_item_data(self):
            return

        def create(self, payload):
            return

        @property
        @jinja_rendered
        def name(self):
            return self.data.get('name')

        @property
        @jinja_rendered
        def type(self):
            return self.data.get('type')

        @property
        @jinja_rendered
        def complex_data(self):
            return self.data.get('complex_data')

    return SomeTestItem


class TestBaseInputItem(unittest.TestCase):

    def setUp(self):
        self.mock_instance = MagicMock(spec=InputInstance)
        self.jinja_env = SandboxedEnvironment()
        self.jinja_env.globals = {
            'default': {
                'note': 'foo',
                'suffix': '-bar',
                'system_name': 'ryan',
                'site-domain': 'example.com'
            }
        }
        self.mock_data = {
            "name": "test-item",
            "type": "test-type",
            "if_exists": None,  # Default value for if_exists
        }

        # Create a concrete subclass of BaseInputItem for testing
        class ConcreteBaseInputItem(BaseInputItem):
            """Dummy implementation of BaseInputItem for testing."""
            def get_create_item_data(self):
                return {}

            def create(self, payload):
                pass

        self.ConcreteBaseInputItem = ConcreteBaseInputItem

    def test_report_rows_have_correct_attrs(self):
        """Test that report rows are generated for input items"""
        data = {'name': 'foo', 'type': 'configuration', 'complex_data': 'columbo'}
        item_cls = create_input_item_cls()
        self.assertEqual(['foo', 'configuration', 'columbo'],
                         item_cls(data, self.mock_instance, 0, self.jinja_env).report_row())

    def test_report_rows_excluded(self):
        """Test that report rows are not included if not present in report_attrs"""
        data = {'name': 'foo', 'something_else': 'another_thing'}
        item_cls = create_input_item_cls()
        item_cls.report_attrs = ['name']
        self.assertEqual(item_cls(data, self.mock_instance, 0, self.jinja_env).report_row(), ['foo'])

    def test_missing_report_attrs_are_missing(self):
        """Test that missing report attrs are reported as MISSING"""
        # This data is missing a value for the 'complex_data' key
        data = {'name': 'foo', 'type': 'configuration'}
        item_cls = create_input_item_cls()
        item_cls.report_attrs = item_cls.report_attrs + ['nonexistent_property']
        report_row = item_cls(data, self.mock_instance, 0, self.jinja_env).report_row()
        self.assertEqual(['foo', 'configuration', None, MISSING_VALUE], report_row)

    def test_jinja_rendered_string_value(self):
        """Test that jinja_rendered works on a string value"""
        data = {'name': 'foo{{default.suffix}}', 'type': 'configuration-{{default.system_name}}'}
        item_cls = create_input_item_cls()
        item = item_cls(data, self.mock_instance, 0, self.jinja_env)
        self.assertEqual('foo-bar', item.name)
        self.assertEqual('configuration-ryan', item.type)

    def test_jinja_rendered_complex_value(self):
        """Test that jinja_rendered works on a more complex value"""
        data = {
            'name': 'foo',
            'type': 'configuration',
            'complex_data': {
                'kitchen': {
                    'furniture': ['{{furniture.brand}} table', '{{furniture.brand}} chair'],
                    'appliances': ['oven', 'fridge'],
                    'color': '{{paint.primary}}'
                },
                'living_room': {
                    'furniture': ['couch', 'chair', 'rug'],
                    'appliances': ['lamp', 'tv'],
                    'color': '{{paint.secondary}}'
                }
            }
        }
        self.jinja_env.globals = {
            'furniture': {
                'brand': 'IKEA'
            },
            'paint': {
                'primary': 'blue',
                'secondary': 'red'
            }
        }
        item_cls = create_input_item_cls()
        item = item_cls(data, self.mock_instance, 0, self.jinja_env)
        self.assertEqual(
            {
                'kitchen': {
                    'furniture': ['IKEA table', 'IKEA chair'],
                    'appliances': ['oven', 'fridge'],
                    'color': 'blue'
                },
                'living_room': {
                    'furniture': ['couch', 'chair', 'rug'],
                    'appliances': ['lamp', 'tv'],
                    'color': 'red'
                }
            },
            item.complex_data
        )

    def test_jinja_template_rendering_undefined_variable(self):
        """Test jinja_rendered property that uses an undefined variable."""
        item_cls = create_input_item_cls()
        data = {'name': '{{undefined_variable}}', 'type': '{{nested.undefined_variable}}'}
        item = item_cls(data, self.mock_instance, 0, self.jinja_env)

        self.assertEqual('', item.name)
        err_regex = (r"Failed to render Jinja2 template {{nested\.undefined_variable}} "
                     r"for value type: 'nested' is undefined")
        with self.assertRaisesRegex(item_cls.template_render_err, err_regex):
            item.type

    def test_jinja_template_rendering_undefined_variable_nested(self):
        """Test jinja_rendered property that uses an undefined variable in a nested field."""
        item_cls = create_input_item_cls()
        data = {
            'name': 'foo',
            'type': 'configuration',
            'complex_data': {
                'kitchen': {
                    'color': '{{colors.primary}}'
                }
            }
        }
        item = item_cls(data, self.mock_instance, 0, self.jinja_env)

        err_regex = (r"Failed to render Jinja2 template {{colors.primary}} "
                     r"for value complex_data: 'colors' is undefined")
        with self.assertRaisesRegex(item_cls.template_render_err, err_regex):
            item.complex_data

    def test_if_exists_skip(self):
        """Test BaseInputItem behavior when if_exists is set to 'skip'."""
        self.mock_data["if_exists"] = "skip"
        item = self.ConcreteBaseInputItem(self.mock_data, self.mock_instance, 0, self.jinja_env)

        # Ensure the if_exists attribute is set correctly
        self.assertEqual(item.if_exists, "skip")

    def test_if_exists_overwrite(self):
        """Test BaseInputItem behavior when if_exists is set to 'overwrite'."""
        self.mock_data["if_exists"] = "overwrite"
        item = self.ConcreteBaseInputItem(self.mock_data, self.mock_instance, 0, self.jinja_env)

        # Ensure the if_exists attribute is set correctly
        self.assertEqual(item.if_exists, "overwrite")

    def test_if_exists_abort(self):
        """Test BaseInputItem behavior when if_exists is set to 'abort'."""
        self.mock_data["if_exists"] = "abort"
        item = self.ConcreteBaseInputItem(self.mock_data, self.mock_instance, 0, self.jinja_env)

        # Ensure the if_exists attribute is set correctly
        self.assertEqual(item.if_exists, "abort")

    def test_if_exists_default(self):
        """Test BaseInputItem behavior when if_exists is not set."""
        del self.mock_data["if_exists"]  # Remove the if_exists key
        item = self.ConcreteBaseInputItem(self.mock_data, self.mock_instance, 0, self.jinja_env)

        # Ensure the if_exists attribute defaults to None
        self.assertIsNone(item.if_exists)
