#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.apiclient.fas
"""

import copy
from datetime import datetime
import json
import logging
import unittest
from unittest.mock import Mock, call, patch

from sat.apiclient import APIError, APIGatewayClient
from sat.apiclient.fas import FASClient, _DateTimeEncoder, _now_and_later
from sat.xname import XName
from tests.test_util import ExtendedTestCase

FAS_FIRMWARE_DEVICES = {
    'full_snap': {
        'ready': True,
        'devices': [
            {
                'xname': 'x3000c0r15b0',
                'targets': [
                    {
                        'name': 'BMC',
                        'targetName': '',
                        'firmwareVersion': '1.00'
                    },
                    {
                        'name': 'FPGA0',
                        'targetName': '',
                        'firmwareVersion': '2.00'
                    }
                ]
            },
            {
                'xname': 'x3000c0s17b1',
                'targets': [
                    {
                        'name': '8',
                        'targetName': 'BMC',
                        'firmwareVersion': '1.01'
                    },
                    {
                        'name': '10',
                        'targetName': 'FPGA0',
                        'firmwareVersion': '2.01'
                    }
                ]
            }
        ]
    },
    'partial_snap': {
        'ready': True,
        'devices': [{
            'xname': 'x3000c0r15b0',
            'targets': [
                {
                    'name': 'BMC',
                    'targetName': '',
                    'firmwareVersion': '1.02'
                },
                {
                    'name': 'FPGA0',
                    'targetName': '',
                    'firmwareVersion': '2.02'
                }
            ]
        }],
    }
}

FAS_ACTIONS = {
    'actions': [
        {'state': 'new'},
        {'state': 'configured'},
        {'state': 'blocked'},
        {'state': 'running'},
        {'state': 'abort signaled'},
        {'state': 'aborted'},
        {'state': 'completed'}
    ]
}


class TestFASClient(ExtendedTestCase):
    """Test the FASClient class."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_session = Mock()
        self.fas_client = FASClient(self.mock_session)
        self.fas_firmware_devices = copy.deepcopy(FAS_FIRMWARE_DEVICES)
        self.fas_snapshots = {'snapshots': [{'name': name} for name in self.fas_firmware_devices]}
        self.fas_actions = copy.deepcopy(FAS_ACTIONS)
        self.mock_get = patch.object(APIGatewayClient, 'get', side_effect=self.mock_api_get).start()
        self.mock_post = patch.object(APIGatewayClient, 'post').start()
        # Functions that sleep do not need to sleep.
        patch('sat.apiclient.fas.time.sleep').start()
        # Mock datetime.utcnow() so the return values of _now_and_later are consistent
        patch('sat.apiclient.fas.datetime.utcnow', return_value=datetime(2021, 3, 7, 23, 35, 0, 403824))
        self.json_exception = None

    def mock_api_get(self, resource, name=None):
        """Mock the behavior of the API's get() method.

        Args:
            resource: The type of resource to query, e.g. 'snapshots' or 'actions'
            name: The name of the resource to query, e.g. a snapshot name.

        Returns:
            A Mock whose json() method returns a dictionary equivalent to the
            data returned by the API.
        """
        mock_api_response = Mock()
        # tests may set self.json_exception to have the Mock json() method raise an exception, e.g. ValueError
        mock_api_response.json.side_effect = self.json_exception
        if resource == 'actions':
            mock_api_response.json.return_value = self.fas_actions
        elif resource == 'snapshots':
            if name:
                mock_api_response.json.return_value = self.fas_firmware_devices.get(name)
            else:
                mock_api_response.json.return_value = self.fas_snapshots
        else:
            self.fail('mock_api_get called incorrectly')

        return mock_api_response

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_get_updates_valid(self):
        """get_updates with valid response from FAS should return the value of the 'actions' key."""
        expected = self.fas_actions['actions']
        actual = self.fas_client.get_actions()
        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with('actions')

    def test_get_updates_no_actions_key(self):
        """get_updates with missing 'actions' key in FAS response should raise APIError"""
        del self.fas_actions['actions']
        err_regex = r"^No 'actions' key in response from FAS."
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_actions()
        self.mock_get.assert_called_once_with('actions')

    def test_get_updates_invalid_json(self):
        """get_updates with json() raising a ValueError should raise APIError"""
        self.json_exception = ValueError('invalid json')
        err_regex = (r'^Unable to parse json in response from '
                     r'FAS: invalid json')
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_actions()
        self.mock_get.assert_called_once_with('actions')

    def test_get_updates_api_err(self):
        """Test get_updates with a get to FAS raising an APIError."""
        api_err_msg = 'FAS unavailable'
        self.mock_get.side_effect = APIError(api_err_msg)
        err_regex = r'^{}'.format(api_err_msg)
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_actions()
        self.mock_get.assert_called_once_with('actions')

    def test_get_active_updates(self):
        """get_active_updates with mix of active and inactive updates should return the active ones."""
        expected_active_updates = [
            update for update in self.fas_actions['actions']
            if update['state'] in ['new', 'configured', 'blocked', 'running', 'abort signaled']
        ]
        active_updates = self.fas_client.get_active_actions()
        self.assertEqual(expected_active_updates, active_updates)
        self.mock_get.assert_called_once_with('actions')

    def test_get_all_snapshot_names(self):
        """Positive test case for get_all_snapshot_names"""
        expected = set(self.fas_firmware_devices.keys())
        actual = self.fas_client.get_all_snapshot_names()
        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with('snapshots')

    def test_get_all_snapshot_names_api_error(self):
        """get_all_snapshot_names should raise if the FW API raises.
        """
        self.mock_get.side_effect = APIError
        err_regex = r'Failed to get snapshots from the FAS API: '
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_all_snapshot_names()

    def test_get_all_snapshot_names_key_error(self):
        """It should raise a if the payload has no 'snapshots' entry."""
        del self.fas_snapshots['snapshots']
        err_regex = r'missing an entry for "snapshots"'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_all_snapshot_names()

    def test_get_all_snapshot_names_value_error(self):
        """get_all_snapshot_names should raise an error if the .json() call raised one."""
        self.json_exception = ValueError('invalid json')
        err_regex = r'JSON payload was invalid: invalid json'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_all_snapshot_names()

    def test_get_snapshot(self):
        """A normal call to get_snapshot_devices should return the 'devices' key from the FAS payload"""
        self.mock_get.return_value.json.return_value = self.fas_firmware_devices['full_snap']
        expected = self.fas_firmware_devices['full_snap']['devices']
        actual = self.fas_client.get_snapshot_devices('full_snap')
        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with('snapshots', 'full_snap')

    def test_get_snapshot_api_error(self):
        """get_snapshot_devices should raise if the FAS query failed."""
        self.mock_get.side_effect = APIError
        err_regex = r'Failed to get snapshot "full_snap" from the FAS API: '
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_snapshot_devices('full_snap')
        self.mock_get.assert_called_once_with('snapshots', 'full_snap')

    def test_get_snapshot_key_error(self):
        """get_snapshot_devices should raise if missing 'devices' key."""
        del self.fas_firmware_devices['full_snap']['devices']
        self.mock_get.return_value.json.return_value = self.fas_firmware_devices['full_snap']
        err_regex = r'missing a "devices" key'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_snapshot_devices('full_snap')
        self.mock_get.assert_called_once_with('snapshots', 'full_snap')

    def test_get_snapshot_value_error(self):
        """get_snapshot_devices should raise APIError if the .json() call raised a ValueError."""
        self.json_exception = ValueError('invalid json')
        err_regex = r'The JSON payload from snapshot "full_snap" was invalid: invalid json'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_snapshot_devices('full_snap')
        self.mock_get.assert_called_once_with('snapshots', 'full_snap')

    def test_get_snapshot_with_xname(self):
        """get_snapshot_devices with an xname provided should filter the returned data."""
        xnames_to_query = ['x3000c0s17b1']
        expected = [
            dev
            for dev in self.fas_firmware_devices['full_snap']['devices']
            if dev.get('xname') in xnames_to_query
        ]
        actual = self.fas_client.get_snapshot_devices('full_snap', xnames_to_query)
        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with('snapshots', 'full_snap')

    def test_get_snapshot_with_nonexistent_xname(self):
        """get_snapshot_devices with an xname that doesn't exist in the snapshot should result in an APIError."""
        xnames_to_query = ['x3000c0s17b1']
        err_regex = (
            r'Snapshot partial_snap did not have any devices under its "devices" '
            r'key for xname\(s\) x3000c0s17b1.'
        )
        with self.assertRaisesRegex(APIError, err_regex):
            with self.assertLogs(level=logging.WARNING) as logs:
                self.fas_client.get_snapshot_devices('partial_snap', xnames_to_query)
        self.assert_in_element(f'xname(s) x3000c0s17b1 not in snapshot partial_snap', logs.output)
        self.mock_get.assert_called_once_with('snapshots', 'partial_snap')

    def test_get_snapshot_with_one_nonexistent_xname(self):
        """get_snapshot_devices with one xname that exists and that does not should warn but return data."""
        xnames_to_query = ['x3000c0r15b0', 'x3000c0s17b1']
        expected = [
            dev
            for dev in self.fas_firmware_devices['partial_snap']['devices']
            if dev.get('xname') in xnames_to_query
        ]
        with self.assertLogs(level=logging.WARNING) as logs:
            actual = self.fas_client.get_snapshot_devices('partial_snap', xnames_to_query)
        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with('snapshots', 'partial_snap')
        self.assert_in_element('xname(s) x3000c0s17b1 not in snapshot partial_snap', logs.output)

    def test_get_snapshots_single_snapshot(self):
        """get_multiple_snapshot_devices with one snapshot should return a dict indexed by the snapshot name."""
        mock_get_snapshot = patch.object(self.fas_client, 'get_snapshot_devices').start()
        snapshot_to_query = 'full_snap'
        expected = {snapshot_to_query: mock_get_snapshot.return_value}
        actual = self.fas_client.get_multiple_snapshot_devices([snapshot_to_query])
        self.assertEqual(expected, actual)
        mock_get_snapshot.assert_called_once_with(snapshot_to_query, None)

    def test_get_snapshots_multiple_snapshots(self):
        """get_multiple_snapshot_devices with multiple snapshots should return a dict indexed by the snapshot name."""
        snapshots_to_query = ['full_snap', 'partial_snap']
        mock_snapshots = [Mock(), Mock()]
        mock_get_snapshot = patch.object(self.fas_client, 'get_snapshot_devices').start()
        mock_get_snapshot.side_effect = mock_snapshots
        expected = {
            'full_snap': mock_snapshots[0],
            'partial_snap': mock_snapshots[1]
        }
        actual = self.fas_client.get_multiple_snapshot_devices(snapshots_to_query)
        self.assertEqual(expected, actual)
        mock_get_snapshot.assert_has_calls([
            call('full_snap', None), call('partial_snap', None)
        ])

    def test_get_snapshots_with_xname(self):
        """get_snapshots_with_an_xname should call get_snapshot_devices with that xname"""
        snapshots_to_query = ['full_snap', 'partial_snap']
        xname_to_query = 'x3000c0r15b0'
        mock_snapshots = [Mock(), Mock()]
        mock_get_snapshot = patch.object(self.fas_client, 'get_snapshot_devices').start()
        mock_get_snapshot.side_effect = mock_snapshots
        expected = {
            'full_snap': mock_snapshots[0],
            'partial_snap': mock_snapshots[1]
        }
        actual = self.fas_client.get_multiple_snapshot_devices(snapshots_to_query, [xname_to_query])
        self.assertEqual(expected, actual)
        mock_get_snapshot.assert_has_calls([
            call('full_snap', [xname_to_query]), call('partial_snap', [xname_to_query])
        ])

    def test_get_snapshots_one_error(self):
        """When get_snapshot_devices raises APIError for one snapshot but not the other, log it but return data."""
        snapshots_to_query = ['full_snap', 'partial_snap']
        mock_snapshot = Mock()
        mock_get_snapshot = patch.object(self.fas_client, 'get_snapshot_devices').start()
        mock_get_snapshot.side_effect = [
            APIError('The API failed'), mock_snapshot
        ]
        expected = {
            'partial_snap': mock_snapshot,
        }
        with self.assertLogs(level=logging.ERROR) as logs:
            actual = self.fas_client.get_multiple_snapshot_devices(snapshots_to_query, None)
        self.assertEqual(expected, actual)
        mock_get_snapshot.assert_has_calls([
            call('full_snap', None), call('partial_snap', None)
        ])
        self.assert_in_element('Error getting snapshot full_snap: The API failed', logs.output)

    def test_get_snapshots_both_error(self):
        """When get_snapshot_devices raises APIError for both snapshots, log them and raise APIError."""
        snapshots_to_query = ['full_snap', 'partial_snap']
        mock_get_snapshot = patch.object(self.fas_client, 'get_snapshot_devices').start()
        mock_get_snapshot.side_effect = [
            APIError('The API failed'), APIError('The API failed again!')
        ]
        err_regex = r'No firmware found.'
        with self.assertRaisesRegex(APIError, err_regex):
            with self.assertLogs(level=logging.ERROR) as logs:
                self.fas_client.get_multiple_snapshot_devices(snapshots_to_query, None)
        mock_get_snapshot.assert_has_calls([
            call('full_snap', None), call('partial_snap', None)
        ])
        self.assert_in_element('Error getting snapshot full_snap: The API failed', logs.output)
        self.assert_in_element('Error getting snapshot partial_snap: The API failed again!', logs.output)

    def test_get_snapshots_nonexistent_snapshot(self):
        """When getting one snapshot that does not exist, warn then raise an APIError"""
        snapshots_to_query = ['nonexistent_snap']
        with self.assertRaisesRegex(APIError, 'No firmware found.'):
            with self.assertLogs(level=logging.WARNING) as logs:
                self.fas_client.get_multiple_snapshot_devices(snapshots_to_query)
        self.mock_get.assert_called_once_with('snapshots')
        self.assert_in_element('Snapshot nonexistent_snap does not exist', logs.output)

    def test_get_snapshots_only_one_snapshot_exists(self):
        """When one snapshot does not exist but the other does, warn and return all matching data."""
        snapshots_to_query = ['full_snap', 'nonexistent_snap']
        expected = {'full_snap': self.fas_firmware_devices['full_snap']['devices']}
        with self.assertLogs(level=logging.WARNING) as logs:
            actual = self.fas_client.get_multiple_snapshot_devices(snapshots_to_query)
        self.assertEqual(expected, actual)
        self.assert_in_element('Snapshot nonexistent_snap does not exist', logs.output)
        self.mock_get.assert_has_calls([call('snapshots'), call('snapshots', 'full_snap')])

    def test_get_snapshots_api_error(self):
        """get_multiple_snapshot_devices should raise if the API couldn't be queried to list snapshots."""
        self.mock_get.side_effect = APIError
        err_regex = r'Failed to get snapshots from the FAS API: '
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_multiple_snapshot_devices(['full_snap'])

    def test_get_device_firmwares(self):
        """Positive test case for get_device_firmwares.

        A new snapshot formatted like 'SAT-year-month-day-hour-minute-sec
        should be created, and the payload should tell the FAS to expire it
        in 10 minutes.
        """
        now, later = _now_and_later(10)
        not_ready_response = Mock()
        not_ready_response.json.return_value = {'ready': False}
        ready_response = Mock()
        ready_response.json.return_value = {
            'ready': True,
            'devices': [{
                'xname': 'x3000c0r15b0',
                'targets': [
                    {
                        'name': 'BMC',
                        'targetName': '',
                        'firmwareVersion': '1.00'
                    },
                    {
                        'name': 'FPGA0',
                        'targetName': '',
                        'firmwareVersion': '2.00'
                    }
                ]
            }]
        }
        # Mock the return values of get() to test that we wait for the snapshot to be ready
        self.mock_get.side_effect = (
            not_ready_response,
            ready_response
        )

        expected = ready_response.json.return_value['devices']
        actual = self.fas_client.get_device_firmwares()

        exp_name = 'SAT-{}-{}-{}-{}-{}-{}'.format(
            now.year, now.month, now.day, now.hour, now.minute, now.second)
        exp_payload = {'name': exp_name, 'expirationTime': later}
        exp_payload = json.dumps(exp_payload, cls=_DateTimeEncoder)

        self.assertEqual(expected, actual)
        self.mock_post.assert_called_once_with('snapshots', payload=exp_payload)
        self.mock_get.assert_has_calls([call('snapshots', exp_name)] * 2)

    def test_get_device_firmwares_with_xname(self):
        """Calling get_device_firmwares with an xname should create a snapshot filtered for that xname"""
        xname_to_query = 'x3000c0s17b1'
        now, later = _now_and_later(10)
        # Mock the return values of get() to test that we wait for the snapshot to be ready
        not_ready_response = Mock()
        not_ready_response.json.return_value = {'ready': False}
        ready_response = Mock()
        ready_response.json.return_value = {
            'ready': True,
            'devices': [{
                'xname': 'x3000c0r15b0',
                'targets': [
                    {
                        'name': 'BMC',
                        'targetName': '',
                        'firmwareVersion': '1.00'
                    },
                    {
                        'name': 'FPGA0',
                        'targetName': '',
                        'firmwareVersion': '2.00'
                    }
                ]
            }]
        }
        self.mock_get.side_effect = (
            not_ready_response,
            ready_response
        )

        expected = ready_response.json.return_value['devices']
        actual = self.fas_client.get_device_firmwares([xname_to_query])

        exp_name = 'SAT-{}-{}-{}-{}-{}-{}'.format(
            now.year, now.month, now.day, now.hour, now.minute, now.second)
        exp_payload = {
            'name': exp_name, 'expirationTime': later, 'stateComponentFilter': {'xnames': [xname_to_query]}
        }
        exp_payload = json.dumps(exp_payload, cls=_DateTimeEncoder)

        self.assertEqual(expected, actual)
        self.mock_post.assert_called_once_with('snapshots', payload=exp_payload)
        self.mock_get.assert_has_calls([call('snapshots', exp_name)] * 2)

    def test_get_device_firmwares_post_api_error(self):
        """get_device_firmwares should raise if the post fails."""
        self.mock_post.side_effect = APIError

        err_regex = r'Error when posting new snapshot'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_get_api_error(self):
        """get_device_firmwares should raise if a get fails."""
        self.mock_get.side_effect = APIError

        err_regex = r'Error when polling the snapshot'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_value_error(self):
        """get_device_firmwares should raise APIError if get().json() raised ValueError."""
        self.json_exception = ValueError('invalid json')

        err_regex = r'The JSON received was invalid: invalid json'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_ready_key_error(self):
        """Raise an APIError if the value returned from get() while polling is missing the 'ready' key."""
        missing_ready_response = Mock()
        missing_ready_response.json.return_value = {'no-ready': True}
        self.mock_get.side_effect = [missing_ready_response]

        err_regex = r'did not have "ready" field'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_devices_key_error(self):
        """Raise an APIError if the value returned from get() while polling is missing the 'devices' key."""
        missing_devices_response = Mock()
        missing_devices_response.json.return_value = {
            'ready': True, 'not-devices': []
        }
        self.mock_get.side_effect = [missing_devices_response]

        err_regex = r'not contain a "devices" field'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_make_fw_table(self):
        """Test creating a table from a basic firmware response"""
        expected = [[XName('x3000c0r15b0'), 'BMC', '', '1.00'],
                    [XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        result = self.fas_client.make_fw_table(
            self.fas_firmware_devices['full_snap']['devices']
        )
        self.assertEqual(expected, result)

    def test_make_fw_table_with_error_and_all_fields(self):
        """When a target has an 'error' but all fields are present, log an error and display the row"""
        self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['error'] = 'firmware bad'
        expected = [[XName('x3000c0r15b0'), 'BMC', '', '1.00'],
                    [XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with self.assertLogs(level=logging.ERROR) as logs:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        self.assert_in_element('Error getting firmware for x3000c0r15b0 target BMC: firmware bad', logs.output)
        self.assertEqual(expected, result)

    def test_make_fw_table_with_error_and_missing_version(self):
        """When a target has an 'error' and no firmware version, log error and don't display the row."""
        self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['error'] = 'firmware bad'
        del self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['firmwareVersion']
        expected = [[XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with self.assertLogs(level=logging.ERROR) as logs:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        self.assert_in_element('Error getting firmware for x3000c0r15b0 target BMC: firmware bad', logs.output)
        self.assertEqual(expected, result)

    def test_make_fw_table_with_error_and_missing_targetname(self):
        """When a target has an 'error' but all fields are present except targetName, log error and display the row."""
        self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['error'] = 'firmware bad'
        del self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['targetName']
        expected = [[XName('x3000c0r15b0'), 'BMC', 'MISSING', '1.00'],
                    [XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with self.assertLogs(level=logging.ERROR) as logs:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        self.assert_in_element('Error getting firmware for x3000c0r15b0 target BMC: firmware bad', logs.output)
        self.assertEqual(expected, result)

    def test_make_fw_table_with_error_and_missing_targetname_and_name(self):
        """When target has an 'error' and no name or targetName field, log error and don't display the row."""
        self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['error'] = 'firmware bad'
        del self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['name']
        del self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['targetName']
        expected = [[XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with self.assertLogs(level=logging.ERROR) as logs:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        self.assert_in_element('Error getting firmware for x3000c0r15b0 target MISSING: firmware bad', logs.output)
        self.assertEqual(expected, result)

    def test_make_fw_table_with_empty_error_on_target(self):
        """When target has an empty string for an 'error' but targets look good, don't log an error"""
        self.fas_firmware_devices['full_snap']['devices'][0]['targets'][0]['error'] = ''
        expected = [[XName('x3000c0r15b0'), 'BMC', '', '1.00'],
                    [XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with patch('sat.apiclient.fas.LOGGER.error') as logs_error:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        logs_error.assert_not_called()
        self.assertEqual(expected, result)

    def test_make_fw_table_with_error_on_xname(self):
        """When an xname has an 'error' but targets look good, log an error for the xname and display the row."""
        self.fas_firmware_devices['full_snap']['devices'][0]['error'] = 'xname bad'
        expected = [[XName('x3000c0r15b0'), 'BMC', '', '1.00'],
                    [XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with self.assertLogs(level=logging.ERROR) as logs:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        self.assert_in_element('Error getting firmware for x3000c0r15b0: xname bad', logs.output)
        self.assertEqual(expected, result)

    def test_make_fw_table_with_empty_error_on_xname(self):
        """When an xname has an empty string for an 'error', don't log an error."""
        self.fas_firmware_devices['full_snap']['devices'][0]['error'] = ''
        expected = [[XName('x3000c0r15b0'), 'BMC', '', '1.00'],
                    [XName('x3000c0r15b0'), 'FPGA0', '', '2.00'],
                    [XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with patch('sat.apiclient.fas.LOGGER.error') as logs_error:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        logs_error.assert_not_called()
        self.assertEqual(expected, result)

    def test_make_fw_table_with_empty_error_on_xname_and_missing_targets(self):
        """When an xname has an error and also no targets, make sure exactly one error is logged."""
        self.fas_firmware_devices['full_snap']['devices'][0]['error'] = 'xname bad'
        self.fas_firmware_devices['full_snap']['devices'][0]['targets'] = []
        expected = [[XName('x3000c0s17b1'), '8', 'BMC', '1.01'],
                    [XName('x3000c0s17b1'), '10', 'FPGA0', '2.01']]
        with patch('sat.apiclient.fas.LOGGER') as logger:
            result = self.fas_client.make_fw_table(
                self.fas_firmware_devices['full_snap']['devices']
            )
        logger.warning.assert_not_called()
        logger.error.assert_called_once()
        self.assertEqual(expected, result)


if __name__ == '__main__':
    unittest.main()
