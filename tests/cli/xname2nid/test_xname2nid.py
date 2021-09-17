"""
Unit tests for the sat.cli.xname2nid module.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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

import logging
import unittest
from argparse import Namespace
from unittest import mock

from sat.apiclient import APIError
from sat.cli.xname2nid.main import (
    ERR_HSM_API_FAILED,
    ERR_MISSING_NAMES,
    do_xname2nid
)
from tests.common import ExtendedTestCase


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.xnames = ['x1000c0s1b0n1']
    namespace.format = 'range'


class TestDoXname2nid(ExtendedTestCase):
    """Unit test for xname2nid"""

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
             'Type': 'Node',
             'ID': 'x1000c2s2b1n0'},
            {'NID': 1076,
             'Type': 'Node',
             'ID': 'x1000c2s2b1n1'}
        ]
        self.mock_hsm_client = mock.patch('sat.cli.xname2nid.main.HSMClient',
                                          autospec=True).start().return_value
        self.mock_hsm_client.get_node_components.return_value = self.node_data

        self.mock_sat_session = mock.patch('sat.cli.xname2nid.main.SATSession').start()
        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.fake_args = Namespace()
        set_options(self.fake_args)

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_one_node_xname_exists(self):
        """Test do_xname2nid with one valid node xname."""
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        self.assert_in_element(f'xname: {self.node_data[0]["ID"]}, nid: {self.node_data[0]["NID"]}',
                               logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid001006')

    def test_one_node_bmc_xname_exists(self):
        """Test do_xname2nid with one valid node BMC xname."""
        self.fake_args.xnames = ['x1000c2s2b0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[2:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001073-001074]')

    def test_one_node_bmc_xname_exists_nid_output(self):
        """Test do_xname2nid with one valid node BMC xname with nid output."""
        self.fake_args.xnames = ['x1000c2s2b0']
        self.fake_args.format = 'nid'
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[2:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid001073,nid001074')

    def test_one_slot_xname_exists(self):
        """Test do_xname2nid with one valid slot xname."""
        self.fake_args.xnames = ['x1000c2s2']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[2:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001073-001076]')

    def test_one_chassis_xname_exists(self):
        """Test do_xname2nid with one valid chassis xname."""
        self.fake_args.xnames = ['x1000c2']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073-001076]')

    def test_one_chassis_xname_exists_nid_output(self):
        """Test do_xname2nid with one valid chassis xname with nid output."""
        self.fake_args.xnames = ['x1000c2']
        self.fake_args.format = 'nid'
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid001069,nid001073,nid001074,nid001075,nid001076')

    def test_one_cabinet_xname_exists(self):
        """Test do_xname2nid with one valid cabinet xname."""
        self.fake_args.xnames = ['x1000']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[0:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with(
            'nid[001006,001069,001073-001076]'
        )

    def test_one_xname_not_exists(self):
        """Test do_xname2nid with one invalid xname."""
        self.fake_args.xnames = ['x1000c2s1b0n5']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_xname2nid(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.assert_in_element(f'xname: {self.fake_args.xnames[0]}, nid: MISSING', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_not_called()

    def test_two_node_xnames_exist(self):
        """Test do_xname2nid with two valid node xnames."""
        self.fake_args.xnames = ['x1000c2s1b0n0', 'x1000c2s2b0n0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:2]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073]')

    def test_two_comma_separated_node_xnames_exist(self):
        """Test do_xname2nid with two valid comma separated node xnames."""
        self.fake_args.xnames = ['x1000c2s1b0n0,x1000c2s2b0n0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:2]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073]')

    def test_two_node_and_bmc_xnames_exist(self):
        """Test do_xname2nid with two valid node and BMC xnames."""
        self.fake_args.xnames = ['x1000c2s1b0n0', 'x1000c2s2b0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073-001074]')

    def test_one_node_and_one_bmc_xnames_with_duplicates(self):
        """Test do_xname2nid with one valid node and one BMC xnames with duplicates."""
        self.fake_args.xnames = ['x1000c0s1b0n1', 'x1000c0s1b0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        self.assert_in_element(f'xname: {self.node_data[0]["ID"]}, nid: {self.node_data[0]["NID"]}',
                               logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid001006')

    def test_one_node_and_one_bmc_xnames_with_duplicates_nid_output(self):
        """Test do_xname2nid with one valid node and one BMC xnames with duplicates with nid output."""
        self.fake_args.xnames = ['x1000c0s1b0n1', 'x1000c0s1b0']
        self.fake_args.format = 'nid'
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        self.assert_in_element(f'xname: {self.node_data[0]["ID"]}, nid: {self.node_data[0]["NID"]}',
                               logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid001006,nid001006')

    def test_one_node_and_slot_xnames_exist(self):
        """Test do_xname2nid with one valid node and one valid slot xnames."""
        self.fake_args.xnames = ['x1000c2s1b0n0', 'x1000c2s2']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073-001076]')

    def test_one_node_and_one_slot_xnames_with_duplicates(self):
        """Test do_xname2nid with one valid node and one slot xnames with duplicates."""
        self.fake_args.xnames = ['x1000c2s2b0n1', 'x1000c2s2']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        self.assert_in_element(f'xname: {self.node_data[3]["ID"]}, nid: {self.node_data[3]["NID"]}',
                               logs.output)
        for node in self.node_data[2:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001073-001076]')

    def test_one_node_and_one_slot_xnames_with_duplicates_nid_output(self):
        """Test do_xname2nid with one valid node and one slot xnames with duplicates with nid output."""
        self.fake_args.xnames = ['x1000c2s2b0n1', 'x1000c2s2']
        self.fake_args.format = 'nid'
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        self.assert_in_element(f'xname: {self.node_data[3]["ID"]}, nid: {self.node_data[3]["NID"]}',
                               logs.output)
        for node in self.node_data[2:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid001074,nid001073,nid001074,nid001075,nid001076')

    def test_one_node_and_chassis_xnames_exist(self):
        """Test do_xname2nid with one valid node and one valid chassis xnames."""
        self.fake_args.xnames = ['x1000c0s1b0n1', 'x1000c2']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[0:5]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with(
            'nid[001006,001069,001073-001076]'
        )

    def test_two_comma_separated_node_and_bmc_xnames_exist(self):
        """Test do_xname2nid with two valid comma separated node and BMC xnames."""
        self.fake_args.xnames = ['x1000c2s1b0n0,x1000c2s2b0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073-001074]')

    def test_two_comma_separated_node_xnames_with_space_exist(self):
        """Test do_xname2nid with two valid comma separated node xnames with space."""
        self.fake_args.xnames = ['x1000c2s1b0n0,', 'x1000c2s2b0n0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            do_xname2nid(self.fake_args)
        for node in self.node_data[1:2]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073]')

    def test_three_node_xnames_one_invalid(self):
        """Test do_xname2nid with two valid node xnames and one invalid string."""
        self.fake_args.xnames = ['x1000c2s1b0n0', 'not-an-xname', 'x1000c2s2b0n0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_xname2nid(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        for node in self.node_data[1:2]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.assert_in_element(f'xname: {self.fake_args.xnames[1]}, nid: MISSING', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073]')

    def test_three_node_and_bmc_xnames_one_invalid(self):
        """Test do_xname2nid with two valid node and BMC xnames and one invalid string."""
        self.fake_args.xnames = ['x1000c2s1b0n0', 'not-an-xname', 'x1000c2s2b0']
        with self.assertLogs(level=logging.DEBUG) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_xname2nid(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        for node in self.node_data[1:3]:
            self.assert_in_element(f'xname: {node["ID"]}, nid: {node["NID"]}', logs.output)
        self.assert_in_element(f'xname: {self.fake_args.xnames[1]}, nid: MISSING', logs.output)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.mock_print.assert_called_once_with('nid[001069,001073-001074]')

    def test_xname2nid_api_error(self):
        """Test xname2nid logs an error and exits when an APIError occurs."""
        self.mock_hsm_client.get_node_components.side_effect = APIError('HSM failed')
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_xname2nid(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_HSM_API_FAILED)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.assert_in_element('Request to HSM API failed: HSM failed', logs.output)
        self.mock_print.assert_not_called()

    def test_xname2nid_node_xname_invalid_hsm_data_error(self):
        """Test xname2nid with node xname logs an error and exits non-zero when invalid data from HSM occurs."""
        self.mock_hsm_client.get_node_components.return_value = [
            {'Type': 'Node', 'ID': 'x1000c2s2b0n2'}
        ]
        self.fake_args.xnames = ['x1000c2s2b0n2']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_xname2nid(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.assert_in_element('HSM API has no NID for valid node xname: x1000c2s2b0n2', logs.output)
        self.assert_in_element('xname: x1000c2s2b0n2, nid: MISSING', logs.output)
        self.mock_print.assert_not_called()

    def test_xname2nid_node_bmc_xname_invalid_hsm_data_error(self):
        """Test xname2nid with node BMC xname logs an error and exits non-zero when invalid data from HSM occurs."""
        self.mock_hsm_client.get_node_components.return_value = [
            {'NID': 1073, 'Type': 'Node', 'ID': 'x1000c2s2b0n0'},
            {'NID': 1074, 'Type': 'Node', 'ID': 'x1000c2s2b0n1'},
            {'Type': 'Node', 'ID': 'x1000c2s2b0n2'}
        ]
        self.fake_args.xnames = ['x1000c2s2b0']
        with self.assertLogs(level=logging.ERROR) as logs:
            with self.assertRaises(SystemExit) as cm:
                do_xname2nid(self.fake_args)
        self.assertEqual(cm.exception.code, ERR_MISSING_NAMES)
        self.mock_hsm_client.get_node_components.assert_called_once_with()
        self.assert_in_element('HSM API has no NID for valid node xname: x1000c2s2b0n2', logs.output)
        self.mock_print.assert_called_once_with('nid[001073-001074]')


if __name__ == '__main__':
    unittest.main()
