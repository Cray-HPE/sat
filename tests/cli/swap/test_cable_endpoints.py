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
Unit tests for sat.cli.swap.cable_endpoints
"""

import logging
import os
import unittest
from unittest import mock

from sat.cli.swap.cable_endpoints import CableEndpoints

P2P_DIR = os.path.join(os.path.dirname(__file__), '../..', 'resources/slingshot/')


class TestCableEndpoints(unittest.TestCase):
    """Unit tests for the sat.cli.swap.cable_endpoints.CableEndpoints class"""

    def setUp(self):
        """Mock functions called."""

        self.mock_copy_shasta_p2p_file = mock.patch(
            'sat.cli.swap.cable_endpoints.CableEndpoints.copy_shasta_p2p_file',
            autospec=True).start()
        self.mock_copy_shasta_p2p_file.return_value = True

        self.cable_endpoints = CableEndpoints()
        self.cable_endpoints.dest_dir = P2P_DIR

    def load_valid_p2p_file_without_header(self):
        """Load and parse a Shasta p2p file without a header"""

        self.cable_endpoints.p2p_file = 'Shasta_system_hsn_pt_pt.valid.1.csv'
        return self.cable_endpoints.load_cables_from_p2p_file()

    def load_valid_p2p_file_with_header(self):
        """Load and parse a Shasta p2p file with a header"""

        self.cable_endpoints.p2p_file = 'Shasta_system_hsn_pt_pt.valid.2.csv'
        return self.cable_endpoints.load_cables_from_p2p_file()

    def test_load_valid_p2p_file(self):
        """Test load and parse of Shasta p2p file"""

        result = self.load_valid_p2p_file_without_header()
        self.assertEqual(result, True)

    def test_load_valid_p2p_file_with_header(self):
        """Test load and parse of Shasta p2p file with header"""

        result = self.load_valid_p2p_file_with_header()
        self.assertEqual(result, True)

    def test_load_invalid_p2p_file(self):
        """Test load and parse of an invalid Shasta p2p file"""

        self.cable_endpoints.p2p_file = 'Shasta_system_hsn_pt_pt.invalid.csv'
        result = self.cable_endpoints.load_cables_from_p2p_file()
        self.assertEqual(result, False)

    def test_get_local_cable(self):
        """Test get local cable data from Shasta p2p file"""

        self.load_valid_p2p_file_without_header()
        expected = {
            'src_conn_a': 'x9000c1r3j16',
            'src_conn_b': 'none',
            'dst_conn_a': 'x9000c3r5j16',
            'dst_conn_b': 'none'
        }
        result = self.cable_endpoints.get_cable('x9000c1r3j16')
        self.assertEqual(result, expected)

    def test_get_edge_cable(self):
        """Test get edge cable data from Shasta p2p file"""

        self.load_valid_p2p_file_without_header()
        expected = {
            'src_conn_a': 'x3000c0r15j14',
            'src_conn_b': 'none',
            'dst_conn_a': 'x3000c0s17b1n0h0',
            'dst_conn_b': 'x3000c0s04b1n0h1'
        }
        result = self.cable_endpoints.get_cable('x3000c0r15j14')
        self.assertEqual(result, expected)

    def test_get_cable_invalid_xname(self):
        """Test get cable data from Shasta p2p file using xname not in p2p file"""

        self.load_valid_p2p_file_without_header()
        result = self.cable_endpoints.get_cable('x9000c1r3j1600')
        self.assertEqual(result, None)

    def test_get_cable_with_p2p_file_with_header(self):
        """Test get cable data from Shasta p2p file with header"""

        self.load_valid_p2p_file_with_header()
        expected = {
            'src_conn_a': 'x3000c0r15j12',
            'src_conn_b': 'none',
            'dst_conn_a': 'x3000c0s19b1n0h0',
            'dst_conn_b': 'x3000c0s20b1n0h0'
        }
        result = self.cable_endpoints.get_cable('x3000c0r15j12')
        self.assertEqual(result, expected)

    def test_get_linked_jack_list_for_local_cable(self):
        """Test get local cable linked jack list from Shasta p2p file"""

        self.load_valid_p2p_file_without_header()
        expected = [
            'x9000c1r3j16',
            'x9000c3r5j16'
        ]
        result = self.cable_endpoints.get_linked_jack_list('x9000c1r3j16')
        self.assertEqual(result, expected)

    def test_get_linked_jack_list_for_edge_cable(self):
        """Test get edge cable linked jack list from Shasta p2p file"""

        self.load_valid_p2p_file_without_header()
        expected = [
            'x3000c0r15j14'
        ]
        result = self.cable_endpoints.get_linked_jack_list('x3000c0r15j14')
        self.assertEqual(result, expected)

    def test_get_linked_jack_list_for_cable_with_p2p_header(self):
        """Test get cable linked jack list from Shasta p2p file with header"""

        self.load_valid_p2p_file_with_header()
        expected = [
            'x3000c0r15j12'
        ]
        result = self.cable_endpoints.get_linked_jack_list('x3000c0r15j12')
        self.assertEqual(result, expected)

    def test_validate_jack_using_p2p_file(self):
        """Test validate_jacks_using_p2p_file() for one jack xname"""

        self.load_valid_p2p_file_without_header()
        result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j16'])
        self.assertEqual(result, True)

    def test_validate_jack_no_cables(self):
        """Test validate_jacks_using_p2p_file() for one jack xname without any data on cables"""

        with self.assertLogs(level=logging.WARNING) as warning_msg:
            result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j16'])
        self.assertEqual(result, False)
        self.assertEqual(1, len(warning_msg.output))
        self.assertIn('No cable data available from p2p file', warning_msg.output[0])

    def test_validate_invalid_jack_using_p2p_file(self):
        """Test validate_jacks_using_p2p_file() for one jack xname not in p2p file"""

        self.load_valid_p2p_file_without_header()
        with self.assertLogs(level=logging.WARNING) as warning_msg:
            result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j1600'])
        self.assertEqual(result, False)
        self.assertEqual(1, len(warning_msg.output))
        self.assertIn('Jack data for x9000c1r3j1600 not available from p2p file', warning_msg.output[0])

    def test_validate_single_cable_jacks_using_p2p_file(self):
        """Test validate_jacks_using_p2p_file() for two jack xnames for single cable"""

        self.load_valid_p2p_file_without_header()
        result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j16', 'x9000c3r5j16'])
        self.assertEqual(result, True)

    def test_validate_invalid_jack_in_list_using_p2p_file(self):
        """Test validate_jacks_using_p2p_file() for one invalid jack xname in list of xnames"""

        self.load_valid_p2p_file_without_header()
        with self.assertLogs(level=logging.WARNING) as warning_msg:
            result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j16', 'x9000c1r3j1600'])
        self.assertEqual(result, False)
        self.assertEqual(1, len(warning_msg.output))
        self.assertIn('Jack data for x9000c1r3j1600 not available from p2p file', warning_msg.output[0])

    def test_validate_two_invalid_jacks_in_list_using_p2p_file(self):
        """Test validate_jacks_using_p2p_file() for two invalid jack xnames in list of xnames"""

        self.load_valid_p2p_file_without_header()
        with self.assertLogs(level=logging.WARNING) as warning_msg:
            result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j16',
                                                                         'x9000c1r3j1600',
                                                                         'x9000c1r3j1601'])
        self.assertEqual(result, False)
        self.assertEqual(2, len(warning_msg.output))
        self.assertIn('Jack data for x9000c1r3j1600 not available from p2p file', warning_msg.output[0])
        self.assertIn('Jack data for x9000c1r3j1601 not available from p2p file', warning_msg.output[1])

    def test_validate_two_cables_with_jacks_using_p2p_file(self):
        """Test validate_jacks_using_p2p_file() for two jack xnames for two cables"""

        self.load_valid_p2p_file_without_header()
        with self.assertLogs(level=logging.WARNING) as warning_msg:
            result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j16', 'x9000c3r3j16'])
        self.assertEqual(result, False)
        self.assertEqual(1, len(warning_msg.output))
        self.assertIn('Jacks x9000c1r3j16,x9000c3r3j16 are not connected by a single cable',
                      warning_msg.output[0])

    def test_validate_two_cables_with_multiple_jacks_using_p2p_file(self):
        """Test validate_jacks_using_p2p_file() for four jack xnames for two cables"""

        self.load_valid_p2p_file_without_header()
        with self.assertLogs(level=logging.WARNING) as warning_msg:
            result = self.cable_endpoints.validate_jacks_using_p2p_file(['x9000c1r3j16', 'x9000c3r5j16',
                                                                         'x9000c1r3j18', 'x9000c3r3j16'])
        self.assertEqual(result, False)
        self.assertEqual(1, len(warning_msg.output))
        self.assertIn(
            'Jacks x9000c1r3j16,x9000c3r5j16,x9000c1r3j18,x9000c3r3j16 are not connected by a single cable',
            warning_msg.output[0])

    def tearDown(self):
        mock.patch.stopall()


if __name__ == '__main__':
    unittest.main()
