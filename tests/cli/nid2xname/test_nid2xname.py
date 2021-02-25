"""
Unit tests for the sat.cli.nid2xname

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

from sat.cli.nid2xname.main import do_nid2xname


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.nids = ['nid001006']


class TestDoNid2xname(unittest.TestCase):
    """Unit test for nid2xname"""

    def setUp(self):
        """Mock functions called."""
        self.mock_hsm_client = mock.patch('sat.cli.nid2xname.main.HSMClient',
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
        self.mock_sat_session = mock.patch('sat.cli.nid2xname.main.SATSession').start()
        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.fake_args = Namespace()
        set_options(self.fake_args)

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_one_nid_exists(self):
        """Test do_nid2xname with one valid nid."""
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1')

    def test_one_nid_not_exists(self):
        """Test do_nid2xname with one invalid nid."""
        self.fake_args.nids = ['nid001111']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('MISSING')

    def test_two_nids_exist(self):
        """Test do_nid2xname with two valid nids."""
        self.fake_args.nids = ['1006', '1069']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s1b0n0')

    def test_two_comma_separated_nids_exist(self):
        """Test do_nid2xname with two valid comma separated nids."""
        self.fake_args.nids = ['001006,001069']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s1b0n0')

    def test_two_comma_separated_nids_with_space_exist(self):
        """Test do_nid2xname with two valid comma separated nids with space."""
        self.fake_args.nids = ['nid001069,', 'nid001073']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,x1000c2s2b0n0')

    def test_three_nids_different_formats_exist(self):
        """Test do_nid2xname with three valid nids using different formats."""
        self.fake_args.nids = ['nid001069', 'nid1073', '1074', '001006']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,x1000c2s2b0n0,x1000c2s2b0n1,x1000c0s1b0n1')

    def test_three_nids_one_invalid(self):
        """Test do_nid2xname with two valid nids and one invalid string."""
        self.fake_args.nids = ['1069', 'not-a-nid', '1074']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,MISSING,x1000c2s2b0n1')

    def test_one_nid_range(self):
        """Test do_nid2xname with one nid range."""
        self.fake_args.nids = ['1073-1074']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c2s2b0n0,x1000c2s2b0n1')

    def test_one_nid_range_not_exists(self):
        """Test do_nid2xname with range of nids that do not exist."""
        self.fake_args.nids = ['20-22']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('MISSING,MISSING,MISSING')

    def test_nid_with_nid_range(self):
        """Test do_nid2xname with one nid and one nid range."""
        self.fake_args.nids = ['1006', '1073-1074']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1')

    def test_mix_of_nids_with_nid_ranges(self):
        """Test do_nid2xname with mix of nids and nid ranges."""
        self.fake_args.nids = ['1006', '1073-1074', '1069']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_mix_of_nids_with_nid_ranges_different_formats(self):
        """Test do_nid2xname with mix of nids and nid ranges with different formats."""
        self.fake_args.nids = ['nid1006', 'nid1073-1074', 'nid001069']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_one_nid_range_invalid(self):
        """Test do_nid2xname with an invalid range."""
        self.fake_args.nids = ['not-a-range']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('MISSING')

    def test_mix_of_nids_with_nid_range_invalid(self):
        """Test do_nid2xname with mix of nids and invalid range."""
        self.fake_args.nids = ['1069', 'not-a-range', '1074']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,MISSING,x1000c2s2b0n1')

    def test_comma_separated_mix_of_nids_with_nid_ranges(self):
        """Test do_nid2xname with comma separated mix of nids and nid ranges."""
        self.fake_args.nids = ['1006,1073-1074,1069']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_comma_separated_mix_of_nids_with_nid_ranges_with_space(self):
        """Test do_nid2xname with comma separated mix of nids and nid ranges with space."""
        self.fake_args.nids = ['1006,', '1073-1074,', '1069']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_comma_separated_mix_of_nids_with_nid_ranges_different_formats(self):
        """Test do_nid2xname with comma separated mix of nids and nid ranges with different formats."""
        self.fake_args.nids = ['nid1006,nid1073-1074,nid001069']
        do_nid2xname(self.fake_args)
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')


if __name__ == '__main__':
    unittest.main()
