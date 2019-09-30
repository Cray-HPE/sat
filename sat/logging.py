"""
Sets up logging for SAT.
Copyright 2019 Cray Inc. All Rights Reserved
"""
import logging
import os

from sat.config import get_config_value

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
    root_logger = logging.getLogger()
    root_logger.setLevel(logging.DEBUG)
    _add_console_handler(root_logger, logging.WARNING)


def configure_logging(args):
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

    Args:
        args: The argparse.Namespace object containing the parsed arguments for
            this program.

    Returns:
        None
    """
    root_logger = logging.getLogger()

    log_file_name = get_config_value('log_file_name')
    if args.logfile is not None:
        log_file_name = args.logfile

    log_file_level = get_config_value('log_file_level')
    log_stderr_level = get_config_value('log_stderr_level')
    if args.loglevel is not None:
        log_file_level = args.loglevel
        log_stderr_level = args.loglevel

    # Convert to actual logging levels
    log_file_level = getattr(logging, log_file_level.upper())
    log_stderr_level = getattr(logging, log_stderr_level.upper())

    # Remove all handlers to configure handlers according to config file
    root_logger.handlers = []

    _add_console_handler(root_logger, log_stderr_level)

    log_dir = os.path.dirname(log_file_name)
    try:
        os.makedirs(log_dir, exist_ok=True)
    except OSError as err:
        LOGGER.error("Unable to create log directory '%s': %s", log_dir, err)
        return

    file_handler = logging.FileHandler(filename=log_file_name)
    file_handler.setLevel(log_file_level)
    file_formatter = logging.Formatter(FILE_LOG_FORMAT)
    file_handler.setFormatter(file_formatter)
    root_logger.addHandler(file_handler)
