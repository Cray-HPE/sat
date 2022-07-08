#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
Unit tests for main bootprep module
"""
from argparse import Namespace
import logging
import unittest
from unittest.mock import MagicMock, patch

from sat.cli.bootprep.errors import (
    BootPrepInternalError,
    BootPrepDocsError,
    BootPrepValidationError,
    ConfigurationCreateError,
    ImageCreateError,
    ValidationErrorCollection
)
from sat.cli.bootprep.main import (
    do_bootprep,
    do_bootprep_run,
    do_bootprep_docs,
    do_bootprep_schema
)
from sat.cli.bootprep.validate import SCHEMA_FILE_RELATIVE_PATH


class TestDoBootprepDocs(unittest.TestCase):
    """Tests for the do_bootprep_docs function."""
    def setUp(self):
        """Mock functions called by do_bootprep_docs"""
        self.mock_resource_path = patch('sat.cli.bootprep.main.resource_absolute_path').start()
        self.mock_generate_docs_tarball = patch('sat.cli.bootprep.main.generate_docs_tarball').start()
        self.args = Namespace(output_dir='./output/')

    def tearDown(self):
        patch.stopall()

    def test_do_bootprep_docs_success(self):
        """Test a successful call to do_bootprep_docs."""
        do_bootprep_docs(self.args)
        self.mock_resource_path.assert_called_once_with(SCHEMA_FILE_RELATIVE_PATH)
        self.mock_generate_docs_tarball.assert_called_once_with(
            self.mock_resource_path.return_value, self.args.output_dir
        )

    def test_do_bootprep_docs_failure(self):
        """Test a failed call to do_bootprep_docs when generating documentation fails."""
        self.mock_generate_docs_tarball.side_effect = BootPrepDocsError('docs failed')
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep_docs(self.args)
        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))


class TestDoBootprepSchema(unittest.TestCase):
    """Tests for the do_bootprep_schema function."""

    def setUp(self):
        """Mock functions called by do_bootprep_schema"""
        self.mock_schema_file = MagicMock()
        self.mock_display_schema = patch('sat.cli.bootprep.main.display_schema').start()

    def tearDown(self):
        patch.stopall()

    def test_do_bootprep_schema_success(self):
        """Test a successful call to do_bootprep_schema."""
        do_bootprep_schema(self.mock_schema_file)
        self.mock_display_schema.assert_called_once_with(self.mock_schema_file)

    def test_do_bootprep_schema_failure(self):
        """Test a failed call to do_bootprep_schema when generating documentation fails."""
        self.mock_display_schema.side_effect = BootPrepDocsError('could not display')
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep_schema(self.mock_schema_file)
        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))


class TestDoBootprepRun(unittest.TestCase):
    """Tests for the do_bootprep_run function."""

    def setUp(self):
        """Mock functions called by do_bootprep_run"""
        self.input_file = 'input.yaml'
        self.overwrite_templates = False
        self.skip_existing_templates = False
        self.dry_run = False
        self.args = Namespace(action='run', input_file=self.input_file,
                              overwrite_templates=self.overwrite_templates,
                              skip_existing_templates=self.skip_existing_templates, dry_run=self.dry_run,
                              view_input_schema=False, generate_schema_docs=False,
                              bos_version='v1', recipe_version=None, vars_file=None, vars=None)
        self.schema_file = 'schema.yaml'
        self.mock_validator_cls = MagicMock()
        self.mock_load_and_validate_instance = patch('sat.cli.bootprep.main.load_and_validate_instance').start()
        self.validated_data = self.mock_load_and_validate_instance.return_value
        self.mock_input_instance_cls = patch('sat.cli.bootprep.main.InputInstance').start()
        self.mock_input_instance = self.mock_input_instance_cls.return_value
        self.mock_sat_session = patch('sat.cli.bootprep.main.SATSession').start()
        self.mock_cfs_client = patch('sat.cli.bootprep.main.CFSClient').start().return_value
        self.mock_ims_client = patch('sat.cli.bootprep.main.IMSClient').start().return_value
        self.mock_bos_client = patch('sat.cli.bootprep.main.BOSClientCommon.get_bos_client').start().return_value
        self.mock_create_configurations = patch('sat.cli.bootprep.main.create_configurations').start()
        self.mock_create_images = patch('sat.cli.bootprep.main.create_images').start()
        self.mock_session_templates = self.mock_input_instance.input_session_templates
        self.mock_product_catalog_cls = patch('sat.cli.bootprep.main.ProductCatalog').start()
        self.mock_product_catalog = self.mock_product_catalog_cls.return_value
        self.mock_variable_context_cls = patch('sat.cli.bootprep.main.VariableContext').start()
        self.mock_variable_context = self.mock_variable_context_cls.return_value
        self.mock_variable_context.vars = {}
        self.mock_request_dumper = patch('sat.cli.bootprep.main.RequestDumper').start()

    def tearDown(self):
        patch.stopall()

    def test_do_bootprep_run_success(self):
        """Test do_bootprep_run in the successful case"""
        with self.assertLogs(level=logging.INFO) as cm:
            do_bootprep_run(self.mock_validator_cls, self.args)

        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)
        self.mock_input_instance_cls.assert_called_once_with(
            self.validated_data, self.mock_cfs_client, self.mock_ims_client,
            self.mock_bos_client, self.mock_variable_context, self.mock_product_catalog)
        self.mock_create_configurations.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_create_images.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_session_templates.handle_existing_items.assert_called_once_with(
            self.overwrite_templates, self.skip_existing_templates, self.dry_run
        )
        self.mock_session_templates.validate.assert_called_once_with(dry_run=self.dry_run)
        self.mock_session_templates.create_items.assert_called_once_with(
            dumper=self.mock_request_dumper.return_value)
        info_msgs = [r.msg for r in cm.records]
        expected_msgs = [
            f'Validating given input file {self.input_file}',
            'Input file successfully validated against schema'
        ]
        self.assertEqual(expected_msgs, info_msgs)

    def test_do_bootprep_run_validation_error(self):
        """Test do_bootprep_run when an error occurs loading the input file"""
        validation_err_msg = 'failed to load instance'
        self.mock_load_and_validate_instance.side_effect = BootPrepValidationError(validation_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep_run(self.mock_validator_cls, self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(validation_err_msg, logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)

    def test_do_bootprep_run_validation_error_collection(self):
        """Test do_bootprep_run when an error occurs validating the input against the schema"""
        self.mock_load_and_validate_instance.side_effect = ValidationErrorCollection([])
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep_run(self.mock_validator_cls, self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual('Input file is invalid with the following validation errors:\n',
                         logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)

    def test_do_bootprep_run_configuration_create_error(self):
        """Test do_bootprep_run when an error occurs creating a configuration"""
        create_err_msg = 'Failed to create a configuration'
        self.mock_create_configurations.side_effect = ConfigurationCreateError(create_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep_run(self.mock_validator_cls, self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(create_err_msg, logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)
        self.mock_input_instance_cls.assert_called_once_with(
            self.validated_data, self.mock_cfs_client, self.mock_ims_client,
            self.mock_bos_client, self.mock_variable_context, self.mock_product_catalog)
        self.mock_create_configurations.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_create_images.assert_not_called()
        self.mock_session_templates.handle_existing_items.assert_not_called()
        self.mock_session_templates.validate.assert_not_called()
        self.mock_session_templates.create_items.assert_not_called()

    def test_do_bootprep_run_image_create_error(self):
        """Test do_bootprep_run when an error occurs creating an image"""
        create_err_msg = 'Failed to create an image'
        self.mock_create_images.side_effect = ImageCreateError(create_err_msg)
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep_run(self.mock_validator_cls, self.args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(create_err_msg, logs_cm.records[0].msg)
        self.mock_load_and_validate_instance.assert_called_once_with(
            self.input_file, self.mock_validator_cls)
        self.mock_input_instance_cls.assert_called_once_with(
            self.validated_data, self.mock_cfs_client, self.mock_ims_client,
            self.mock_bos_client, self.mock_variable_context, self.mock_product_catalog)
        self.mock_create_configurations.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_create_images.assert_called_once_with(self.mock_input_instance, self.args)
        self.mock_session_templates.handle_existing_items.assert_not_called()
        self.mock_session_templates.validate.assert_not_called()
        self.mock_session_templates.create_items.assert_not_called()


class TestDoBootprep(unittest.TestCase):
    """Tests for the do_bootprep function."""

    def setUp(self):
        """Mock functions called by do_bootprep."""
        self.args = Namespace()
        self.mock_do_bootprep_docs = patch('sat.cli.bootprep.main.do_bootprep_docs').start()
        self.mock_do_bootprep_example = patch('sat.cli.bootprep.main.do_bootprep_example').start()
        self.mock_do_bootprep_run = patch('sat.cli.bootprep.main.do_bootprep_run').start()
        self.mock_do_bootprep_schema = patch('sat.cli.bootprep.main.do_bootprep_schema').start()
        self.mock_validator_cls = MagicMock()
        self.mock_schema_file = MagicMock()
        self.mock_load_and_validate_schema = patch(
            'sat.cli.bootprep.main.load_and_validate_schema',
            return_value=(self.mock_schema_file, self.mock_validator_cls)).start()
        self.mock_ensure_output_directory = patch('sat.cli.bootprep.main.ensure_output_directory').start()

    def tearDown(self):
        patch.stopall()

    def test_do_bootprep_run(self):
        """Test the run action calls do_bootprep_run."""
        self.args.action = 'run'
        do_bootprep(self.args)
        self.mock_do_bootprep_run.assert_called_once_with(self.mock_validator_cls, self.args)

    def test_do_bootprep_example(self):
        """Test the generate-example action calls do_bootprep_example."""
        self.args.action = 'generate-example'
        do_bootprep(self.args)
        self.mock_do_bootprep_example.assert_called_once_with(self.mock_validator_cls, self.args)

    def test_do_bootprep_generate_docs(self):
        """Test the generate-docs action calls do_bootprep_docs."""
        self.args.action = 'generate-docs'
        do_bootprep(self.args)
        self.mock_do_bootprep_docs.assert_called_once_with(self.args)

    def test_do_bootprep_view_schema(self):
        """Test the view-schema action calls do_bootprep_schema."""
        self.args.action = 'view-schema'
        do_bootprep(self.args)
        self.mock_do_bootprep_schema.assert_called_once_with(self.mock_schema_file)

    def test_do_bootprep_bad_schema(self):
        """Test a failed call to do_bootprep when the schema is not valid."""
        self.mock_load_and_validate_schema.side_effect = BootPrepInternalError('bad schema')
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.ERROR) as logs_cm:
                do_bootprep(self.args)
        self.assertEqual(1, raises_cm.exception.code)
        self.assertEqual(1, len(logs_cm.records))


if __name__ == '__main__':
    unittest.main()
