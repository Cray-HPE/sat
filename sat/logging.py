#
# MIT License
#
# (C) Copyright 2019-2020,2023 Hewlett Packard Enterprise Development LP
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
Sets up logging for SAT.
"""
import logging
import os

from sat.config import get_config_value

CSM_CLIENT_MODULE_NAME = 'csm_api_client'
WARNINGS_MODULE_NAME = 'py.warnings'
CONSOLE_LOG_FORMAT = '%(levelname)s: %(message)s'
FILE_LOG_FORMAT = '%(asctime)s - %(levelname)s - %(name)s - %(message)s'
LOGGER = logging.getLogger(__name__)


def _add_console_handler(logger, log_level):
    """Adds a handler that prints to stderr to the given logger

    Args:
        logger (logging.Logger): the Logger object to add the handler to
        log_level: the level to set in the handler
    """
    console_handler = logging.StreamHandler()
    console_handler.setLevel(log_level)
    console_formatter = logging.Formatter(CONSOLE_LOG_FORMAT)
    console_handler.setFormatter(console_formatter)
    logger.addHandler(console_handler)


def bootstrap_logging():
    """Sets up logging just enough to log warnings and errors to stderr.

    Logging setup is done in two stages. This first stage is done before loading
    the configuration file that specifies the log file location and log levels
    for the file and console handlers. This allows the code that loads and
    validates the config file to log errors and warnings using its logger.

    Returns:
        None
    """
    sat_logger_name = __name__.split('.', 1)[0]
    sat_logger = logging.getLogger(sat_logger_name)
    sat_logger.setLevel(logging.DEBUG)
    _add_console_handler(sat_logger, logging.WARNING)


def configure_logging():
    """Configures logging according to the config file and command-line options

    This sets up two handlers, one that logs to a log file and one that logs to
    stderr.

    For a module within sat to log, the module should obtain a logger object
    as shown below:

        import logging
        LOGGER = logging.getLogger(__name__)

    Then they should use this `LOGGER` to log messages. This will automatically
    ensure that the name of the module logging the message is included in the
    log message, and it will inherit the configuration from the root logger
    set up here.

    Returns:
        None
    """
    sat_logger_name = __name__.split('.', 1)[0]
    sat_logger = logging.getLogger(sat_logger_name)

    # Handle log messages from the CSM API client with the same
    # handlers and log levels as log messages from SAT.
    csm_client_logger = logging.getLogger(CSM_CLIENT_MODULE_NAME)
    csm_client_logger.setLevel(logging.DEBUG)
    # Handle log messages from the warnings module too
    warnings_logger = logging.getLogger(WARNINGS_MODULE_NAME)
    warnings_logger.setLevel(logging.WARNING)

    log_file_name = get_config_value('logging.file_name')
    log_file_level = get_config_value('logging.file_level')
    log_stderr_level = get_config_value('logging.stderr_level')

    # Convert to actual logging levels
    log_file_level = getattr(logging, log_file_level.upper())
    log_stderr_level = getattr(logging, log_stderr_level.upper())

    # Remove all handlers to configure handlers according to config file
    sat_logger.handlers = []

    _add_console_handler(sat_logger, log_stderr_level)
    _add_console_handler(csm_client_logger, log_stderr_level)
    _add_console_handler(warnings_logger, log_stderr_level)

    # Create log directories if needed
    log_dir = os.path.dirname(log_file_name)
    if log_dir:
        try:
            os.makedirs(log_dir, exist_ok=True)
        except OSError as err:
            LOGGER.warning("Unable to create log directory '%s': %s", log_dir, err)
            return
    try:
        file_handler = logging.FileHandler(filename=log_file_name)
    except OSError as err:
        LOGGER.warning("Unable to write to log file: %s", err)
    else:
        file_handler.setLevel(log_file_level)
        file_formatter = logging.Formatter(FILE_LOG_FORMAT)
        file_handler.setFormatter(file_formatter)
        sat_logger.addHandler(file_handler)
        csm_client_logger.addHandler(file_handler)
        warnings_logger.addHandler(file_handler)
