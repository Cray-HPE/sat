"""
Unit tests for the sat.cli.xname2nid

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
from unittest import mock
from argparse import Namespace

from sat.cli.xname2nid.main import do_xname2nid


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.xnames = ['x1000c0s1b0n1']


class TestDoXname2nid(unittest.TestCase):
    """Unit test for xname2nid"""

    def setUp(self):
        """Mock functions called."""
        self.mock_hsm_client = mock.patch('sat.cli.xname2nid.main.HSMClient',
                                          autospec=True).start().return_value
        self.mock_hsm_client.get_node_components.return_value = [
            {'NID': 1006,
             'Type': 'Node',
             'ID': 'x1000c0s1b0n1'},
            {'NID': 1069,
             'Type': 'Node',
             'ID': 'x1000c2s1b0n0'},
            {'NID': 1073,
             'Type': 'Node',
             'ID': 'x1000c2s2b0n0'},
            {'NID': 1074,
             'Type': 'Node',
             'ID': 'x1000c2s2b0n1'}
        ]
        self.mock_sat_session = mock.patch('sat.cli.xname2nid.main.SATSession').start()
        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.fake_args = Namespace()
        set_options(self.fake_args)

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_one_xname_exists(self):
        """Test do_xname2nid with one valid xname."""
        do_xname2nid(self.fake_args)
        self.mock_print.assert_called_once_with('nid001006')

    def test_one_xname_not_exists(self):
        """Test do_xname2nid with one invalid xname."""
        self.fake_args.xnames = ['x1000c2s1b0n5']
        do_xname2nid(self.fake_args)
        self.mock_print.assert_called_once_with('MISSING')

    def test_two_xnames_exist(self):
        """Test do_xname2nid with two valid xnames."""
        self.fake_args.xnames = ['x1000c2s1b0n0', 'x1000c2s2b0n0']
        do_xname2nid(self.fake_args)
        self.mock_print.assert_called_once_with('nid001069,nid001073')

    def test_two_comma_separated_xnames_exist(self):
        """Test do_xname2nid with two valid comma separated xnames."""
        self.fake_args.xnames = ['x1000c2s1b0n0,x1000c2s2b0n0']
        do_xname2nid(self.fake_args)
        self.mock_print.assert_called_once_with('nid001069,nid001073')

    def test_two_comma_separated_xnames_with_space_exist(self):
        """Test do_xname2nid with two valid comma separated xnames with space."""
        self.fake_args.xnames = ['x1000c2s1b0n0,', 'x1000c2s2b0n0']
        do_xname2nid(self.fake_args)
        self.mock_print.assert_called_once_with('nid001069,nid001073')

    def test_three_xnames_one_invalid(self):
        """Test do_xname2nid with two valid xnames and one invalid string."""
        self.fake_args.xnames = ['x1000c2s1b0n0', 'not-an-xname', 'x1000c2s2b0n0']
        do_xname2nid(self.fake_args)
        self.mock_print.assert_called_once_with('nid001069,MISSING,nid001073')


if __name__ == '__main__':
    unittest.main()
