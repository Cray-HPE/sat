"""
Unit tests for sat.cli.firmware

Copyright 2020 Cray Inc. All Rights Reserved.
"""

import unittest
from unittest import mock
from argparse import Namespace
from sat.apiclient import APIError
import sat.cli.firmware.main


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.xname = []
    namespace.no_borders = True
    namespace.no_headings = False
    namespace.format = 'pretty'
    namespace.reverse = object()
    namespace.sort_by = object()
    namespace.filter_strs = object()


class TestDoFirmware(unittest.TestCase):
    """Unit test for Firmware do_firmware()."""

    def setUp(self):
        """Mock everything tested elsewhere (plus the builtin print)."""
        # Mock the FirmwareClient to return some valid data. If a test wishes to
        # change the mock_fw_data, the test should do something like:
        #     self.mock_fw_response.json.return_value = {'foo': 'bar'}

        # The data that will be returned by the firmware response's JSON method
        self.mock_fw_data = {
            'devices': [
                {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '1.0'}]}
            ]
        }
        self.mock_fw_response = mock.Mock()
        self.mock_fw_response.json.return_value = self.mock_fw_data

        self.mock_fw_client = mock.Mock()
        self.mock_fw_client.get.return_value = self.mock_fw_response
        self.mock_fw_client_cls = mock.patch('sat.cli.firmware.main.FirmwareClient',
                                             return_value=self.mock_fw_client).start()

        self.mock_make_fw_table = mock.patch('sat.cli.firmware.main.make_fw_table',
                                             autospec=True).start()
        self.mock_make_fw_table.return_value = [['a', 'table', 'row'],
                                                ['another', 'table', 'row']]

        self.mock_report_cls = mock.patch('sat.cli.firmware.main.Report',
                                          autospec=True).start()
        self.mock_report_obj = self.mock_report_cls.return_value

        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.parsed = Namespace()
        set_options(self.parsed)

        self.mock_config_values = {
            'format.no_headings': True,
            'format.no_borders': False
        }
        self.mock_get_config_value = mock.patch('sat.cli.firmware.main.get_config_value',
                                                side_effect=lambda x: self.mock_config_values[x],
                                                autospec=True).start()

    def tearDown(self):
        mock.patch.stopall()

    def test_success(self):
        """Test Firmware: do_firmware() success"""
        sat.cli.firmware.main.do_firmware(self.parsed)
        self.mock_make_fw_table.assert_called_once_with(self.mock_fw_data['devices'])
        self.mock_report_cls.assert_called_once_with(
            sat.cli.firmware.main.HEADERS, None,
            self.parsed.sort_by, self.parsed.reverse,
            self.mock_config_values['format.no_headings'],
            self.mock_config_values['format.no_borders'],
            filter_strs=self.parsed.filter_strs
        )
        self.mock_report_obj.add_rows.assert_called_once_with(self.mock_make_fw_table.return_value)
        self.mock_print.assert_called_once_with(self.mock_report_obj)

    def test_success_yaml(self):
        """Test Firmware: do_firmware() success with yaml output"""
        self.parsed.format = 'yaml'
        sat.cli.firmware.main.do_firmware(self.parsed)
        self.mock_make_fw_table.assert_called_once_with(self.mock_fw_data['devices'])
        self.mock_report_cls.assert_called_once_with(
            sat.cli.firmware.main.HEADERS, None,
            self.parsed.sort_by, self.parsed.reverse,
            self.mock_config_values['format.no_headings'],
            self.mock_config_values['format.no_borders'],
            filter_strs=self.parsed.filter_strs
        )
        self.mock_report_obj.add_rows.assert_called_once_with(self.mock_make_fw_table.return_value)
        self.mock_print.assert_called_once()
        self.mock_report_obj.get_yaml.assert_called_once_with()

    def test_api_error(self):
        """Test Firmware: do_firmware() api error"""
        self.mock_fw_client.get.side_effect = APIError
        with self.assertRaises(SystemExit):
            sat.cli.firmware.main.do_firmware(self.parsed)
        self.mock_fw_client.get.side_effect = None

    def test_value_error(self):
        """Test Firmware: do_firmware() value error getting json"""
        self.mock_fw_response.json.side_effect = ValueError
        with self.assertRaises(SystemExit):
            sat.cli.firmware.main.do_firmware(self.parsed)
        self.mock_fw_client.get.side_effect = None

    def test_get_empty_json(self):
        """Test Firmware: do_firmware() get empty json"""
        self.mock_fw_response.json.return_value = {}
        with self.assertRaises(SystemExit):
            sat.cli.firmware.main.do_firmware(self.parsed)

    def test_xnames_success(self):
        """Test Firmware: do_firmware() xnames success"""
        mock_json = [
            {'devices': [
                {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]},
            {'devices': [
                {'xname': 'x3000c0s1b1', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]},
            {'devices': [
                {'xname': 'x3000c0s1b2', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]}
        ]
        self.mock_fw_response.json.side_effect = mock_json
        self.parsed.xname = ['x3000c0s1b0, x3000c0s1b1', 'x3000c0s1b2']
        sat.cli.firmware.main.do_firmware(self.parsed)
        make_fw_table_args = [data['devices'] for data in mock_json]
        # Allow any order because mock inserts calls involving call().__radd__([]).
        self.mock_make_fw_table.assert_has_calls(
            [mock.call(arg) for arg in make_fw_table_args], any_order=True
        )
        self.mock_report_cls.assert_called_once_with(
            sat.cli.firmware.main.HEADERS, None,
            self.parsed.sort_by, self.parsed.reverse,
            self.mock_config_values['format.no_headings'],
            self.mock_config_values['format.no_borders'],
            filter_strs=self.parsed.filter_strs
        )
        self.mock_report_obj.add_rows.assert_called_once_with(
            self.mock_make_fw_table.return_value * len(mock_json)
        )
        self.mock_print.assert_called_once_with(self.mock_report_obj)

    def test_xnames_api_error(self):
        """Test Firmware: do_firmware() xnames api error"""
        self.mock_fw_client.get.side_effect = [
            self.mock_fw_response,
            APIError,
            self.mock_fw_response]
        mock_json = [
            {'devices': [
                {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]},
            {'devices': [
                {'xname': 'x3000c0s1b2', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]}
        ]
        self.mock_fw_response.json.side_effect = mock_json
        self.parsed.xname = ['x3000c0s1b0, x3000c0s1b1', 'x3000c0s1b2']
        sat.cli.firmware.main.do_firmware(self.parsed)
        make_fw_table_args = [data['devices'] for data in mock_json]
        # Allow any order because mock inserts calls involving call().__radd__([]).
        self.mock_make_fw_table.assert_has_calls(
            [mock.call(arg) for arg in make_fw_table_args], any_order=True
        )
        self.mock_report_cls.assert_called_once_with(
            sat.cli.firmware.main.HEADERS, None,
            self.parsed.sort_by, self.parsed.reverse,
            self.mock_config_values['format.no_headings'],
            self.mock_config_values['format.no_borders'],
            filter_strs=self.parsed.filter_strs
        )
        self.mock_report_obj.add_rows.assert_called_once_with(
            self.mock_make_fw_table.return_value * len(mock_json)
        )
        self.mock_print.assert_called_once_with(self.mock_report_obj)

    def test_xnames_value_error(self):
        """Test Firmware: do_firmware() xnames value error"""
        mock_json = [
            {'devices': [
                {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]},
            ValueError,
            {'devices': [
                {'xname': 'x3000c0s1b2', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]}
        ]
        self.mock_fw_response.json.side_effect = mock_json
        self.parsed.xname = ['x3000c0s1b0, x3000c0s1b1', 'x3000c0s1b2']
        sat.cli.firmware.main.do_firmware(self.parsed)
        make_fw_table_args = [data['devices'] for data in mock_json if isinstance(data, dict)]
        # Allow any order because mock inserts calls involving call().__radd__([]).
        self.mock_make_fw_table.assert_has_calls(
            [mock.call(arg) for arg in make_fw_table_args], any_order=True
        )
        self.mock_report_cls.assert_called_once_with(
            sat.cli.firmware.main.HEADERS, None,
            self.parsed.sort_by, self.parsed.reverse,
            self.mock_config_values['format.no_headings'],
            self.mock_config_values['format.no_borders'],
            filter_strs=self.parsed.filter_strs
        )
        self.mock_report_obj.add_rows.assert_called_once_with(
            self.mock_make_fw_table.return_value * (len(mock_json) - 1)
        )
        self.mock_print.assert_called_once_with(self.mock_report_obj)

    def test_xnames_get_empty_json(self):
        """Test Firmware: do_firmware() xnames get empty json"""
        mock_json = [
            {'devices': [
                {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]},
            {},
            {'devices': [
                {'xname': 'x3000c0s1b2', 'targets': [{'id': 'BMC', 'version': '1.0'}]}]}
        ]
        self.mock_fw_response.json.side_effect = mock_json
        self.parsed.xname = ['x3000c0s1b0, x3000c0s1b1', 'x3000c0s1b2']
        sat.cli.firmware.main.do_firmware(self.parsed)
        make_fw_table_args = [data['devices'] for data in mock_json if data]
        # Allow any order because mock inserts calls involving call().__radd__([]).
        self.mock_make_fw_table.assert_has_calls(
            [mock.call(arg) for arg in make_fw_table_args], any_order=True
        )
        self.mock_report_cls.assert_called_once_with(
            sat.cli.firmware.main.HEADERS, None,
            self.parsed.sort_by, self.parsed.reverse,
            self.mock_config_values['format.no_headings'],
            self.mock_config_values['format.no_borders'],
            filter_strs=self.parsed.filter_strs
        )
        self.mock_report_obj.add_rows.assert_called_once_with(
            self.mock_make_fw_table.return_value * (len(mock_json) - 1)
        )
        self.mock_print.assert_called_once_with(self.mock_report_obj)


class TestMakeFwTable(unittest.TestCase):
    """Unit test for Firmware make_fw_table()."""

    def test_zero_devices(self):
        """Test Firmware: make_fw_table() with zero devices/xnames"""
        fw_table = sat.cli.firmware.main.make_fw_table([])
        self.assertEqual(fw_table, [])

    def test_one_device(self):
        """Test Firmware: make_fw_table() with one device/xname"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '1.0'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'BMC', '1.0']])

    def test_two_devices(self):
        """Test Firmware: make_fw_table() with two devices/xnames"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '0.0'}]},
            {'xname': 'x3000c0s1b1', 'targets': [{'id': 'BMC', 'version': '1.0'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'BMC', '0.0'],
                                    ['x3000c0s1b1', 'BMC', '1.0']])

    def test_multiple_targets(self):
        """Test Firmware: make_fw_table() with two devices/xnames and two targets"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC', 'version': '0.0'},
                                                 {'id': 'SDR', 'version': '0.0.0'}]},
            {'xname': 'x3000c0s1b1', 'targets': [{'id': 'BMC', 'version': '1.0'},
                                                 {'id': 'SDR', 'version': '1.0.0'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'BMC', '0.0'],
                                    ['x3000c0s1b0', 'SDR', '0.0.0'],
                                    ['x3000c0s1b1', 'BMC', '1.0'],
                                    ['x3000c0s1b1', 'SDR', '1.0.0']])

    def test_missing_xname(self):
        """Test Firmware: make_fw_table() with xname missing"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'stuff': 'noise', 'targets': [{'id': 'BMC', 'version': '1.0'}]}])
        self.assertEqual(fw_table, [])

    def test_missing_targets(self):
        """Test Firmware: make_fw_table() with targets missing"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0'}])
        self.assertEqual(fw_table, [])

    def test_missing_id(self):
        """Test Firmware: make_fw_table() with id missing"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'targets': [{'version': '1.0'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'MISSING', '1.0']])

    def test_missing_version(self):
        """Test Firmware: make_fw_table() with version missing"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'targets': [{'id': 'BMC'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'BMC', 'MISSING']])

    def test_error_with_fw_data(self):
        """Test Firmware: make_fw_table() with error"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'error': 'Danger Will Robinson',
             'targets': [{'id': 'BMC', 'version': '1.0'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'BMC', '1.0']])

    def test_error_without_xname(self):
        """Test Firmware: make_fw_table() with error and no xname"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'error': 'Danger Will Robinson',
             'targets': [{'id': 'BMC', 'version': '1.0'}]}])
        self.assertEqual(fw_table, [])

    def test_error_in_target(self):
        """Test Firmware: make_fw_table() with error in target"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0',
             'targets': [{'error': 'Danger Will Robinson',
                          'id': 'BMC', 'version': '1.0'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'BMC', '1.0']])

    def test_error_in_target_without_id(self):
        """Test Firmware: make_fw_table() with error in target and no id"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0',
             'targets': [{'error': 'Danger Will Robinson',
                          'version': '1.0'}]}])
        self.assertEqual(fw_table, [])

    def test_error_without_targets(self):
        """Test Firmware: make_fw_table() with error and no targets"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'error': 'Danger Will Robinson'}])
        self.assertEqual(fw_table, [])

    def test_error_without_id(self):
        """Test Firmware: make_fw_table() with error and no id"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'error': 'Danger Will Robinson',
             'targets': [{'version': '1.0'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'MISSING', '1.0']])

    def test_error_without_version(self):
        """Test Firmware: make_fw_table() with error and no version"""
        fw_table = sat.cli.firmware.main.make_fw_table([
            {'xname': 'x3000c0s1b0', 'error': 'Danger Will Robinson',
             'targets': [{'id': 'BMC'}]}])
        self.assertEqual(fw_table, [['x3000c0s1b0', 'BMC', 'MISSING']])


if __name__ == '__main__':
    unittest.main()
