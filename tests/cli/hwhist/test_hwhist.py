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
Unit tests for the sat.cli.xname2nid module.
"""

import logging
import unittest
from argparse import Namespace
from unittest import mock

from sat.apiclient import APIError
from sat.cli.hwhist.hwhist_fields import (
    BY_FRU_FIELD_MAPPING,
    BY_LOCATION_FIELD_MAPPING
)
from sat.cli.hwhist.main import (
    do_hwhist,
    make_raw_table
)
from sat.xname import XName

from tests.common import ExtendedTestCase


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.xnames = None
    namespace.fruids = None
    namespace.by_fru = False
    namespace.sort_by = 0
    namespace.reverse = False
    namespace.filter_strs = None
    namespace.format = 'pretty'
    namespace.fields = None


class TestDoHwhist(ExtendedTestCase):
    """Unit tests for hwhist"""

    def setUp(self):
        """Mock functions called."""
        self.mock_history_data = [
            {
                "ID": "x3000c0s3b0n0p0",
                "History": [
                    {
                        "ID": "x3000c0s3b0n0p0",
                        "FRUID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6",
                        "Timestamp": "2021-06-02T18:37:31.619581Z",
                        "EventType": "Detected"
                    },
                    {
                        "ID": "x3000c0s3b0n0p0",
                        "FRUID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D7",
                        "Timestamp": "2021-06-16T14:42:49.528142Z",
                        "EventType": "Detected"
                    }
                ]
            },
            {
                "ID": "x3000c0s3b0n1p0",
                "History": [
                    {
                        "ID": "x3000c0s3b0n1p0",
                        "FRUID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6",
                        "Timestamp": "2021-06-16T14:42:49.528142Z",
                        "EventType": "Detected"
                    }
                ]
            }
        ]

        self.mock_history_by_fru_data = [
            {
                "ID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6",
                "History": [
                    {
                        "ID": "x3000c0s3b0n0p0",
                        "FRUID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6",
                        "Timestamp": "2021-06-02T18:37:31.619581Z",
                        "EventType": "Detected"
                    },
                    {
                        "ID": "x3000c0s3b0n1p0",
                        "FRUID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6",
                        "Timestamp": "2021-06-16T14:42:49.528142Z",
                        "EventType": "Detected"
                    }
                ]
            },
            {
                "ID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D7",
                "History": [
                    {
                        "ID": "x3000c0s3b0n0p0",
                        "FRUID": "Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D7",
                        "Timestamp": "2021-06-16T14:42:49.528142Z",
                        "EventType": "Detected"
                    }
                ]
            }
        ]

        self.mock_hsm_client = mock.patch('sat.cli.hwhist.main.HSMClient',
                                          autospec=True).start().return_value
        self.mock_hsm_client.get_component_history.return_value = self.mock_history_data

        self.mock_sat_session = mock.patch('sat.cli.hwhist.main.SATSession').start()
        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.fake_args = Namespace()
        set_options(self.fake_args)

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_hwhist(self):
        """Test do_hwhist with no options."""
        do_hwhist(self.fake_args)
        self.mock_hsm_client.get_component_history.assert_called_once_with(by_fru=False, cids=None)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_hwhist_by_fru(self):
        """Test do_hwhist by_fru including all fruids."""
        self.fake_args.by_fru = True
        self.mock_hsm_client.get_component_history.return_value = self.mock_history_by_fru_data
        do_hwhist(self.fake_args)
        self.mock_hsm_client.get_component_history.assert_called_once_with(by_fru=True, cids=None)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_hwhist_one_bad_xname(self):
        """Test do_hwhist with invalid xname."""
        self.fake_args.xnames = ['x3000c0s3b0n1p0_bad']
        with self.assertLogs(level=logging.WARNING) as mylogs:
            do_hwhist(self.fake_args)
        self.assert_in_element(
            f'{set(self.fake_args.xnames)} '
            f'not available from HSM hardware component history API.',
            mylogs.output)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_hwhist_one_bad_fruid(self):
        """Test do_hwhist with invalid fruid."""
        self.fake_args.fruids = ['NotaFRUID']
        with self.assertLogs(level=logging.WARNING) as mylogs:
            do_hwhist(self.fake_args)
        self.assert_in_element(
            f'{set(self.fake_args.fruids)} '
            f'not available from HSM hardware component history API.',
            mylogs.output)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_make_raw_table(self):
        """Test make_raw_table with all history data by xname."""
        expected_output = [
            [XName('x3000c0s3b0n0p0'), 'Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6',
             '2021-06-02T18:37:31.619581Z', 'Detected'],
            [XName('x3000c0s3b0n0p0'), 'Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D7',
             '2021-06-16T14:42:49.528142Z', 'Detected'],
            [XName('x3000c0s3b0n1p0'), 'Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6',
             '2021-06-16T14:42:49.528142Z', 'Detected']
        ]
        raw_table = make_raw_table(self.mock_history_data, BY_LOCATION_FIELD_MAPPING)
        self.assertEqual(raw_table, expected_output)

    def test_make_raw_table_by_fru(self):
        """Test make_raw_table with all history data by fru."""
        expected_output = [
            ['Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6', XName('x3000c0s3b0n0p0'),
             '2021-06-02T18:37:31.619581Z', 'Detected'],
            ['Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6', XName('x3000c0s3b0n1p0'),
             '2021-06-16T14:42:49.528142Z', 'Detected'],
            ['Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D7', XName('x3000c0s3b0n0p0'),
             '2021-06-16T14:42:49.528142Z', 'Detected']
        ]
        raw_table = make_raw_table(self.mock_history_by_fru_data, BY_FRU_FIELD_MAPPING)
        self.assertEqual(raw_table, expected_output)


if __name__ == '__main__':
    unittest.main()
