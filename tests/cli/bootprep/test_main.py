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
from unittest.mock import MagicMock, patch

from sat.cli.bootprep.errors import (
    BootPrepInternalError,
    BootPrepValidationError,
    ConfigurationCreateError,
    ImageCreateError,
    ValidationErrorCollection
)
from sat.cli.bootprep.main import do_bootprep


class TestDoBootprep(unittest.TestCase):
    """Tests for the do_bootprep function."""

    def setUp(self):
        """Mock functions called by do_bootprep"""
        self.input_file = 'input.yaml'
        self.overwrite_templates = False
        self.skip_existing_templates = False
        self.dry_run = False
        self.args = Namespace(input_file=self.input_file, overwrite_templates=self.overwrite_templates,
                              skip_existing_templates=self.skip_existing_templates, dry_run=self.dry_run,
                              view_input_schema=False, generate_schema_docs=False)
        self.schema_file = 'schema.yaml'
        self.mock_validator_cls = MagicMock()
        self.mock_load_and_validate_schema = patch('sat.cli.bootprep.main.load_and_validate_schema',
                                                   return_value=(self.schema_file, self.mock_validator_cls)).start()
        self.mock_load_and_validate_instance = patch('sat.cli.bootprep.main.load_and_validate_instance').start()
        self.validated_data = self.mock_load_and_validate_instance.return_value
        self.mock_input_instance_cls = patch('sat.cli.bootprep.main.InputInstance').start()
        self.mock_input_instance = self.mock_input_instance_cls.return_value
        self.mock_sat_session = patch('sat.cli.bootprep.main.SATSession').start()
        self.mock_cfs_client = patch('sat.cli.bootprep.main.CFSClient').start().return_value
        self.mock_ims_client = patch('sat.cli.bootprep.main.IMSClient').start().return_value
        self.mock_bos_client = patch('sat.cli.bootprep.main.BOSClient').start().return_value
        self.mock_create_configurations = patch('sat.cli.bootprep.main.create_configurations').start()
        self.mock_create_images = patch('sat.cli.bootprep.main.create_images').start()
        self.mock_session_templates = self.mock_input_instance.input_session_templates

    def tearDown(self):
        patch.stopall()

    def test_do_bootprep_success(self):
        """Test do_bootprep in the successful case"""
        with self.assertLogs(level=logging.INFO) as cm:
            do_bootprep(self.args)

        self.mock_load_and_validate_schema.assert_called_once_with()
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)
        self.mock_input_instance_cls.assert_called_once_with(
            self.validated_data, self.mock_cfs_client, self.mock_ims_client, self.mock_bos_client)
        self.mock_create_configurations.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_create_images.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_session_templates.handle_existing_items.assert_called_once_with(
            self.overwrite_templates, self.skip_existing_templates, self.dry_run
        )
        self.mock_session_templates.validate.assert_called_once_with(dry_run=self.dry_run)
        self.mock_session_templates.create_items.assert_called_once_with()
        info_msgs = [r.msg for r in cm.records]
        expected_msgs = [
            'Loading schema file',
            f'Validating given input file {self.input_file}',
            'Input file successfully validated against schema'
        ]
        self.assertEqual(expected_msgs, info_msgs)

    def test_do_bootprep_schema_error(self):
        """Test do_bootprep when an error occurs validating the schema itself"""
        internal_err_msg = 'bad schema'
        self.mock_load_and_validate_schema.side_effect = BootPrepInternalError(internal_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Internal error while loading schema: {internal_err_msg}',
                         logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_not_called()

    def test_do_bootprep_validation_error(self):
        """Test do_bootprep when an error occurs loading the input file"""
        validation_err_msg = 'failed to load instance'
        self.mock_load_and_validate_instance.side_effect = BootPrepValidationError(validation_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(validation_err_msg, logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)

    def test_do_bootprep_validation_error_collection(self):
        """Test do_bootprep when an error occurs validating the input against the schema"""
        self.mock_load_and_validate_instance.side_effect = ValidationErrorCollection([])
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual('Input file is invalid with the following validation errors:\n',
                         logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)

    def test_do_bootprep_configuration_create_error(self):
        """Test do_bootprep when an error occurs creating a configuration"""
        create_err_msg = 'Failed to create a configuration'
        self.mock_create_configurations.side_effect = ConfigurationCreateError(create_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(create_err_msg, logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)
        self.mock_input_instance_cls.assert_called_once_with(
            self.validated_data, self.mock_cfs_client, self.mock_ims_client, self.mock_bos_client)
        self.mock_create_configurations.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_create_images.assert_not_called()
        self.mock_session_templates.handle_existing_items.assert_not_called()
        self.mock_session_templates.validate.assert_not_called()
        self.mock_session_templates.create_items.assert_not_called()

    def test_do_bootprep_image_create_error(self):
        """Test do_bootprep when an error occurs creating an image"""
        create_err_msg = 'Failed to create an image'
        self.mock_create_images.side_effect = ImageCreateError(create_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(create_err_msg, logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)
        self.mock_input_instance_cls.assert_called_once_with(
            self.validated_data, self.mock_cfs_client, self.mock_ims_client, self.mock_bos_client)
        self.mock_create_configurations.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_create_images.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_session_templates.handle_existing_items.assert_not_called()
        self.mock_session_templates.validate.assert_not_called()
        self.mock_session_templates.create_items.assert_not_called()


if __name__ == '__main__':
    unittest.main()
