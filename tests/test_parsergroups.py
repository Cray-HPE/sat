"""
Tests the argument parser.

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

from sat.parsergroups import create_xname_options


xnames_file = os.path.join(os.path.dirname(__file__), 'resources', 'xnames.txt')


class TestCreateXnameOptions(unittest.TestCase):
    """Tests for ensuring behavior of command line argument parsing.
    """
    def test_single_xname1(self):
        """Test a single xname can be stored in the argparser.
        """
        parser = create_xname_options()
        args = parser.parse_args(['-x', 'x1'])
        self.assertEqual(['x1'], args.xnames)

    def test_single_xname2(self):
        """Same as above, but with the --xname option.
        """
        parser = create_xname_options()
        args = parser.parse_args(['--xname', 'x1'])
        self.assertEqual(['x1'], args.xnames)

    def test_single_xname3(self):
        """Same as above, but with the --xnames option.
        """
        parser = create_xname_options()
        args = parser.parse_args(['--xnames', 'x1'])
        self.assertEqual(['x1'], args.xnames)

    def test_xnames_via_csv(self):
        """Multiple xnames should be passable via csv string.
        """
        parser = create_xname_options()
        args = parser.parse_args(['-x', 'x1,x2,x3'])
        self.assertEqual(['x1', 'x2', 'x3'], args.xnames)

    def test_multiple_args(self):
        """The arg should be capable of being specified multiple times.
        """
        parser = create_xname_options()
        args = parser.parse_args(['-x', 'x1', '-x', 'x2'])
        self.assertEqual(['x1', 'x2'], args.xnames)

    def test_xnames_from_file(self):
        """The Xnames should be readable from a file.
        """
        parser = create_xname_options()
        args = parser.parse_args(['--xname-file', xnames_file])
        self.assertEqual(['x1', 'x2', 'x3'], args.xnames)

    def test_file_not_found(self):
        """If the xnames file isn't found then an exception should raise.
        """
        parser = create_xname_options()
        with self.assertRaises(SystemExit):
            args = parser.parse_args(['--xname-file', 'idontexist'])

    @mock.patch('builtins.open', side_effect=PermissionError)
    def test_file_permission_error(self, mocker):
        """If the xnames file cannot be read then an exception should raise.
        """
        parser = create_xname_options()
        with self.assertRaises(SystemExit):
            args = parser.parse_args(['--xname-file', xnames_file])

    def test_ultimate_cat(self):
        """Prepare for everything.
        """
        l_ = [
            '--xname-file', xnames_file,
            '-x', 'x4',
            '--xnames', 'x5, x6, x7',
            '--xname', 'x8',
        ]
        expected = ['x1', 'x2', 'x3', 'x4', 'x5', 'x6', 'x7', 'x8']
        parser = create_xname_options()
        args = parser.parse_args(l_)
        self.assertEqual(expected, args.xnames)

    def test_ip_addr(self):
        """ The sensors subcommand can accept IP addresses as well.
        """
        l_ = ['-x', '192.168.0.1', '--xnames', '192.168.0.2']
        expected = ['192.168.0.1', '192.168.0.2']
        parser = create_xname_options()
        args = parser.parse_args(l_)
        self.assertEqual(expected, args.xnames)

    def test_list(self):
        """ Nargs > 1 should not be supported.
        """
        l_ = ['-x', '192.168.0.1', '192.168.0.2']
        parser = create_xname_options()
        with self.assertRaises(SystemExit):
            args = parser.parse_args(l_)

    def test_deduplicated(self):
        """ Duplicated xnames should be removed.
        """
        l_ = ['-x', 'x1, x2', '--xnames', 'x1', '--xname-file', xnames_file]
        expected = ['x1', 'x2', 'x3']
        parser = create_xname_options()
        args = parser.parse_args(l_)

        self.assertEqual(expected, args.xnames)


if __name__ == '__main__':
    unittest.main()
