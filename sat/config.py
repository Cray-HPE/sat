"""
Loads configuration from a config file in INI format.
Copyright 2019 Cray Inc. All Rights Reserved
"""

from collections import namedtuple
from configparser import ConfigParser
import logging
import os

DEFAULT_CONFIG_PATH = '/etc/sat.ini'
LOGGER = logging.getLogger(__name__)
CONFIG = None

OptionSpec = namedtuple('OptionSpec', ['type', 'default', 'validation_func'])


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
    'default': {
        'api_gateway_host': OptionSpec(str, 'api-gw-service-nmn.local', None),
        'log_file_name': OptionSpec(str, '/var/log/cray/sat.log', None),
        'log_file_level': OptionSpec(str, 'INFO', validate_log_level),
        'log_stderr_level': OptionSpec(str, 'WARNING', validate_log_level),
        'site_info': OptionSpec(str, '/opt/cray/etc/site_info.yml', None),
    }
}


class SATConfig(object):
    """A class representing the configuration of the SAT program.

    This class is responsible for loading the configuration from a config file
    and providing default values in case values are missing from the config
    file or the file is not readable. It also handles validation of all the
    fields in the config.
    """

    def __init__(self, config_file_path):
        """Create the SATConfig object and load values from the given file path

        Args:
            config_file_path: The path to the config file in INI format.
        """
        self.config_parser = ConfigParser(interpolation=None)

        for section, options in SAT_CONFIG_SPEC.items():
            self.config_parser[section] = {}
            for option_name, option_spec in options.items():
                self.config_parser[section][option_name] = option_spec.default

        success_files = self.config_parser.read(config_file_path)
        if not success_files:
            LOGGER.error("Unable to read config file at '%s'. Using default "
                         "configuration values.", config_file_path)

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
        for section in self.config_parser.sections():
            if section not in SAT_CONFIG_SPEC:
                LOGGER.warning("Ignoring unknown section '%s' in config file.",
                               section)
                unknown_sections.append(section)
                continue

            unknown_options = []
            for option, value in self.config_parser[section].items():
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
                    self.config_parser[section][option] = option_spec.default
                    continue

                try:
                    if option_spec.validation_func is not None:
                        option_spec.validation_func(converted_value)
                except ConfigValidationError as err:
                    LOGGER.error("Invalid value '%s' given for option '%s' in section '%s': %s "
                                 "Defaulting to '%s'.",
                                 converted_value, option, section, err, option_spec.default)
                    self.config_parser[section][option] = option_spec.default
                    continue

                # The value converted to the correct type and validated
                self.config_parser[section][option] = converted_value

            # Remove any unknown options in this section to prevent them from being used
            for unknown_option in unknown_options:
                self.config_parser.remove_option(section, unknown_option)

        # Remove any unknown sections to prevent them from being used
        for unknown_section in unknown_sections:
            self.config_parser.remove_section(unknown_section)

    def get(self, section, option):
        """Gets the value of the option in the given section.

        Args:
            section: The section in the config file.
            option: The option in the config file.

        Returns:
            The value of the given `option` in the given `section`.
        """
        return self.config_parser.get(section, option)


def load_config():
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

    CONFIG = SATConfig(config_file_path)


def get_config_value(option, section='default'):
    """Loads config (if necessary) and gets option value.

    This is a convenience function to quickly access config option values from
    the global CONFIG object in this module.

    Args:
        option (str): The name of the option
        section (str): The name of the section, defaults to 'default' for convenience.

    Returns:
        The requested option from the global CONFIG object.
    """
    load_config()
    return CONFIG.get(section, option)
