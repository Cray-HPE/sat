"""
Loads configuration from a config file in INI format.
Copyright 2019 Cray Inc. All Rights Reserved
"""

from collections import namedtuple
import getpass
import logging
import os

import toml

DEFAULT_CONFIG_PATH = '/etc/sat.toml'
LOGGER = logging.getLogger(__name__)
CONFIG = None

OptionSpec = namedtuple('OptionSpec', ['type', 'default', 'validation_func', 'cmdline_arg'])


class ConfigValidationError(Exception):
    """An error occurred during validation of configuration."""
    pass


def validate_log_level(level):
    """Validates the given log level.

    Args:
        level (str): The log level string to validate.

    Returns:
        None

    Raises:
        ConfigValidationError: If the given `level` is not valid.
    """
    valid_log_levels = ['CRITICAL', 'ERROR', 'WARNING', 'INFO', 'DEBUG']
    if level.upper() not in valid_log_levels:
        raise ConfigValidationError(
            "Level '{}' is not one of the valid log levels: {}".format(
                level, ", ".join(valid_log_levels)
            )
        )


SAT_CONFIG_SPEC = {
    'api_gateway': {
        'host': OptionSpec(str, 'api-gw-service-nmn.local', None, None),
        'cert_verify': OptionSpec(bool, True, None, None),
        'username': OptionSpec(str, getpass.getuser, None, 'username'),
        'token_file': OptionSpec(str, '', None, 'token_file'),
    },
    'format': {
        'no_headings': OptionSpec(bool, False, None, 'no_headings'),
        'no_borders': OptionSpec(bool, False, None, 'no_borders'),
        'show_empty': OptionSpec(bool, False, None, 'show_empty'),
        'show_missing': OptionSpec(bool, False, None, 'show_missing'),
    },
    'general': {
        'site_info': OptionSpec(str, '/opt/cray/etc/site_info.yml', None, None),
    },
    'logging': {
        'file_name': OptionSpec(str, '/var/log/cray/sat.log', None, 'logfile'),
        'file_level': OptionSpec(str, 'INFO', validate_log_level, 'loglevel'),
        'stderr_level': OptionSpec(str, 'WARNING', validate_log_level, 'loglevel'),
    },
    'redfish': {
        'username': OptionSpec(str, '', None, None),
        'password': OptionSpec(str, '', None, None)
    },
}


def _option_value(args, curr, spec):
    """Determine the value of an option.

    There is a hierarchy of importance when determining what the value of an
    option should be. First, if an argument is set on the command line, that
    value should be used. Second, if the value is set in the configuration file,
    but not on the command line, that value should be used. Third, if the value
    is supplied neither on the command line nor in the configuration file, then
    the OptionSpec default value is used.

    The default value may be a callable object. If so, then it is called with no
    arguments, and the result is used as the default value. This allows build-
    time introspection to set such options to empty, as the results would likely
    be meaningless.

    Args:
        args: a Namespace from an ArgumentParser.
        curr: the current value (or None if not set) of some option.
        spec: an OptionSpec for the option.
    """

    if spec.cmdline_arg:
        # Override with command-line value if specified
        args_value = getattr(args, spec.cmdline_arg, None)
        if args_value is not None:
            return args_value

    default = spec.default() if callable(spec.default) else spec.default

    return default if curr is None else curr


