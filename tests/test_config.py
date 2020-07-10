"""
Unit tests for sat.config

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
import os
import unittest
from unittest import mock

import sat
from sat.config import ConfigValidationError, DEFAULT_CONFIG_PATH, get_config_value, load_config,\
    SATConfig, SAT_CONFIG_SPEC, validate_log_level, _option_value, OptionSpec, validate_fail_action
from tests.common import ExtendedTestCase

CONFIGS_DIR = os.path.join(os.path.dirname(__file__), 'resources/configs')


class TestValidateLogLevel(unittest.TestCase):
    """Tests for validate_log_level validation function"""

    def test_validate_log_level_valid(self):
        """Test validate_log_level with valid levels"""
        for lvl in ['debug', 'info', 'warning', 'error', 'critical']:
            validate_log_level(lvl)

        # Verify that case doesn't matter
        validate_log_level('dEbUg')

    def test_validate_log_level_invalid(self):
        """Test validate_log_level with invalid level"""
        invalid_level = 'foo'
        expected_msg = "Level '{}' is not one of the valid log levels".format(invalid_level)
        with self.assertRaisesRegex(ConfigValidationError, expected_msg):
            validate_log_level(invalid_level)


class TestValidateFailAction(unittest.TestCase):
    """Tests for validate_fail_action validation function"""

    def test_validate_fail_action_valid(self):
        """Test validate_fail_action with valid actions"""
        for action in ['abort', 'skip', 'prompt', 'force']:
            validate_fail_action(action)

    def test_validate_fail_action_invalid(self):
        """Test validate_fail_action with invalid action"""
        invalid_action = 'foo'
        expected_msg = "Action '{}' is not one of the valid actions".format(invalid_action)
        with self.assertRaisesRegex(ConfigValidationError, expected_msg):
            validate_fail_action(invalid_action)


class TestOptionValue(unittest.TestCase):
    """Test we get the right values from _option_value."""
    def setUp(self):
        self.default = 'some default value...'
        self.cmdline_option = 'cmdline_option'
        self.option_spec = OptionSpec(str, self.default, None, self.cmdline_option)
        self.mock_args = mock.MagicMock()

    def test_callable_default(self):
        """Test the result of a callable default value is the result of the call."""
        mock_default = mock.MagicMock(return_value='this should be default')
        callable_option = OptionSpec(str, mock_default, None, None)
        self.assertEqual('this should be default', _option_value(self.mock_args, None, callable_option))

    def test_no_arg_no_config_file(self):
        """Test we get default without arg or config file option."""
        setattr(self.mock_args, self.cmdline_option, None)
        self.assertEqual(_option_value(self.mock_args, None, self.option_spec),
                         self.default)

    def test_arg_but_no_config_file(self):
        """Test we get command line value with no config file option."""
        cmdline_val = 'some value from the command line...'
        setattr(self.mock_args, self.cmdline_option, cmdline_val)
        self.assertEqual(_option_value(self.mock_args, None, self.option_spec),
                         cmdline_val)

    def test_arg_and_config_file(self):
        """Test we get command line value even with supplied config file option."""
        cmdline_val = 'some value from the command line...'
        setattr(self.mock_args, self.cmdline_option, cmdline_val)
        self.assertEqual(_option_value(self.mock_args, 'value from the config file',
                                       self.option_spec),
                         cmdline_val)

    def test_no_arg_but_config_file(self):
        """Test we get config file value with no command line arg."""
        config_val = 'value from the config file'
        setattr(self.mock_args, self.cmdline_option, None)
        self.assertEqual(_option_value(self.mock_args, config_val, self.option_spec),
                         config_val)

    def test_no_corresponding_arg_config_file(self):
        """Test we get config option with no corresponding command line arg."""
        config_val = 'value from the config file'
        setattr(self.mock_args, self.cmdline_option, 'should have no effect')
        different_option_spec = OptionSpec(str, self.default, None, None)
        self.assertEqual(_option_value(self.mock_args, config_val, different_option_spec),
                         config_val)

    def test_no_corresponding_arg_default(self):
        """Test we get default option with no corresponding command line arg."""
        setattr(self.mock_args, self.cmdline_option, 'should have no effect')
        different_option_spec = OptionSpec(str, self.default, None, None)
        self.assertEqual(_option_value(self.mock_args, None, different_option_spec),
                         self.default)


class TestLoadConfig(unittest.TestCase):
    """Tests for load_config function"""

    def setUp(self):
        """Sets up for test methods.

        Patches SATConfig constructor.
        """
        # Ensure that CONFIG is None to start with a clean slate
        self.backup_config = sat.config.CONFIG
        sat.config.CONFIG = None
        self.mock_sat_config_obj = mock.Mock()
        self.patcher = mock.patch('sat.config.SATConfig',
                                  return_value=self.mock_sat_config_obj)
        self.mock_sat_config_cls = self.patcher.start()

    def tearDown(self):
        """Cleans up after test methods.

        Stops patcher for the SATConfig constructor.
        """
        self.patcher.stop()
        sat.config.CONFIG = self.backup_config

    @mock.patch('os.environ', {k: v for k, v in os.environ.items() if k != 'SAT_CONFIG_FILE'})
    def test_load_config(self):
        """Test load_config with default config path."""
        with mock.patch('sat.config.os.getenv', lambda x, y: DEFAULT_CONFIG_PATH):
            load_config()
            self.mock_sat_config_cls.assert_called_once_with(DEFAULT_CONFIG_PATH, None)
            self.assertEqual(self.mock_sat_config_obj, sat.config.CONFIG)

    def test_load_config_env_var(self):
        """Test load_config with the config file path set in an env var."""
        config_file_path = '/my/custom/config.toml'
        with mock.patch('os.getenv', return_value=config_file_path):
            load_config()
        self.mock_sat_config_cls.assert_called_once_with(config_file_path, None)
        self.assertEqual(self.mock_sat_config_obj, sat.config.CONFIG)

    @mock.patch('sat.config.CONFIG')
    def test_load_config_already_loaded(self, mock_config):
        """Test load_config with CONFIG already loaded."""
        load_config()
        self.mock_sat_config_cls.assert_not_called()
        self.assertEqual(sat.config.CONFIG, mock_config)


class TestGetConfigValue(unittest.TestCase):
    """Tests for the get_config function."""

    @mock.patch('sat.config.CONFIG')
    @mock.patch('sat.config.load_config')
    def test_get_config_value(self, mock_load_config, mock_config):
        option_name = 'foo.bar'
        expected_value = 'expected'
        mock_config.get.return_value = expected_value
        option_value = get_config_value(option_name)
        mock_load_config.assert_called_once_with()
        mock_config.get.assert_called_once_with('foo', 'bar')
        self.assertEqual(expected_value, option_value)


class TestSATConfig(ExtendedTestCase):
    """Tests for the SATConfig class"""

    def assert_defaults_set(self, config):
        """Assert that all options in config are set to defaults.

        Returns:
            None.

        Raises:
            AssertionError: if any assertions fail.
        """
        for section in SAT_CONFIG_SPEC:
            for option_name, option_spec in SAT_CONFIG_SPEC[section].items():
                self.assertEqual(
                    config.get(section, option_name),
                    option_spec.default() if callable(option_spec.default) else option_spec.default)

    def test_valid_config(self):
        """Test creating a SATConfig from a valid config file."""
        config = SATConfig(os.path.join(CONFIGS_DIR, 'valid.toml'))
        self.assertEqual(config.get('logging', 'file_name'),
                         '/var/log/sat.log')
        self.assertEqual(config.get('logging', 'file_level'),
                         'DEBUG')
        self.assertEqual(config.get('logging', 'stderr_level'),
                         'ERROR')

    def test_invalid_log_levels(self):
        """Test creating a SATConfig from a config file w/ invalid option vals

        Currently, this is just invalid log levels.
        """
        with self.assertLogs(level='ERROR') as cm:
            config = SATConfig(os.path.join(CONFIGS_DIR, 'invalid_levels.toml'))

        msg_template = "Invalid value '{}' given for option '{}' in section 'logging'"
        file_err_msg = msg_template.format('BLAH', 'file_level')
        stderr_err_msg = msg_template.format('WHATEVA', 'stderr_level')

        self.assert_in_element(file_err_msg, cm.output)
        self.assert_in_element(stderr_err_msg, cm.output)

        self.assert_defaults_set(config)

    def test_unknown_sections(self):
        """Test creating a SATConfig from a config file w/ unknown sections."""
        with self.assertLogs(level='WARNING') as cm:
            config = SATConfig(os.path.join(CONFIGS_DIR, 'unknown_sections.toml'))

        unknown_section_template = "Ignoring unknown section '{}' in config file."

        self.assertEqual(len(cm.output), 2)
        for section in ['unknown', 'another_unknown']:
            self.assert_in_element(unknown_section_template.format(section), cm.output)

        self.assert_defaults_set(config)

    def test_unknown_options(self):
        """Test creating a SATConfig from a config file w/ unknown options."""
        with self.assertLogs(level='WARNING') as cm:
            config = SATConfig(os.path.join(CONFIGS_DIR, 'unknown_options.toml'))

        unknown_option_template = ("Ignoring unknown option '{}' in section 'general' "
                                   "of config file.")

        self.assertEqual(len(cm.output), 2)
        for option in ['unknown', 'another_unknown']:
            self.assert_in_element(unknown_option_template.format(option), cm.output)

        self.assert_defaults_set(config)

    def test_empty_file(self):
        """Test creating a SATConfig from an empty config file."""
        config = SATConfig(os.path.join(CONFIGS_DIR, 'empty.toml'))
        self.assert_defaults_set(config)

    def test_nonexistent_file(self):
        """Test creating a SATConfig from a non-existent file."""
        file_name = 'does_not_exist.toml'
        with self.assertLogs(level='ERROR') as cm:
            config = SATConfig(file_name)

        expected_err_msg = ("Unable to read config file at '{}'. "
                            "Using default configuration values.").format(file_name)
        self.assert_in_element(expected_err_msg, cm.output)

        self.assert_defaults_set(config)


if __name__ == '__main__':
    unittest.main()
