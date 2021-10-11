"""
Unit tests for main bootprep module

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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
from argparse import Namespace
import logging
import unittest
from unittest.mock import patch

from sat.cli.bootprep.errors import (
    BootPrepInternalError,
    BootPrepValidationError,
    ValidationErrorCollection
)
from sat.cli.bootprep.main import do_bootprep


class TestDoBootprep(unittest.TestCase):
    """Tests for the do_bootprep function."""

    def setUp(self):
        """Mock functions called by do_bootprep"""
        self.input_file = 'input.yaml'
        self.args = Namespace(input_file=self.input_file)
        self.mock_load_bootprep_schema = patch('sat.cli.bootprep.main.load_bootprep_schema').start()
        self.mock_load_and_validate = patch('sat.cli.bootprep.main.load_and_validate_instance').start()
        self.validated_instance = self.mock_load_and_validate.return_value
        self.mock_create_configurations = patch('sat.cli.bootprep.main.create_configurations').start()

    def tearDown(self):
        patch.stopall()

    def test_do_bootprep_success(self):
        """Test do_bootprep in the successful case"""
        with self.assertLogs(level=logging.INFO) as cm:
            do_bootprep(self.args)

        self.mock_load_bootprep_schema.assert_called_once_with()
        self.mock_load_and_validate.assert_called_once_with(
            self.input_file, self.mock_load_bootprep_schema.return_value)
        self.mock_create_configurations.assert_called_once_with(self.validated_instance, self.args)
        info_msgs = [r.msg for r in cm.records]
        expected_msgs = [
            'Loading schema file',
            f'Validating given input file {self.input_file}',
            'Input file successfully validated'
        ]
        self.assertEqual(expected_msgs, info_msgs)

    def test_do_bootprep_schema_error(self):
        """Test do_bootprep when an error occurs validating the schema itself"""
        internal_err_msg = 'bad schema'
        self.mock_load_bootprep_schema.side_effect = BootPrepInternalError(internal_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        error_msgs = [r.msg for r in logs_cm.records if r.levelno == logging.ERROR]
        self.assertEqual([f'Internal error while loading schema: {internal_err_msg}'],
                         error_msgs)
        self.mock_load_and_validate.assert_not_called()

    def test_do_bootprep_validation_error(self):
        """Test do_bootprep when an error occurs loading the input file"""
        validation_err_msg = 'failed to load instance'
        self.mock_load_and_validate.side_effect = BootPrepValidationError(validation_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        error_msgs = [r.msg for r in logs_cm.records if r.levelno == logging.ERROR]
        self.assertEqual([validation_err_msg], error_msgs)
        self.mock_load_and_validate.assert_called_once_with(
            self.input_file, self.mock_load_bootprep_schema.return_value)

    def test_do_bootprep_validation_error_collection(self):
        """Test do_bootprep when an error occurs validating the input against the schema"""
        self.mock_load_and_validate.side_effect = ValidationErrorCollection([])
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        error_msgs = [r.msg for r in logs_cm.records if r.levelno == logging.ERROR]
        self.assertEqual(['Input file is invalid with the following validation errors:\n'],
                         error_msgs)
        self.mock_load_and_validate.assert_called_once_with(
            self.input_file, self.mock_load_bootprep_schema.return_value)


if __name__ == '__main__':
    unittest.main()
