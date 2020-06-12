"""
Unit tests for the sat.cli.bootsys.main module.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
import unittest
from unittest.mock import Mock, patch

from sat.cli.bootsys.main import do_boot, do_bootsys, do_shutdown


class TestDoBoot(unittest.TestCase):
    """Test the do_boot function (not yet implemented)."""

    def test_do_boot(self):
        """Test the do_boot function, which is unimplemented."""
        args = Mock()
        with self.assertRaises(SystemExit) as cm:
            do_boot(args)

        self.assertEqual(1, cm.exception.code)


class TestDoShutdown(unittest.TestCase):
    """Test the do_shutdown function."""

    @patch('builtins.print')
    @patch('sat.cli.bootsys.main.do_service_activity_check')
    def test_do_shutdown(self, mock_checker, mock_print):
        """Test the do_shutdown function."""
        args = Mock()
        do_shutdown(args)
        mock_checker.assert_called_once_with(args)
        mock_print.assert_called_once_with(
            'It is safe to continue with the shutdown procedure. '
            'Please proceed.'
        )


class TestDoBootsys(unittest.TestCase):
    """Test the do_bootsys function."""

    def setUp(self):
        """Mock the methods called by do_bootsys."""
        self.mock_do_boot = patch('sat.cli.bootsys.main.do_boot').start()
        self.mock_do_shutdown = patch('sat.cli.bootsys.main.do_shutdown').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_do_bootsys_boot(self):
        """Test do_bootsys with boot action."""
        args = Mock(action='boot')
        do_bootsys(args)
        self.mock_do_boot.assert_called_once_with(args)
        self.mock_do_shutdown.assert_not_called()

    def test_do_bootsys_shutdown(self):
        """Test do_bootsys with shutdown action."""
        args = Mock(action='shutdown')
        do_bootsys(args)
        self.mock_do_shutdown.assert_called_once_with(args)
        self.mock_do_boot.assert_not_called()

    def test_do_bootsys_invalid_action(self):
        """Test do_bootsys with an invalid action."""
        args = Mock(action='invalid')
        with self.assertRaises(SystemExit) as cm:
            do_bootsys(args)
        self.assertEqual(1, cm.exception.code)
        self.mock_do_boot.assert_not_called()
        self.mock_do_shutdown.assert_not_called()


if __name__ == '__main__':
    unittest.main()
