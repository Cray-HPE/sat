#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.nid2xname module.
"""

import logging
import unittest
from argparse import Namespace
from unittest import mock

from sat.apiclient import APIError
from sat.cli.nid2xname.main import (
    ERR_MISSING_NAMES,
    ERR_HSM_API_FAILED,
    do_nid2xname
)
from tests.common import ExtendedTestCase


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.nids = ['nid001006']


class TestDoNid2xname(ExtendedTestCase):
    """Unit test for nid2xname"""

    def setUp(self):
        """Mock functions called."""
        self.node_data = [
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
             'ID': 'x1000c2s2b0n1'},
            {'NID': 1075,
             'Type': 'Node'}
        ]
        self.mock_hsm_client = mock.patch('sat.cli.nid2xname.main.HSMClient',
                                          autospec=True).start().return_value
        self.mock_hsm_client.get_node_components.return_value = self.node_data
        self.mock_sat_session = mock.patch('sat.cli.nid2xname.main.SATSession').start()
        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.fake_args = Namespace()
        set_options(self.fake_args)

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_one_nid_exists(self):
        """Test do_nid2xname with one valid nid."""
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        self.assert_in_element(f'xname: {self.node_data[0]["ID"]}, nid: {self.node_data[0]["NID"]}',
                               logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1')

    def test_one_nid_not_exists(self):
        """Test do_nid2xname with one invalid nid."""
        self.fake_args.nids = ['nid001111']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.assert_in_element('xname: MISSING, nid: 1111', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_not_called()

    def test_two_nids_exist(self):
        """Test do_nid2xname with two valid nids."""
        self.fake_args.nids = ['1006', '1069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:1]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s1b0n0')

    def test_two_comma_separated_nids_exist(self):
        """Test do_nid2xname with two valid comma separated nids."""
        self.fake_args.nids = ['001006,001069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:1]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s1b0n0')

    def test_two_comma_separated_nids_with_space_exist(self):
        """Test do_nid2xname with two valid comma separated nids with space."""
        self.fake_args.nids = ['nid001069,', 'nid001073']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[1:2]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,x1000c2s2b0n0')

    def test_four_nids_different_formats_exist(self):
        """Test do_nid2xname with four valid nids using different formats."""
        self.fake_args.nids = ['nid001069', 'nid1073', '1074', '001006']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,x1000c2s2b0n0,x1000c2s2b0n1,x1000c0s1b0n1')

    def test_three_nids_one_invalid(self):
        """Test do_nid2xname with two valid nids and one invalid string."""
        self.fake_args.nids = ['1069', 'not-a-nid', '1073']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.assert_in_element('xname: MISSING, nid: not-a-nid', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,x1000c2s2b0n0')

    def test_one_nid_range(self):
        """Test do_nid2xname with one nid range."""
        self.fake_args.nids = ['1073-1074']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[2:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c2s2b0n0,x1000c2s2b0n1')

    def test_one_nid_range_not_exists(self):
        """Test do_nid2xname with range of nids that do not exist."""
        self.fake_args.nids = ['20-22']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        for nid in list(map(str, range(20, 23))):
            self.assert_in_element(f'xname: MISSING, nid: {nid}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_not_called()

    def test_one_pdsh_nid_range(self):
        """Test do_nid2xname with one pdsh nid range."""
        self.fake_args.nids = ['nid[1073-1074]']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[2:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c2s2b0n0,x1000c2s2b0n1')

    def test_complex_pdsh_nid_range(self):
        """Test do_nid2xname with complex pdsh nid range."""
        self.fake_args.nids = ['nid[1006,1069,1073-1074]']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[2:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s1b0n0,x1000c2s2b0n0,x1000c2s2b0n1')

    def test_nids_with_nid_range(self):
        """Test do_nid2xname with two nids and one nid range."""
        self.fake_args.nids = ['1006', '1069', '1073-1074']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s1b0n0,x1000c2s2b0n0,x1000c2s2b0n1')

    def test_nids_with_pdsh_nid_range(self):
        """Test do_nid2xname with two nids and one pdsh nid range."""
        self.fake_args.nids = ['1006', '1069', 'nid[1073-1074]']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s1b0n0,x1000c2s2b0n0,x1000c2s2b0n1')

    def test_mix_of_nids_with_nid_range(self):
        """Test do_nid2xname with mix of nids and nid range."""
        self.fake_args.nids = ['1006', '1073-1074', '1069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_mix_of_nids_with_pdsh_nid_range(self):
        """Test do_nid2xname with mix of nids and pdsh nid range."""
        self.fake_args.nids = ['1006', 'nid[1073-1074,1069]']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_mix_of_nids_with_nid_ranges_different_formats(self):
        """Test do_nid2xname with mix of nids and nid ranges with different formats."""
        self.fake_args.nids = ['nid1006', 'nid1073-1074', 'nid001069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_mix_of_nids_with_pdsh_nid_ranges_different_formats(self):
        """Test do_nid2xname with mix of nids and pdsh nid ranges with different formats."""
        self.fake_args.nids = ['nid1006', 'nid[1073-1074]', 'nid001069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_one_nid_range_invalid(self):
        """Test do_nid2xname with an invalid range."""
        self.fake_args.nids = ['not-a-range']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.assert_in_element('xname: MISSING, nid: not-a-range', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_not_called()

    def test_one_pdsh_nid_range_invalid(self):
        """Test do_nid2xname with an invalid pdsh range."""
        self.fake_args.nids = ['nid[not-a-range]']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.assert_in_element('xname: MISSING, nid: not-a-range', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_not_called()

    def test_mix_of_nids_with_nid_range_invalid(self):
        """Test do_nid2xname with mix of nids and invalid range."""
        self.fake_args.nids = ['1069', 'not-a-range', '1073']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.assert_in_element('xname: MISSING, nid: not-a-range', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,x1000c2s2b0n0')

    def test_mix_of_nids_with_pdsh_nid_range_invalid(self):
        """Test do_nid2xname with mix of nids and invalid pdsh range."""
        self.fake_args.nids = ['1069', 'nid[not-a-range]', '1073']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.assert_in_element('xname: MISSING, nid: not-a-range', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c2s1b0n0,x1000c2s2b0n0')

    def test_comma_separated_mix_of_nids_with_nid_range(self):
        """Test do_nid2xname with comma separated mix of nids and nid range."""
        self.fake_args.nids = ['1006,1073-1074,1069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_comma_separated_mix_of_nids_with_pdsh_nid_range(self):
        """Test do_nid2xname with comma separated mix of nids and pdsh nid range."""
        self.fake_args.nids = ['1006,nid10[73-74],1069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_comma_separated_mix_of_nids_with_nid_range_with_space(self):
        """Test do_nid2xname with comma separated mix of nids and nid range with space."""
        self.fake_args.nids = ['1006,', '1073-1074,', '1069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_comma_separated_mix_of_nids_with_pdsh_nid_range_with_space(self):
        """Test do_nid2xname with comma separated mix of nids and pdsh_nid range with space."""
        self.fake_args.nids = ['1006,', 'nid[1073-1074],', '1069']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0')

    def test_comma_separated_mix_of_nids_with_nid_ranges_different_formats(self):
        """Test do_nid2xname with comma separated mix of nids and nid ranges with different formats."""
        self.fake_args.nids = ['nid1006,nid1073-1074,nid001069,nid10[69,73-74]']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_nid2xname(self.fake_args)
        for node in self.node_data[0:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('x1000c0s1b0n1,x1000c2s2b0n0,x1000c2s2b0n1,x1000c2s1b0n0,'
                                                'x1000c2s1b0n0,x1000c2s2b0n0,x1000c2s2b0n1')

    def test_nid2xname_api_error(self):
        """Test nid2xname logs an error and exits when an APIError occurs."""
        self.mock_hsm_client.get_node_components.side_effect = APIError('HSM failed')
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_HSM_API_FAILED)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.assert_in_element('Request to HSM API failed: HSM failed', logs.output)
        self.mock_print.assert_not_called()

    def test_nid2xname_invalid_hsm_data_error(self):
        """Test nid2xname logs an error and exits non-zero when invalid data from HSM occurs."""
        self.fake_args.nids = ['nid1075']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_nid2xname(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.assert_in_element('HSM API has no ID for valid NID: 1075', logs.output)
        self.assert_in_element('xname: MISSING, nid: 1075', logs.output)
        self.mock_print.assert_not_called()


if __name__ == '__main__':
    unittest.main()
