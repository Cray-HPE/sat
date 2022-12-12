#
# MIT License
#
# (C) Copyright 2022-2023 Hewlett Packard Enterprise Development LP
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
Tests for sat.cli.bootprep.output
"""

from argparse import Namespace
import unittest
from unittest.mock import patch

from sat.cli.bootprep.output import ensure_output_directory, RequestDumper


class TestEnsureOutputDirectory(unittest.TestCase):
    """Tests for the ensure_output_directory() function"""
    def setUp(self):
        self.args = Namespace(
            action='run',
            output_dir='.',
            save_files=True
        )
        self.mock_makedirs = patch('sat.cli.bootprep.output.os.makedirs').start()

    def tearDown(self):
        patch.stopall()

    def test_dont_make_directory_when_no_save_files(self):
        """Test that directories are not created when --save-files not specified"""
        self.args.save_files = False
        ensure_output_directory(self.args)
        self.mock_makedirs.assert_not_called()

    def test_output_dir_is_cwd(self):
        """Test ensure_output_directory() when the output dir is '.'"""
        ensure_output_directory(self.args)
        self.mock_makedirs.assert_not_called()

    def test_output_dir_is_other(self):
        """Test ensure_output_directory() when the output dir is an arbitrary directory"""
        output_dir = '/some/path/to/somewhere'
        self.args.output_dir = output_dir
        ensure_output_directory(self.args)
        self.mock_makedirs.assert_called_once_with(output_dir, exist_ok=True)

    def test_output_dir_created_in_generate_actions(self):
        """Test ensure_output_directory() when the actions is generating output"""
        for action in ['generate-docs', 'generate-example']:
            with self.subTest(action=action):
                output_dir = f'/some/path/to/{action}/'
                self.args.output_dir = output_dir
                self.args.action = action
                ensure_output_directory(self.args)
                self.mock_makedirs.assert_called_with(output_dir, exist_ok=True)

    def test_exit_on_ensure_dir_fail(self):
        """Test that ensure_output_directory() exits the program if there's a problem"""
        self.args.output_dir = '/some/output/path'
        self.mock_makedirs.side_effect = OSError
        with self.assertRaises(SystemExit):
            ensure_output_directory(self.args)


class TestRequestDumper(unittest.TestCase):
    """Tests for the RequestDumper class"""
    def setUp(self):
        self.args = Namespace(
            action='run',
            output_dir='.',
            save_files=True
        )

        self.mock_open = patch('builtins.open').start()
        self.mocked_file = self.mock_open.return_value.__enter__.return_value
        self.mock_json_dump = patch('sat.cli.bootprep.output.json.dump').start()

        self.request_body = {
            'some attribute': 'some content',
            'other attribute': {'more content': 'something else'}
        }
        self.request_type = 'test request'
        self.item_name = 'test item 1'

    def tearDown(self):
        patch.stopall()

    def test_writing_request_body(self):
        """Test that request bodies are written to output files"""
        dumper = RequestDumper(self.args.save_files, self.args.output_dir)
        dumper.write_request_body(self.request_type, self.item_name, self.request_body)
        self.mock_open.assert_called_once_with(
            dumper.get_filename_for_request(self.request_type, self.item_name), 'w'
        )
        self.mock_json_dump.assert_called_once_with(
            self.request_body,
            self.mocked_file,
            **dumper.json_params
        )

    def test_writing_request_body_when_not_saving_files(self):
        """Test that requests are not written when --save-files not used"""
        self.args.save_files = False
        dumper = RequestDumper(self.args.save_files, self.args.output_dir)
        dumper.write_request_body(self.request_type, self.item_name, self.request_body)
        self.mock_open.assert_not_called()
        self.mock_json_dump.assert_not_called()

    def test_warning_logged_on_req_write_failure(self):
        """Test that a warning is logged if the request cannot be written"""
        self.mock_open.side_effect = OSError
        dumper = RequestDumper(self.args.save_files, self.args.output_dir)
        with self.assertLogs(level='WARNING'):
            dumper.write_request_body(self.request_type, self.item_name, self.request_body)

    def test_arbitrary_json_format_params(self):
        """Test that arbitrary json formatting parameters can be used"""
        json_params = {'indent': 2, 'allow_nan': False}
        dumper = RequestDumper(self.args.save_files, self.args.output_dir, json_params=json_params)
        dumper.write_request_body(self.request_type, self.item_name, self.request_body)
        self.mock_json_dump.assert_called_once_with(
            self.request_body,
            self.mocked_file,
            **json_params
        )
