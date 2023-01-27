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
Unit tests for sat.logging
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
        # In the logging module, getLogger is called twice, once to get the main
        # logger for SAT and once to get the logger for the csm_api_client library.
        self.logger = logging.getLogger(__name__)
        self.sub_logger = logging.getLogger('submodule')
        self.mock_get_logger = mock.patch(
            'sat.logging.logging.getLogger',
            side_effect=(self.logger, self.sub_logger)
        ).start()

        config_values = self.config_values = {
            'logging.file_name': '/var/log/cray/sat/sat.log',
            'logging.file_level': 'debug',
            'logging.stderr_level': 'warning'
        }
        self.mock_get_config = mock.patch('sat.logging.get_config_value',
                                          lambda opt: config_values[opt]).start()

    def tearDown(self):
        """Tears down after each test method.

        Stops the patching of getLogger and get_config_value. Removes handlers
        that may have been added by the tests to ensure a clean slate for tests.
        """
        mock.patch.stopall()
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

        # This should have gotten the logger named 'sat'
        self.mock_get_logger.assert_called_once_with('sat')

        self.assertEqual(logging.DEBUG, self.logger.level)

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
    def test_configure_logging(self, mock_makedirs):
        """Test configure_logging function."""
        configure_logging()

        # This should have gotten the logger named 'sat'
        self.mock_get_logger.assert_any_call('sat')
        # And also the logger named 'csm_api_client'
        self.mock_get_logger.assert_any_call('csm_api_client')

        log_dir = os.path.dirname(self.config_values['logging.file_name'])
        mock_makedirs.assert_called_once_with(log_dir, exist_ok=True)

        stream_handler, file_handler = self.assert_configured_handlers()

        self.assertEqual(stream_handler.level, logging.WARNING)

        self.assertEqual(file_handler.level, logging.DEBUG)
        self.assertEqual(file_handler.baseFilename, self.config_values['logging.file_name'])

        warning_message = 'This is a warning'
        with self.assertLogs(self.logger, logging.WARNING) as cm:
            self.logger.warning(warning_message)

        self.assertEqual(stream_handler.format(cm.records[0]),
                         'WARNING: {}'.format(warning_message))
        self.assertIn(
            ' - WARNING - {} - {}'.format(self.logger.name,
                                          warning_message),
            file_handler.format(cm.records[0]))

    @mock.patch('os.makedirs', side_effect=OSError)
    def test_configure_logging_directory_fail(self, _):
        """Test configure_logging with a failure to create the log directory"""
        configure_logging()

        # This should have gotten the logger named 'sat'
        self.mock_get_logger.assert_any_call('sat')
        self.mock_get_logger.assert_any_call('csm_api_client')

        # Exactly one handler of type StreamHandler should have been added.
        self.assertEqual(len(self.logger.handlers), 1)
        handler = self.logger.handlers[0]
        self.assertIsInstance(handler, logging.StreamHandler)
        self.assertEqual(handler.level, logging.WARNING)

    @mock.patch('os.makedirs')
    def test_configure_logging_no_directory(self, mock_makedirs):
        """Test no log directories are created when they are not needed"""
        self.config_values['logging.file_name'] = 'sat.log'
        configure_logging()
        mock_makedirs.assert_not_called()


if __name__ == '__main__':
    unittest.main()
