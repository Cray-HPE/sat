#
# MIT License
#
# (C) Copyright 2019-2022, 2024 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.config
"""

from collections import OrderedDict
import os
from textwrap import dedent
import unittest
from unittest import mock

import sat
from sat.config import (
    ConfigFileExistsError,
    ConfigValidationError,
    DEFAULT_CONFIG_PATH,
    OptionSpec,
    SATConfig,
    SAT_CONFIG_SPEC,
    _option_value,
    generate_default_config,
    get_config_value,
    load_config,
    read_config_value_file,
    validate_bos_api_version,
    validate_cfs_api_version,
    validate_log_level
)
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


class TestValidateBosApiVersion(unittest.TestCase):
    """Tests for validate_bos_api_version function"""

    def test_validate_bos_api_version_v1(self):
        """Test that "v1" is a valid BOS API version"""
        validate_bos_api_version('v1')

    def test_validate_invalid_bos_api_version(self):
        """Test that invalid BOS versions are not allowed"""
        for version in ['v3', 'foo', '', '1', '2']:
            with self.subTest(version=version):
                with self.assertRaises(ConfigValidationError):
                    validate_bos_api_version(version)


class TestValidateCfsApiVersion(unittest.TestCase):
    """Tests for validate_cfs_api_version function"""

    def test_validate_cfs_api_version_v2(self):
        """Test that "v2" is a valid CFS API version"""
        validate_cfs_api_version('v2')

    def test_validate_invalid_cfs_api_version(self):
        """Test that invalid CFS versions are not allowed"""
        for version in ['v5', 'foo', '', '1', '2']:
            with self.subTest(version=version):
                with self.assertRaises(ConfigValidationError):
                    validate_cfs_api_version(version)


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


class TestGenerateDefaultConfig(unittest.TestCase):
    """Tests for the generate_default_config function"""

    def setUp(self):
        """Sets up mocks for testing generate_default_config."""
        # Use an OrderedDict to enforce ordering of settings
        self.fake_config_spec = {
            'api_gateway': OrderedDict([
                ('username', OptionSpec(str, lambda x: 'sat_user', None, None)),
                ('favorite_color', OptionSpec(str, 'red', None, None))
            ])
        }
        mock.patch('sat.config.SAT_CONFIG_SPEC', self.fake_config_spec).start()
        self.mock_open = mock.patch('builtins.open').start()
        self.mock_fchmod = mock.patch('sat.config.os.fchmod').start()
        self.mock_output_stream = self.mock_open.return_value
        self.mock_isdir = mock.patch('sat.config.os.path.isdir', return_value=True).start()
        self.mock_isfile = mock.patch('sat.config.os.path.isfile', return_value=False).start()
        self.mock_makedirs = mock.patch('sat.config.os.makedirs').start()

        self.expected_config = dedent("""\
        # Default configuration file for SAT.
        # (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP.

        # Permission is hereby granted, free of charge, to any person obtaining a
        # copy of this software and associated documentation files (the "Software"),
        # to deal in the Software without restriction, including without limitation
        # the rights to use, copy, modify, merge, publish, distribute, sublicense,
        # and/or sell copies of the Software, and to permit persons to whom the
        # Software is furnished to do so, subject to the following conditions:

        # The above copyright notice and this permission notice shall be included
        # in all copies or substantial portions of the Software.

        # THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
        # IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
        # FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
        # THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
        # OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
        # ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
        # OTHER DEALINGS IN THE SOFTWARE.

        [api_gateway]
        # username = ""
        # favorite_color = "red"
        """)

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_basic_config_generation(self):
        """Test basic default config generation"""
        generate_default_config(DEFAULT_CONFIG_PATH)
        self.mock_open.assert_called_with(DEFAULT_CONFIG_PATH, 'w')
        self.mock_output_stream.write.assert_called_once_with(self.expected_config)
        self.mock_fchmod.assert_called_once_with(self.mock_output_stream.fileno.return_value, 0o600)
        self.mock_makedirs.assert_not_called()

    def test_generate_alternate_location(self):
        """Test generate_default_config() can write to any given path"""
        generate_default_config('/mock/path.toml')
        self.mock_open.assert_called_once_with('/mock/path.toml', 'w')
        self.mock_output_stream.write.assert_called_once_with(self.expected_config)
        self.mock_fchmod.assert_called_once_with(self.mock_output_stream.fileno.return_value, 0o600)
        self.mock_makedirs.assert_not_called()

    def test_generate_create_directory(self):
        """Test generate_default_config() will create a config directory if needed"""
        self.mock_isdir.return_value = False
        generate_default_config('/etc/opt/cray/sat.toml')
        self.mock_open.assert_called_once_with('/etc/opt/cray/sat.toml', 'w')
        self.mock_output_stream.write.assert_called_once_with(self.expected_config)
        self.mock_fchmod.assert_called_once_with(self.mock_output_stream.fileno.return_value, 0o600)
        self.mock_makedirs.assert_called_once_with('/etc/opt/cray', mode=0o700, exist_ok=True)

    def test_generate_in_current_directory(self):
        """Test generate_default_config() will not create a directory when not needed"""
        self.mock_isdir.return_value = False
        generate_default_config('local.toml')
        self.mock_open.assert_called_once_with('local.toml', 'w')
        self.mock_output_stream.write.assert_called_once_with(self.expected_config)
        self.mock_makedirs.assert_not_called()
        self.mock_fchmod.assert_called_once_with(self.mock_output_stream.fileno.return_value, 0o600)

    def test_generate_with_username(self):
        """Test generating config with a username will write a config file with a username"""
        self.expected_config = self.expected_config.replace('# username = ""', 'username = "sat_user"')
        generate_default_config(DEFAULT_CONFIG_PATH, username='sat_user')
        self.mock_open.assert_called_with(DEFAULT_CONFIG_PATH, 'w')
        self.mock_output_stream.write.assert_called_once_with(self.expected_config)
        self.mock_fchmod.assert_called_once_with(self.mock_output_stream.fileno.return_value, 0o600)
        self.mock_makedirs.assert_not_called()

    def test_generate_file_exists(self):
        """Test generating a config file when the file exists will not overwrite and raises ConfigFileExistsError."""
        self.mock_isfile.return_value = True
        with self.assertRaisesRegex(
                ConfigFileExistsError,
                f'Configuration file "{DEFAULT_CONFIG_PATH}" already exists. Not generating configuration file.'
        ):
            generate_default_config(DEFAULT_CONFIG_PATH)
        self.mock_open.assert_not_called()
        self.mock_output_stream.write.assert_not_called()
        self.mock_fchmod.assert_not_called()
        self.mock_makedirs.assert_not_called()

    def test_generate_file_exists_force(self):
        """Test generating a config file when the file exists will overwrite if forcing"""
        self.mock_isfile.return_value = True
        generate_default_config(DEFAULT_CONFIG_PATH, force=True)
        self.mock_open.assert_called_with(DEFAULT_CONFIG_PATH, 'w')
        self.mock_output_stream.write.assert_called_once_with(self.expected_config)
        self.mock_fchmod.assert_called_once_with(self.mock_output_stream.fileno.return_value, 0o600)
        self.mock_makedirs.assert_not_called()


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
        """Test a basic call of get_config_value"""
        option_name = 'foo.bar'
        expected_value = 'expected'
        mock_config.get.return_value = expected_value
        option_value = get_config_value(option_name)
        mock_load_config.assert_called_once_with()
        mock_config.get.assert_called_once_with('foo', 'bar')
        self.assertEqual(expected_value, option_value)


class TestGetConfigValueFromFile(unittest.TestCase):

    def setUp(self):
        """Sets up for test methods.

        Patches open, os.path.expanduser, and config.get_config_value.
        """
        self.mock_expanduser = mock.patch('sat.config.os.path.expanduser').start()
        self.mock_open = mock.patch('builtins.open').start()
        self.mock_get_config_value = mock.patch('sat.config.get_config_value').start()

    def tearDown(self):
        """Cleans up after test methods.

        Stop patch of open, os.path.expanduser, and config.get_config_value.
        """
        mock.patch.stopall()

    def test_get_config_value_from_file(self):
        """Test a basic call of get_config_value_from_file"""
        option_name = 'foo.bar'
        expected_value = 'expected'
        self.mock_open.return_value.__enter__.return_value.read.return_value = f'{expected_value}\n'
        actual_value = read_config_value_file(option_name)
        self.mock_get_config_value.assert_called_once_with(option_name)
        self.mock_expanduser.assert_called_once_with(self.mock_get_config_value.return_value)
        self.mock_open.assert_called_once_with(self.mock_expanduser.return_value)
        self.assertEqual(expected_value, actual_value)


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
