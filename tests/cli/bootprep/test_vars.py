#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
Unit tests for variable loading
"""

from textwrap import dedent
import unittest
from unittest.mock import mock_open, patch

from sat.cli.bootprep.constants import LATEST_VERSION_VALUE
from sat.cli.bootprep.vars import VariableContext


class TestEnumeratingVars(unittest.TestCase):
    """Test enumerating variables and sources"""

    def setUp(self):
        self.context = VariableContext()
        self.vars_file_contents = dedent("""
        foo:
            version: 2.3.4
        bar:
            version: 4.5.6
        """)

        self.mock_catalog = patch('sat.cli.bootprep.vars.HPCSoftwareRecipeCatalog').start()
        self.software_recipe_vars = {
            'foo': {'version': '1.2.3'},
            'bar': {'version': '2.3.4'}
        }
        self.mock_catalog.return_value.get_latest_version.return_value.all_vars = self.software_recipe_vars
        self.mock_catalog.return_value.get_recipe_version.return_value.all_vars = self.software_recipe_vars

    def tearDown(self):
        patch.stopall()

    def test_getting_latest_recipe_vars(self):
        """Test enumerating variables from the latest recipe"""
        self.context.recipe_version = LATEST_VERSION_VALUE
        expected_elements = {('foo.version', '1.2.3', 'latest recipe'),
                             ('bar.version', '2.3.4', 'latest recipe')}
        self.assertEqual(set(self.context.enumerate_vars_and_sources()), expected_elements)

    def test_getting_arbitrary_recipe_vars(self):
        """Test enumerating variables from a given recipe version"""
        self.context.recipe_version = '22.07'

        expected_elements = {('foo.version', '1.2.3', '22.07 recipe'),
                             ('bar.version', '2.3.4', '22.07 recipe')}
        self.assertEqual(set(self.context.enumerate_vars_and_sources()), expected_elements)

    def test_getting_file_vars(self):
        """Test retrieving variables from a vars file"""
        self.software_recipe_vars = {}
        vars_file_path = 'some_path.yaml'
        self.context.vars_file_path = vars_file_path
        with patch('sat.cli.bootprep.vars.open', mock_open(read_data=self.vars_file_contents)):
            expected_elements = {('foo.version', '2.3.4', vars_file_path),
                                 ('bar.version', '4.5.6', vars_file_path)}
            self.assertEqual(set(self.context.enumerate_vars_and_sources()), expected_elements)

    def test_getting_cli_vars(self):
        """Test retrieving variables from the command line"""
        self.software_recipe_vars = {}
        self.context.cli_vars = {
            'foo': {'version': '1.2.3'},
            'bar': {'version': '2.3.4'}
        }
        self.context.recipe_version = LATEST_VERSION_VALUE
        expected_elements = {('foo.version', '1.2.3', '--vars'),
                             ('bar.version', '2.3.4', '--vars')}
        self.assertEqual(set(self.context.enumerate_vars_and_sources()), expected_elements)

    def test_file_vars_override_catalog(self):
        """Test that file vars override the HPC CSM Software Recipe"""
        vars_file_path = 'some_path.yaml'
        self.context.vars_file_path = vars_file_path
        vars_file_content = dedent("""
        foo:
            version: 1.2.4
        """)
        self.context.recipe_version = LATEST_VERSION_VALUE
        with patch('sat.cli.bootprep.vars.open', mock_open(read_data=vars_file_content)):
            expected_elements = {('foo.version', '1.2.4', vars_file_path),
                                 ('bar.version', '2.3.4', 'latest recipe')}
            self.assertEqual(set(self.context.enumerate_vars_and_sources()), expected_elements)

    def test_cli_vars_override_file_and_catalog(self):
        """Test that CLI vars override the vars file and catalog"""
        vars_file_path = 'some_path.yaml'
        self.context.vars_file_path = vars_file_path
        vars_file_content = dedent("""
        foo:
            version: 1.2.4
        """)
        self.context.cli_vars = {
            'foo': {'version': '1.2.5'}
        }
        self.context.recipe_version = LATEST_VERSION_VALUE
        with patch('sat.cli.bootprep.vars.open', mock_open(read_data=vars_file_content)):
            expected_elements = {('foo.version', '1.2.5', '--vars'),
                                 ('bar.version', '2.3.4', 'latest recipe')}
            self.assertEqual(set(self.context.enumerate_vars_and_sources()), expected_elements)