class SATConfig:
    """A class representing the configuration of the SAT program.

    This class is responsible for loading the configuration from a config file
    and providing default values in case values are missing from the config
    file or the file is not readable. It also handles validation of all the
    fields in the config.
    """

    def __init__(self, config_file_path, args=None):
        """Create the SATConfig object and load values from the given file path

        Args:
            config_file_path: The path to the config file in TOML format.
            args: a Namespace object returned by an ArgumentParser, used
                to override config values to values supplied on the command
                line.
        """

        self.sections = {}

        config_contents = None
        try:
            with open(config_file_path) as config_file:
                config_contents = toml.load(config_file)
        except IOError as ioerr:
            LOGGER.error("Couldn't open config file %s; using defaults. (%s)",
                         config_file_path, ioerr)

        if config_contents and isinstance(config_contents, dict):
            self.sections.update(config_contents)
        else:
            LOGGER.error("Unable to read config file at '%s'. Using default "
                         "configuration values.", config_file_path)

        for section, options in SAT_CONFIG_SPEC.items():
            if section not in self.sections:
                self.sections[section] = {option: _option_value(args, None, spec)
                                          for option, spec in options.items()}
            else:
                for option, spec in options.items():
                    self.sections[section][option] = \
                        _option_value(args, self.sections[section].get(option), spec)

        self._validate_config()

    def _validate_config(self):
        """Validates the configuration values according to SAT_CONFIG_SPEC.

        Validates that the configuration values are the correct type and pass
        their validation function if they have one. If problems are encountered
        during validation, logs a warning or error and falls back on defaults.

        Returns:
            None
        """
        unknown_sections = []
        for section, options in self.sections.items():
            if section not in SAT_CONFIG_SPEC:
                LOGGER.warning("Ignoring unknown section '%s' in config file.",
                               section)
                unknown_sections.append(section)
                continue

            unknown_options = []
            for option, value in options.items():
                if option not in SAT_CONFIG_SPEC[section]:
                    LOGGER.warning("Ignoring unknown option '%s' in section '%s' "
                                   "of config file.", option, section)
                    unknown_options.append(option)
                    continue

                option_spec = SAT_CONFIG_SPEC[section][option]
                try:
                    converted_value = option_spec.type(value)
                except ValueError:
                    LOGGER.error("Unable to convert value (%s) of option '%s' in section '%s' of "
                                 "config file to the type '%s'. Defaulting to '%s'.",
                                 value, option, section, option_spec.type, option_spec.default)
                    self.sections[section][option] = option_spec.default
                    continue

                try:
                    if option_spec.validation_func is not None:
                        option_spec.validation_func(converted_value)
                except ConfigValidationError as err:
                    LOGGER.error("Invalid value '%s' given for option '%s' in section '%s': %s "
                                 "Defaulting to '%s'.",
                                 converted_value, option, section, err, option_spec.default)
                    self.sections[section][option] = option_spec.default
                    continue

                # The value converted to the correct type and validated
                self.sections[section][option] = converted_value

            # Remove any unknown options in this section to prevent them from being used
            for unknown_option in unknown_options:
                del self.sections[section][unknown_option]

        # Remove any unknown sections to prevent them from being used
        for unknown_section in unknown_sections:
            del self.sections[unknown_section]

    def get(self, section, option):
        """Gets the value of the option in the given section.

        Args:
            section: The section in the config file.
            option: The option in the config file.

        Returns:
            The value of the given `option` in the given `section`.
        """
        if section not in self.sections:
            raise KeyError("Couldn't find section {} in config.".format(section))
        elif option not in self.sections[section]:
            raise KeyError("Couldn't find option {} in section {}.".format(option, section))
        else:
            return self.sections[section][option]


def load_config(args=None):
    """Loads configuration from a config file into CONFIG global variable.

    Returns:
        None
    """
    global CONFIG

    # Only load the configuration once per invocation of this program.
    if CONFIG is not None:
        return

    # Allow the user to specify an alternate config file in an env variable
    config_file_path = os.getenv('SAT_CONFIG_FILE', DEFAULT_CONFIG_PATH)

    CONFIG = SATConfig(config_file_path, args)


def get_config_value(query_string):
    """Loads config (if necessary) and gets option value.

    This is a convenience function to quickly access config option values from
    the global CONFIG object in this module.

    Args:
        query_string (str): A dot-delimited reference to a section and option from
            the configuration. query_string should be in the form '<section>.<option>'.

    Returns:
        The requested option from the global CONFIG object.
    """
    load_config()

    EXPECTED_LEVELS = 2  # TODO: Arbitrary nesting?
    parts = query_string.split('.')
    if len(parts) != EXPECTED_LEVELS:
        raise ValueError("Wrong number of levels in query string passed to get_config_value(). "
                         "(Should be {}, was {}.)".format(EXPECTED_LEVELS, len(parts)))
    else:
        section, option = parts
        if not section or not option:
            raise ValueError("Improperly formatted query string supplied to get_config_value(). "
                             "(Got '%s'.)".format(query_string))
        else:
            return CONFIG.get(section, option)
