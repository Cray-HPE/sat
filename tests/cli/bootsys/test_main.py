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
import glob
import os
import unittest
from unittest.mock import Mock, patch

import sat
from sat.cli.bootsys.main import do_boot, do_bootsys, do_shutdown, dump_pods


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

    @patch('sat.cli.bootsys.main.dump_pods')
    @patch('builtins.print')
    @patch('sat.cli.bootsys.main.do_service_activity_check')
    def test_do_shutdown(self, mock_checker, mock_print, mock_dump_pods):
        """Test the do_shutdown function."""
        args = Mock()
        args.pod_state_file = 'doesnt matter'
        do_shutdown(args)
        mock_checker.assert_called_once_with(args)
        mock_print.assert_called_once_with(
            'It is safe to continue with the shutdown procedure. '
            'Please proceed.'
        )


class TestDoBootsys(unittest.TestCase):
    """Test the do_bootsys function."""

    def setUp(self):
        """Mock the methods called by do_bootsys.
        """
        self.mock_do_boot = patch('sat.cli.bootsys.main.do_boot').start()
        self.mock_do_shutdown = patch('sat.cli.bootsys.main.do_shutdown').start()

        self.default_dir = os.path.join(os.path.dirname(__file__), '../..', 'resources', 'podstates/')
        self.default_podstate = os.path.join(self.default_dir, 'pod-state.json')

        patch('sat.cli.bootsys.main.DEFAULT_DIR', self.default_dir).start()
        patch('sat.cli.bootsys.main.DEFAULT_PODSTATE', self.default_podstate).start()

        self.pod_mock = patch(
            'sat.cli.bootsys.main.get_pods_as_json',
            return_value='hello').start()

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

    def test_dump_pods_custom_path(self):
        """dump_pods should write text to a custom file location.

        More specifically, it should write the output of get_pods_as_json.
        """
        dir_in = self.default_dir
        outfile = os.path.join(dir_in, 'custom-path')

        try:
            dump_pods(outfile)

            with open(outfile, 'r') as f:
                lines = f.read()

            self.assertEqual('hello', lines)

        finally:
            os.remove(outfile)

    def test_dump_pods_default(self):
        """dump_pods should create a symlink that points to the next log.
        """
        try:
            dump_pods(sat.cli.bootsys.main.DEFAULT_PODSTATE)
            with open(self.default_podstate, 'r') as f:
                lines = f.read()
            self.assertEqual('hello', lines)

        finally:
            files = glob.glob(self.default_dir + 'pod-state*')
            for f in files:
                os.remove(f)

    def test_dump_pods_rotating_logs(self):
        """dump_pods should rotate the logs.

        A maximum number of logs should be kept as specified
        in the config file.
        """
        class MockNamer:
            _num = -1
            @classmethod
            def genName(cls):
                MockNamer._num = MockNamer._num + 1
                return self.default_dir + 'pod-state.{:02d}.json'.format(MockNamer._num)

        patch('sat.cli.bootsys.main._new_file_name', MockNamer.genName).start()
        patch('sat.cli.bootsys.main.get_config_value', return_value=5).start()

        # At the end of this, there should only be 5 logs plus the symlink.
        try:
            for i in range(1, 15):
                dump_pods(sat.cli.bootsys.main.DEFAULT_PODSTATE)

            files = [x for x in sorted(os.listdir(self.default_dir)) if x.startswith('pod-state')]

            # There should be 6 files left including the symlink, and the earliest
            # should appear first.
            self.assertEqual(6, len(files))
            self.assertEqual('pod-state.09.json', files[0])

        finally:
            files = glob.glob(self.default_dir + 'pod-state*')
            for f in files:
                os.remove(f)


if __name__ == '__main__':
    unittest.main()
