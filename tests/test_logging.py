"""
Unit tests for sat.logging

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging
import os
import unittest
from unittest import mock

from sat.logging import bootstrap_logging, configure_logging


class TestLogging(unittest.TestCase):

    def setUp(self):
        """Sets up for each test method.

        Sets up by patching getLogger to return a logger of our own and by
        patching get_config_value to return values from a dict.
        """
        self.logger = logging.getLogger(__name__)
        self.get_logger_patcher = mock.patch(
            'sat.logging.logging.getLogger',
            return_value=self.logger
        )
        self.get_logger_patcher.start()

        config_values = self.config_values = {
            'log_file_name': '/var/log/cray/sat.log',
            'log_file_level': 'debug',
            'log_stderr_level': 'warning'
        }
        self.config_patcher = mock.patch('sat.logging.get_config_value',
                                         lambda opt: config_values[opt])
        self.config_patcher.start()

    def tearDown(self):
        """Tears down after each test method.

        Stops the patching of getLogger and get_config_value. Removes handlers
        that may have been added by the tests to ensure a clean slate for tests.
        """
        self.get_logger_patcher.stop()
        self.config_patcher.stop()
        self.logger.handlers = []

    def assert_configured_handlers(self):
        """Gets the handlers configured on self.logger.

        Makes assertions that there is one handler of type StreamHandler and
        one of type FileHandler on self.logger.

        Returns:
            A tuple of stream_handler, file_handler

        Raises:
            AssertionError: if an assertion fails
        """
        self.assertEqual(len(self.logger.handlers), 2)
        stream_handler = None
        file_handler = None
        for handler in self.logger.handlers:
            # Note that FileHandler is a subclass of StreamHandler, so order is important
            if isinstance(handler, logging.FileHandler):
                file_handler = handler
            elif isinstance(handler, logging.StreamHandler):
                stream_handler = handler

        self.assertIsNotNone(stream_handler)
        self.assertIsNotNone(file_handler)
        return stream_handler, file_handler

    def test_bootstrap_logging(self):
        """Test bootstrap_logging function."""
        bootstrap_logging()

        # Exactly one handler of type StreamHandler should have been added.
        self.assertEqual(len(self.logger.handlers), 1)
        handler = self.logger.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertEqual(handler.level, logging.WARNING)

        # Unfortunately self.assertLogs does not work directly to test that
        # logs are emitted with the correct format because it replaces the
        # logger with one of its own with its own handlers and formatter.
        # We can use it here to get a log record to format with the handler
        # created by bootstrap_logging.
        warning_message = 'This is a warning'
        with self.assertLogs(self.logger, logging.WARNING) as cm:
            self.logger.warning(warning_message)

        self.assertEqual(handler.format(cm.records[0]),
                         'WARNING: {}'.format(warning_message))

    @mock.patch('logging.open', mock.MagicMock)
    @mock.patch('os.makedirs')
    def test_configure_logging_no_args(self, mock_makedirs):
        """Test configure_logging function."""
        args = mock.Mock()
        args.logfile = None
        args.loglevel = None
        configure_logging(args)

        log_dir = os.path.dirname(self.config_values['log_file_name'])
        mock_makedirs.assert_called_once_with(log_dir, exist_ok=True)

        stream_handler, file_handler = self.assert_configured_handlers()

        self.assertEqual(stream_handler.level, logging.WARNING)

        self.assertEqual(file_handler.level, logging.DEBUG)
        self.assertEqual(file_handler.baseFilename, self.config_values['log_file_name'])

        warning_message = 'This is a warning'
        with self.assertLogs(self.logger, logging.WARNING) as cm:
            self.logger.warning(warning_message)

        self.assertEqual(stream_handler.format(cm.records[0]),
                         'WARNING: {}'.format(warning_message))
        self.assertIn(
            ' - WARNING - {} - {}'.format(self.logger.name,
                                          warning_message),
            file_handler.format(cm.records[0]))

    @mock.patch('logging.open', mock.MagicMock)
    @mock.patch('os.makedirs')
    def test_configure_logging_with_args(self, mock_makedirs):
        """Test configure_logging function."""
        args = mock.Mock()
        args.logfile = '/my/custom/log/location'
        args.loglevel = 'info'
        configure_logging(args)

        log_dir = os.path.dirname(args.logfile)
        mock_makedirs.assert_called_once_with(log_dir, exist_ok=True)

        stream_handler, file_handler = self.assert_configured_handlers()

        self.assertEqual(stream_handler.level, logging.INFO)

        self.assertEqual(file_handler.level, logging.INFO)
        self.assertEqual(file_handler.baseFilename, args.logfile)

    @mock.patch('os.makedirs', side_effect=OSError)
    def test_configure_logging_directory_fail(self, _):
        """Test configure_logging with a failure to create the log directory"""
        args = mock.Mock()
        args.logfile = None
        args.loglevel = None
        configure_logging(args)

        # Exactly one handler of type StreamHandler should have been added.
        self.assertEqual(len(self.logger.handlers), 1)
        handler = self.logger.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertEqual(handler.level, logging.WARNING)



if __name__ == '__main__':
    unittest.main()
