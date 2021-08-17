"""
Unit tests for sat.cli.firmware

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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

import argparse
import logging
import unittest
from unittest import mock

from tests.test_util import ExtendedTestCase

from sat.apiclient import APIError
from sat.fwclient import FASClient
from sat.cli.firmware.main import do_firmware
from sat.cli.firmware.parser import add_firmware_subparser


class TestFirmware(ExtendedTestCase):

    def setUp(self):
        """Set up mock objects and command parser"""
        # Fake args
        self.parser = argparse.ArgumentParser()
        self.subparser = self.parser.add_subparsers()
        add_firmware_subparser(self.subparser)

        self.firmware_client_cls = mock.patch('sat.cli.firmware.main.FASClient').start()
        self.firmware_client = self.firmware_client_cls.return_value
        self.firmware_client_cls.headers = FASClient.headers
        self.mock_snapshot_names = ['snap1', 'snap2', 'snap3']
        self.mock_snapshots = {
            'snap1': mock.Mock(),
            'snap2': mock.Mock(),
            'snap3': mock.Mock()
        }
        self.firmware_client.get_all_snapshot_names.return_value = set(self.mock_snapshot_names)

        # Fake report
        self.mock_report = mock.patch('sat.cli.firmware.main.Report').start()

        # Fake print
        self.mock_print = mock.patch('sat.cli.firmware.main.print').start()

        # Fake get_config_value
        self.fake_config = {
            'format.no_headings': False,
            'format.no_borders': True
        }
        self.mock_get_config_value = mock.patch('sat.cli.firmware.main.get_config_value',
                                                side_effect=self.fake_get_config_value).start()

    def tearDown(self):
        """Stop mock objects"""
        mock.patch.stopall()

    def fake_get_config_value(self, option):
        """Mimic get_config_value"""
        return self.fake_config.get(option)

    def assertFirmwareTables(self, data_list):
        """Assert that firmware tables were created"""
        self.firmware_client.make_fw_table.assert_has_calls([mock.call(data) for data in data_list], any_order=True)

    def assertReport(self, title, args, rows):
        """Assert that a report was created as specified with the correct data"""

        # Test that the Report was created
        report_args = [
            FASClient.headers, title, args.sort_by, args.reverse,
            self.fake_config['format.no_headings'],
            self.fake_config['format.no_borders']
        ]
        self.mock_get_config_value.assert_has_calls([mock.call('format.no_headings'), mock.call('format.no_borders')])
        report_kwargs = {'filter_strs': args.filter_strs, 'display_headings': args.fields, 'print_format': args.format}
        self.mock_report.assert_any_call(*report_args, **report_kwargs)

        # Test that the rows were added to the Report
        report_obj = self.mock_report.return_value
        report_obj.add_rows.assert_any_call(rows)

        # Test that the report was printed
        self.mock_print.assert_any_call(report_obj)

    def assertExitsWithError(self, function, args, error_message=None):
        """Assert that an error is logged and that the program exits with the expected error code."""
        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level='ERROR') as logs:
                function(args)
        if error_message:
            self.assert_in_element(error_message, logs.output)
        expected_exit_code = 1
        self.assertEqual(expected_exit_code, raises_cm.exception.code)

    def test_get_snapshots(self):
        """Running with --snapshots gets snapshot names and prints them."""
        args = self.parser.parse_args(['firmware', '--snapshots'])
        do_firmware(args)
        self.firmware_client.get_all_snapshot_names.assert_called_once()
        self.mock_print.assert_has_calls([mock.call(name) for name in self.mock_snapshot_names], any_order=True)

    def test_get_snapshot_names_error(self):
        """An APIError getting snapshot names logs an error and exits"""
        args = self.parser.parse_args(['firmware', '--snapshots'])
        self.firmware_client.get_all_snapshot_names.side_effect = APIError
        self.assertExitsWithError(do_firmware, args)

    def test_xname_and_snapshots_without_arguments(self):
        """When giving --xname and --snapshots with no arguments, warn that --xname is ignored."""
        args = self.parser.parse_args(['firmware', '--snapshots', '-x', 'x5000c0s3b0'])
        with self.assertLogs(level=logging.WARNING) as logs:
            do_firmware(args)
        self.firmware_client.get_all_snapshot_names.assert_called_once_with()
        self.mock_print.assert_has_calls([mock.call(name) for name in self.mock_snapshot_names], any_order=True)
        self.assert_in_element(
            '--snapshots was given with no arguments. The value of -x/--xname will be ignored.',
            logs.output
        )

    def test_get_snapshots_error(self):
        """An APIError getting snapshot data logs an error and exits"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'foo'])
        self.firmware_client.get_multiple_snapshot_devices.side_effect = APIError
        self.assertExitsWithError(do_firmware, args)

    def test_get_known_snapshots(self):
        """Getting a known snapshot produces a report for that snapshot"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'snap1'])
        self.firmware_client.get_multiple_snapshot_devices.return_value = {'snap1': self.mock_snapshots['snap1']}
        do_firmware(args)
        self.firmware_client.get_multiple_snapshot_devices.assert_called_once_with(args.snapshots, None)
        self.assertFirmwareTables([self.mock_snapshots['snap1']])
        self.assertReport('snap1', args, self.firmware_client.make_fw_table.return_value)

    def test_get_known_snapshot_with_xname(self):
        """Getting a known snapshot with an xname produces a report for that snapshot and xname"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'snap1', '--xname', 'x3000c0s2b0'])
        self.firmware_client.get_multiple_snapshot_devices.return_value = {'snap1': self.mock_snapshots['snap1']}
        do_firmware(args)
        self.firmware_client.get_multiple_snapshot_devices.assert_called_once_with(args.snapshots, ['x3000c0s2b0'])
        self.assertFirmwareTables([self.mock_snapshots['snap1']])
        self.assertReport('snap1', args, self.firmware_client.make_fw_table.return_value)

    def test_get_multiple_known_snapshots(self):
        """Getting multiple known snapshots produces a report for those snapshots"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'snap1', 'snap2'])
        self.firmware_client.get_multiple_snapshot_devices.return_value = {
            'snap1': self.mock_snapshots['snap1'],
            'snap2': self.mock_snapshots['snap2']
        }
        do_firmware(args)
        self.firmware_client.get_multiple_snapshot_devices.assert_called_once_with(args.snapshots, None)
        self.assertFirmwareTables([self.mock_snapshots['snap1'], self.mock_snapshots['snap2']])
        self.assertReport('snap1', args, self.firmware_client.make_fw_table.return_value)
        self.assertReport('snap2', args, self.firmware_client.make_fw_table.return_value)

    def test_get_all_firmware(self):
        """Getting all firmware uses get_device_firmwares to produce a report."""
        args = self.parser.parse_args(['firmware'])
        do_firmware(args)
        self.firmware_client.get_device_firmwares.assert_called_once_with(None)
        self.assertFirmwareTables([self.firmware_client.get_device_firmwares.return_value])
        self.assertReport(None, args, self.firmware_client.make_fw_table.return_value)

    def test_get_all_firmware_error(self):
        """An APIError getting all firmware exits with an error."""
        args = self.parser.parse_args(['firmware'])
        self.firmware_client.get_device_firmwares.side_effect = APIError('No firmware found.')
        self.assertExitsWithError(do_firmware, args, 'No firmware found.')

    def test_get_firmware_xname(self):
        """Getting firmware by xname produces a report for the xname"""
        args = self.parser.parse_args(['firmware', '-x', 'x5000c0s3b0'])
        do_firmware(args)
        self.firmware_client.get_device_firmwares.assert_called_once_with(args.xnames)
        self.assertFirmwareTables([self.firmware_client.get_device_firmwares.return_value])
        self.assertReport(None, args, self.firmware_client.make_fw_table.return_value)

    def test_get_firmware_multiple_xnames(self):
        """Getting firmware for several xnames produces a report for them."""
        args = self.parser.parse_args(['firmware', '-x', 'x3000c0s2b0', '-x', 'x5000c0s3b0', ])
        do_firmware(args)
        self.firmware_client.get_device_firmwares.assert_called_once_with(args.xnames)
        self.assertFirmwareTables([self.firmware_client.get_device_firmwares.return_value])
        self.assertReport(None, args, self.firmware_client.make_fw_table.return_value)

    def test_get_firmware_xname_api_error(self):
        """An API Error getting firmware by xname exits with an error."""
        args = self.parser.parse_args(['firmware', '-x', 'x3000c0s0b0'])
        self.firmware_client.get_device_firmwares.side_effect = APIError('No firmware found.')
        self.assertExitsWithError(do_firmware, args, 'No firmware found.')


if __name__ == '__main__':
    unittest.main()
