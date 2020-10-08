"""
Unit tests for sat.cli.firmware

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

import argparse
import unittest
from unittest import mock

from sat.apiclient import APIError
from sat.cli.firmware.main import do_firmware, HEADERS
from sat.cli.firmware.parser import add_firmware_subparser


class TestFirmware(unittest.TestCase):

    def setUp(self):
        """Set up mock objects and command parser"""
        # Fake args
        self.parser = argparse.ArgumentParser()
        self.subparser = self.parser.add_subparsers()
        add_firmware_subparser(self.subparser)

        # Fake firmware client
        self.fake_snaps = {
            'foo': {},
            'bar': {}
        }
        self.create_firmware_client = mock.patch('sat.cli.firmware.main.create_firmware_client').start()
        self.firmware_client = self.create_firmware_client.return_value
        self.firmware_client.get_all_snapshot_names.return_value = {'foo', 'bar'}
        self.firmware_client.get_snapshots.side_effect = self.fake_get_snapshots
        self.device_firmwares = self.firmware_client.get_device_firmwares.return_value
        self.fake_firmware_rows = [['abc', 'def', 'ghi'],
                                   ['123', '456', '789']]
        self.firmware_client.make_fw_table.return_value = self.fake_firmware_rows

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

    def fake_get_snapshots(self, snapshot_names):
        """Mimic get_snapshots, which returns all matching snapshots"""
        return {k: v for k, v in self.fake_snaps.items() if k in snapshot_names}

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
            HEADERS, title, args.sort_by, args.reverse,
            self.fake_config['format.no_headings'],
            self.fake_config['format.no_borders']
        ]
        self.mock_get_config_value.assert_has_calls([mock.call('format.no_headings'), mock.call('format.no_borders')])
        report_kwargs = {'filter_strs': args.filter_strs}
        self.mock_report.assert_any_call(*report_args, **report_kwargs)

        # Test that the rows were added to the Report
        report_obj = self.mock_report.return_value
        report_obj.add_rows.assert_any_call(rows)

        # Test that the report was printed
        self.mock_print.assert_any_call(report_obj)

    def assertExitsWithError(self, function, args):
        """Assert that an error is logged and that the program exits"""
        with self.assertRaises(SystemExit):
            with self.assertLogs(level='ERROR'):
                function(args)

    def test_client_creation_fail(self):
        """A failure to create a firmware client should log an error and exit"""
        args = self.parser.parse_args(['firmware'])
        self.create_firmware_client.side_effect = APIError
        self.assertExitsWithError(do_firmware, args)

    def test_get_snapshots(self):
        """Running with --snapshots gets snapshot names and prints them"""
        args = self.parser.parse_args(['firmware', '--snapshots'])
        do_firmware(args)
        self.firmware_client.get_all_snapshot_names.assert_called_once()
        self.mock_print.assert_has_calls([mock.call('foo'), mock.call('bar')], any_order=True)

    def test_get_snapshot_names_error(self):
        """An APIError getting snapshot names logs an error and exits"""
        args = self.parser.parse_args(['firmware', '--snapshots'])
        self.firmware_client.get_all_snapshot_names.side_effect = APIError
        self.assertExitsWithError(do_firmware, args)

    def test_get_snapshots_error(self):
        """An APIError getting snapshot data logs an error and exits"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'foo'])
        self.firmware_client.get_snapshots.side_effect = APIError
        self.assertExitsWithError(do_firmware, args)

    def test_get_known_snapshot(self):
        """Getting a known snapshot produces a report for that snapshot"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'foo'])
        do_firmware(args)
        self.firmware_client.get_all_snapshot_names.assert_called_once_with()
        self.firmware_client.get_snapshots.assert_called_once_with(args.snapshots)
        self.assertFirmwareTables([self.fake_snaps['foo']])
        self.assertReport('foo', args, self.fake_firmware_rows)

    def test_get_multiple_known_snapshots(self):
        """Getting multiple known snapshots produces a report for those snapshots"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'foo', 'bar'])
        do_firmware(args)
        self.firmware_client.get_snapshots.assert_called_once_with(args.snapshots)
        self.assertFirmwareTables([self.fake_snaps['foo'], self.fake_snaps['bar']])
        self.assertReport('foo', args, self.fake_firmware_rows)
        self.assertReport('bar', args, self.fake_firmware_rows)

    def test_get_unknown_snapshot(self):
        """Getting an unknown snapshot prints nothing"""
        # In real operation, the firmware client prints a warning for each snapshot that does not exist
        args = self.parser.parse_args(['firmware', '--snapshots', 'doesNotExist'])
        do_firmware(args)
        self.firmware_client.make_fw_table.assert_not_called()
        self.mock_report.assert_not_called()

    def test_get_one_unknown_snapshot(self):
        """Getting one unknown snapshot and one known prints a table for the known one"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'doesNotExist', 'foo'])
        do_firmware(args)
        self.assertFirmwareTables([self.fake_snaps['foo']])
        self.assertReport('foo', args, self.fake_firmware_rows)

    def test_get_no_known_snapshots(self):
        """Getting a snapshot when no snapshots exist logs an error and exits"""
        args = self.parser.parse_args(['firmware', '--snapshots', 'foo'])
        self.firmware_client.get_all_snapshot_names.return_value = set()
        self.assertExitsWithError(do_firmware, args)

    def test_get_firmware_xname(self):
        """Getting firmware by xname produces a report for the xname"""
        args = self.parser.parse_args(['firmware', '-x', 'x5000c3r3b0'])
        do_firmware(args)
        self.firmware_client.get_device_firmwares.assert_called_once_with(*args.xnames)
        self.assertFirmwareTables(self.device_firmwares)
        self.assertReport(None, args, self.fake_firmware_rows)

    def test_get_firmware_multiple_xnames(self):
        """Getting firmware for several xnames produces a report for them"""
        args = self.parser.parse_args(['firmware', '-x', 'x5000c3r3b0', '-x', 'x5000c3r1b0'])
        do_firmware(args)
        self.assertFirmwareTables(self.device_firmwares)
        self.firmware_client.get_device_firmwares.assert_has_calls([mock.call(xname) for xname in args.xnames],
                                                                   any_order=True)

        # Because firmware rows were returned once for each xname, assert that the table has two sets of rows
        self.assertReport(None, args, self.fake_firmware_rows * 2)

    def test_get_firmware_xname_api_error(self):
        """An API Error getting firmware by xname exits with an error"""
        args = self.parser.parse_args(['firmware', '-x', 'x5000c3r3b0'])
        self.firmware_client.get_device_firmwares.side_effect = APIError
        self.assertExitsWithError(do_firmware, args)

    def test_get_firmware_unknown_xname(self):
        """Getting firmware with an unknown xname exits with an error"""
        args = self.parser.parse_args(['firmware', '-x', 'doesNotExist'])
        # Given an unknown xname, the client returns an empty list
        self.firmware_client.get_device_firmwares.return_value = []
        self.assertExitsWithError(do_firmware, args)
        self.firmware_client.get_device_firmwares.assert_called_once_with(*args.xnames)

    def test_get_complete_firmware(self):
        """Getting firmware for everything produces a big report"""
        args = self.parser.parse_args(['firmware'])
        do_firmware(args)
        self.firmware_client.get_device_firmwares.assert_called_once_with()
        self.assertFirmwareTables(self.device_firmwares)
        self.assertReport(None, args, self.fake_firmware_rows)

    def test_get_complete_firmware_api_error(self):
        """An APIError when producing a full report exits with an error"""
        args = self.parser.parse_args(['firmware'])
        self.firmware_client.get_device_firmwares.side_effect = APIError
        self.assertExitsWithError(do_firmware, args)


if __name__ == '__main__':
    unittest.main()
