#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.cli.init.main
"""
import logging

from argparse import Namespace
from tests.test_util import ExtendedTestCase
import unittest
from unittest.mock import patch

from sat.cli.init.main import do_init
from sat.config import ConfigFileExistsError, DEFAULT_CONFIG_PATH


class TestInitMain(ExtendedTestCase):

    def setUp(self):
        """Set up some mocks."""
        self.sat_init_args = Namespace(
            output=None,
            force=False,
            username=None
        )
        self.mock_print = patch('sat.cli.init.main.print').start()
        self.mock_generate_default_config = patch('sat.cli.init.main.generate_default_config').start()
        self.mock_getenv = patch('sat.cli.init.main.os.getenv').start()
        self.mock_getenv.return_value = DEFAULT_CONFIG_PATH

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    def test_successful_init(self):
        """Test that a normal 'sat init' calls generate_default_config and prints a success message."""
        do_init(self.sat_init_args)
        self.mock_generate_default_config.assert_called_once_with(
            DEFAULT_CONFIG_PATH, username=self.sat_init_args.username, force=self.sat_init_args.force
        )
        self.mock_print.assert_called_once_with(
            f'Configuration file "{DEFAULT_CONFIG_PATH}" generated.'
        )

    def test_init_already_exists(self):
        """Test that a 'sat init' handles the ConfigFileExistsError correctly."""
        self.mock_generate_default_config.side_effect = ConfigFileExistsError(
            f'Configuration file "{DEFAULT_CONFIG_PATH}" already exists. Not generating configuration file.'
        )
        with self.assertLogs(level=logging.WARNING) as logs:
            do_init(self.sat_init_args)
        self.mock_generate_default_config.assert_called_once_with(
            DEFAULT_CONFIG_PATH, username=self.sat_init_args.username, force=self.sat_init_args.force
        )
        self.mock_print.assert_not_called()
        self.assert_in_element(
            f'Configuration file "{DEFAULT_CONFIG_PATH}" already exists. Not generating configuration file.',
            logs.output
        )

    def test_init_output_option(self):
        """Test that giving the output option generates the config at the specified path."""
        mock_path = '/mock/path.toml'
        self.sat_init_args.output = mock_path
        do_init(self.sat_init_args)
        self.mock_generate_default_config.assert_called_once_with(
            mock_path, username=self.sat_init_args.username, force=self.sat_init_args.force
        )
        self.mock_print.assert_called_once_with(
            f'Configuration file "{mock_path}" generated.'
        )

    def test_init_config_file_environment_variable(self):
        """Test that giving the $SAT_CONFIG_FILE environment variable generates the config at the specified path."""
        mock_path = '/mock/path.toml'
        self.mock_getenv.return_value = mock_path
        do_init(self.sat_init_args)
        self.mock_generate_default_config.assert_called_once_with(
            mock_path, username=self.sat_init_args.username, force=self.sat_init_args.force
        )
        self.mock_print.assert_called_once_with(
            f'Configuration file "{mock_path}" generated.'
        )


if __name__ == '__main__':
    unittest.main()
