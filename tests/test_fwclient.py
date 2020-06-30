"""
Unit tests for sat.fwclient

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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

import json
import unittest
from unittest.mock import Mock, patch

import sat.apiclient
from sat.apiclient import APIError, APIGatewayClient
from sat.fwclient import _DateTimeEncoder, FASClient, FUSClient, _now_and_later


class TestFASClient(unittest.TestCase):
    """Test the FASClient class."""

    def setUp(self):
        """Set up some mocks."""
        self.fas_client = FASClient(session=Mock(), host=Mock(), cert_verify=True)
        self.mock_get = patch.object(APIGatewayClient, 'get').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_get_updates_valid(self):
        """Test get_updates with valid response from FAS."""
        mock_updates = Mock()
        self.mock_get.return_value.json.return_value = {
            'actions': mock_updates
        }

        updates = self.fas_client.get_updates()

        self.mock_get.assert_called_once_with('actions')
        self.assertEqual(mock_updates, updates)

    def test_get_updates_no_actions_key(self):
        """Test get_updates with missing 'actions' key in FAS response."""
        self.mock_get.return_value.json.return_value = {
            'not_actions': []
        }
        err_regex = r"^No 'actions' key in response from FAS."

        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_updates()

    def test_get_updates_invalid_json(self):
        """Test get_updates with json() raising a ValueError."""
        val_err_msg = 'invalid json'
        self.mock_get.return_value.json.side_effect = ValueError(val_err_msg)
        err_regex = (r'^Unable to parse json in response from '
                     r'FAS: {}'.format(val_err_msg))

        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_updates()

    def test_get_updates_api_err(self):
        """Test get_updates with a get to FAS raising an APIError."""
        api_err_msg = 'FAS unavailable'
        self.mock_get.side_effect = APIError(api_err_msg)
        err_regex = r'^{}'.format(api_err_msg)

        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_updates()

    def test_get_active_updates(self):
        """Test get_active_updates with mix of active and inactive updates."""
        new_update = {'state': 'new'}
        configured_update = {'state': 'configured'}
        blocked_update = {'state': 'blocked'}
        running_update = {'state': 'running'}
        aborting_update = {'state': 'abort signaled'}
        aborted_update = {'state': 'aborted'}
        completed_update = {'state': 'completed'}
        self.mock_get.return_value.json.return_value = {
            'actions': [
                new_update, configured_update, blocked_update, running_update,
                aborted_update, aborting_update, completed_update
            ]
        }
        expected_active_updates = [
            new_update, configured_update, blocked_update,
            running_update, aborting_update
        ]

        active_updates = self.fas_client.get_active_updates()

        self.assertEqual(expected_active_updates, active_updates)

    def test_get_all_snapshot_names(self):
        """Positive test case for get_all_snapshot_names
        """
        snaps = {
            'snapshots': [
                {'name': 'snap1'},
                {'name': 'snap2'},
            ]
        }

        self.mock_get.return_value.json.return_value = snaps

        known_snaps = self.fas_client.get_all_snapshot_names()

        self.assertEqual({'snap1', 'snap2'}, known_snaps)

    def test_get_all_snapshot_names_api_error(self):
        """get_all_snapshot_names should raise if the FW API raises.
        """
        self.mock_get.side_effect = APIError

        err_regex = r'Contacting the FW API'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_all_snapshot_names()

    def test_get_all_snapshot_names_key_error(self):
        """It should raise a if the payload has no 'snapshots' entry.
        """
        snaps = {}
        self.mock_get.return_value.json.return_value = snaps

        err_regex = r'missing an entry for'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_all_snapshot_names()

    def test_get_all_snapshot_names_value_error(self):
        """It should raise a if the .json() call raised.

        In practice it will re-raise whatever this raises.
        """
        self.mock_get.return_value.json.side_effect = ValueError

        err_regex = r'JSON payload was invalid'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_all_snapshot_names()

    def test_get_snapshot(self):
        """Positive test case for get_snapshot.

        The payload's 'devices' entry should be returned.
        """
        snaps = {'name': 'test-snap', 'devices': []}

        self.mock_get.return_value.json.return_value = snaps

        actual = self.fas_client.get_snapshot('test-snap')
        expected = snaps['devices']

        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with('snapshots', 'test-snap')

    def test_get_snapshot_api_error(self):
        """get_snapshot should raise FAS query failed.
        """
        self.mock_get.side_effect = APIError

        err_regex = r'Contacting the FAS for snapshot'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fas_client.get_snapshot('test-snap')

    def test_get_snapshot_key_error(self):
        """get_snapshot should raise if missing 'devices' key.
        """
        badsnaps = {}

        self.mock_get.return_value.json.return_value = badsnaps

        err_regex = r'missing a "devices" key'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fas_client.get_snapshot('test-snap')

    def test_get_snapshot_value_error(self):
        """get_snapshot should raise if the .json() call raised.
        """
        self.mock_get.return_value.json.side_effect = ValueError

        err_regex = r'JSON payload from'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fas_client.get_snapshot('test-snap')

    def test_get_snapshots(self):
        """Positive test case for get_snapshots.
        """
        # mock return from get_all_snapshot_names.
        snapshot_names = {'snap1', 'snap2', 'snap3'}

        # Sort of mock the underlying data format.
        # The keys are akin to the /snapshots/<name> path, and the values
        # represent the snapshot payload, of which the FASClient cares
        # about the devices.
        snapshots = {
            'snap1': {'devices': ['dev1']},
            'snap2': {'devices': ['dev1']},
            'snap3': {'devices': ['dev1']},
        }

        def mock_get_snapshot(x, name):
            """x mocks 'self'.
            """
            return snapshots[name]['devices']

        patch(
            'sat.fwclient.FASClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        patch(
            'sat.fwclient.FASClient.get_snapshot',
            mock_get_snapshot).start()

        actual = self.fas_client.get_snapshots(['snap1', 'snap2'])
        expected = {
            'snap1': snapshots['snap1']['devices'],
            'snap2': snapshots['snap2']['devices'],
        }

        self.assertEqual(expected, actual)

    def test_get_snapshots_skip_unknown_snaps(self):
        """It shouldn't attempt to get non-existent snapshots.
        """
        # mock return from get_all_snapshot_names.
        snapshot_names = {'snap1', 'snap2'}

        patch(
            'sat.fwclient.FASClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        actual = self.fas_client.get_snapshots(['test-snap'])
        expected = {}

        self.assertEqual(expected, actual)

    def test_get_snapshots_api_error(self):
        """get_snapshot should raise if the api couldn't be queried.
        """
        self.mock_get.side_effect = APIError

        err_regex = r'Contacting the FW API'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fas_client.get_snapshots(['test-snap'])

    def test_get_snapshots_key_error(self):
        """get_snapshot should raise if missing 'devices' key.
        """
        badsnaps = {}
        snapshot_names = {'snap1'}
        patch(
            'sat.fwclient.FASClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        self.mock_get.return_value.json.return_value = badsnaps

        err_regex = r'was missing a "devices" key'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fas_client.get_snapshots(['snap1'])

    def test_get_snapshots_value_error(self):
        """get_snapshot should raise if the .json() call raised.
        """
        snapshot_names = {'snap1'}
        patch(
            'sat.fwclient.FASClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        self.mock_get.return_value.json.side_effect = ValueError

        err_regex = r'JSON payload from snapshot'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fas_client.get_snapshots(['snap1'])

    def test_get_device_firmwares(self):
        """Positive test case for get_device_firmwares.

        A new snapshot formatted like 'year-month-day-hour-minute-sec-all-xnames
        should be created, and the payload should tell the FAS to expire it
        in 10 minutes.
        """
        # the function should ultimately rely on two calls to get,
        # which will need to contain entries for 'ready', and 'devices'.
        # This list of payloads helps ensure the function will retry
        # until the snapshot is ready.
        payloads = [
            {'ready': False, 'devices': 'expected'},
            {'ready': False, 'devices': 'expected'},
            {'ready': True, 'devices': 'expected'},
        ]

        self.mock_get.return_value.json.side_effect = payloads

        mock_post = patch.object(APIGatewayClient, 'post').start()

        now, later = _now_and_later(10)

        patch(
            'sat.fwclient._now_and_later',
            return_value=(now, later)).start()

        # this function calls sleep, and it doesn't need to for the test.
        patch('sat.fwclient.time.sleep').start()

        ret = self.fas_client.get_device_firmwares()

        exp_name = '{}-{}-{}-{}-{}-{}-all-xnames'.format(
            now.year, now.month, now.day, now.hour, now.minute, now.second)
        exp_payload = {'name': exp_name, 'expirationTime': later}
        exp_payload = json.dumps(exp_payload, cls=_DateTimeEncoder)

        mock_post.assert_called_once_with('snapshots', payload=exp_payload)
        self.mock_get.assert_called_with('snapshots', exp_name)

        self.assertEqual('expected', ret)

    def test_get_device_firmwares_post_api_error(self):
        """get_device_firmwares should raise if the post fails.
        """
        patch.object(APIGatewayClient, 'post', side_effect=APIError).start()

        err_regex = r'Error when posting new snapshot'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_get_api_error(self):
        """get_device_firmwares should raise if a get fails.
        """
        self.mock_get.side_effect = APIError

        mock_post = patch.object(APIGatewayClient, 'post').start()

        # this function calls sleep, and it doesn't need to for the test.
        patch('sat.fwclient.time.sleep').start()

        err_regex = r'Error when polling the snapshot'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_value_error(self):
        """It should raise if invalid JSON.
        """
        self.mock_get.return_value.json.side_effect = ValueError

        mock_post = patch.object(APIGatewayClient, 'post').start()

        # this function calls sleep, and it doesn't need to for the test.
        patch('sat.fwclient.time.sleep').start()

        err_regex = r'The JSON received'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_key_error(self):
        """It should raise if the payload is missing a 'ready' entry.
        """
        payload = {'no-ready': False}

        self.mock_get.return_value.json.return_value = payload

        mock_post = patch.object(APIGatewayClient, 'post').start()

        now, later = _now_and_later(10)

        patch(
            'sat.fwclient._now_and_later',
            return_value=(now, later)).start()

        # this function calls sleep, and it doesn't need to for the test.
        patch('sat.fwclient.time.sleep').start()

        err_regex = r'did not have a "ready" field'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()

    def test_get_device_firmwares_key_error(self):
        """It should if the payload is missing a 'devices' entry.
        """
        payload = {'ready': True, 'not-devices': []}

        self.mock_get.return_value.json.return_value = payload

        mock_post = patch.object(APIGatewayClient, 'post').start()

        now, later = _now_and_later(10)

        patch(
            'sat.fwclient._now_and_later',
            return_value=(now, later)).start()

        # this function calls sleep, and it doesn't need to for the test.
        patch('sat.fwclient.time.sleep').start()

        err_regex = r'not contain a "devices" field'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fas_client.get_device_firmwares()


class TestFUSClient(unittest.TestCase):
    """Test the FUSClient class."""

    def setUp(self):
        """Set up some mocks."""
        self.fus_client = FUSClient(session=Mock(), host=Mock(), cert_verify=True)
        self.mock_get = patch.object(APIGatewayClient, 'get').start()

        self.num_active_updates = 4
        self.active_updates = [
            {
                'updateID': idx,
                'startTime': '2020-05-26 22:11:22 UTC',
                'dryrun': False
             } for idx in range(self.num_active_updates)
        ]
        self.num_inactive_updates = 10
        self.inactive_updates = [
            {
                'updateID': idx + self.num_active_updates,
                'startTime': '2020-06-06 22:11:22 UTC',
                'dryrun': False,
                'endTime': '2020-06-06 23:11:22 UTC'
            } for idx in range(self.num_inactive_updates)
        ]

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_get_updates_valid(self):
        """Test get_updates with valid response from FAS."""
        mock_updates = Mock()
        self.mock_get.return_value.json.return_value = mock_updates

        updates = self.fus_client.get_updates()

        self.mock_get.assert_called_once_with('status')
        self.assertEqual(mock_updates, updates)

    def test_get_updates_invalid_json(self):
        """Test get_updates with json() raising a ValueError."""
        val_err_msg = 'invalid json'
        self.mock_get.return_value.json.side_effect = ValueError(val_err_msg)
        err_regex = (r'^Unable to parse json in response from '
                     r'FUS: {}'.format(val_err_msg))

        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_updates()

    def test_get_updates_api_err(self):
        """Test get_updates with a get to FAS raising an APIError."""
        api_err_msg = 'FUS unavailable'
        self.mock_get.side_effect = APIError(api_err_msg)
        err_regex = r'^{}'.format(api_err_msg)

        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_updates()

    def test_get_active_updates(self):
        """Test get_active_updates with mix of active and inactive updates."""
        self.mock_get.return_value.json.return_value = \
            self.inactive_updates + self.active_updates

        active_updates = self.fus_client.get_active_updates()

        self.assertEqual(self.active_updates, active_updates)

    def test_get_all_snapshot_names(self):
        """Positive test case for get_all_snapshot_names
        """
        snaps = {
            'snapshots': [
                {'name': 'snap1'},
                {'name': 'snap2'},
            ]
        }

        self.mock_get.return_value.json.return_value = snaps

        known_snaps = self.fus_client.get_all_snapshot_names()

        self.assertEqual({'snap1', 'snap2'}, known_snaps)

    def test_get_all_snapshot_names_api_error(self):
        """get_all_snapshot_names should raise if the FUS query failed.
        """
        self.mock_get.side_effect = APIError

        err_regex = r'Request to FW API failed'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_all_snapshot_names()

    def test_get_all_snapshot_names_key_error(self):
        """It should raise if the payload has no 'snapshots' entry.
        """
        snaps = {}
        self.mock_get.return_value.json.return_value = snaps

        err_regex = r'missing an entry for "snapshots"'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_all_snapshot_names()

    def test_get_all_snapshot_names_value_error(self):
        """It should raise if the .json() call raised.

        In practice it will re-raise whatever this raises.
        """
        self.mock_get.return_value.json.side_effect = ValueError

        err_regex = r'The JSON payload was invalid'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_all_snapshot_names()

    def test_get_snapshot(self):
        """Positive test case for get_snapshot.

        The payload's 'devices' entry should be returned.
        """
        snaps = {'name': 'test-snap', 'devices': []}

        self.mock_get.return_value.json.return_value = snaps

        actual = self.fus_client.get_snapshot('test-snap')
        expected = snaps['devices']

        self.assertEqual(expected, actual)
        self.mock_get.assert_called_once_with('snapshot', 'test-snap')

    def test_get_snapshot_api_error(self):
        """get_snapshot should raise if the FUS query failed.
        """
        self.mock_get.side_effect = APIError

        err_regex = r'Request to firmware API failed'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fus_client.get_snapshot('test-snap')

    def test_get_snapshot_key_error(self):
        """get_snapshot should raise if missing 'devices' key.
        """
        badsnaps = {}

        self.mock_get.return_value.json.return_value = badsnaps

        err_regex = r'missing an entry for "devices"'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fus_client.get_snapshot('test-snap')

    def test_get_snapshot_value_error(self):
        """get_snapshot should raise if the .json() call raised.
        """
        self.mock_get.return_value.json.side_effect = ValueError

        err_regex = r'The JSON payload was invalid'
        with self.assertRaisesRegex(APIError, err_regex):
            actual = self.fus_client.get_snapshot('test-snap')

    def test_get_snapshots(self):
        """Positive test case for get_snapshots.
        """
        # mock return from get_all_snapshot_names.
        snapshot_names = {'snap1', 'snap2', 'snap3'}

        # Sort of mock the underlying data format.
        # The keys are akin to the /snapshot/<name> path, and the values
        # represent the snapshot payload, of which the FUSClient cares
        # about the devices.
        snapshots = {
            'snap1': {'devices': ['dev1']},
            'snap2': {'devices': ['dev1']},
            'snap3': {'devices': ['dev1']},
        }

        def mock_get_snapshot(x, name):
            """x mocks 'self'.
            """
            return snapshots[name]['devices']

        patch(
            'sat.fwclient.FUSClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        patch(
            'sat.fwclient.FUSClient.get_snapshot',
            mock_get_snapshot).start()

        actual = self.fus_client.get_snapshots(['snap1', 'snap2'])
        expected = {
            'snap1': snapshots['snap1']['devices'],
            'snap2': snapshots['snap2']['devices'],
        }

        self.assertEqual(expected, actual)

    def test_get_snapshots_skip_unknown_snaps(self):
        """It shouldn't attempt to get non-existent snapshots.
        """
        # mock return from get_all_snapshot_names.
        snapshot_names = {'snap1', 'snap2'}

        patch(
            'sat.fwclient.FUSClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        actual = self.fus_client.get_snapshots(['test-snap'])
        expected = {}

        self.assertEqual(expected, actual)

    def test_get_snapshots_api_error(self):
        """get_snapshot should raise if the api couldn't be queried.
        """
        # mock return from get_all_snapshot_names.
        snapshot_names = {'snap1', 'snap2'}

        patch(
            'sat.fwclient.FUSClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        self.mock_get.side_effect = APIError

        err_regex = r'Request to firmware API failed'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_snapshots(['snap1'])

    def test_get_snapshots_key_error(self):
        """get_snapshot should raise if missing 'devices' key.
        """
        # mock return from get_all_snapshot_names.
        snapshot_names = {'snap1', 'snap2'}

        patch(
            'sat.fwclient.FUSClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        badsnaps = {}

        self.mock_get.return_value.json.return_value = badsnaps

        err_regex = r'missing an entry for "devices"'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_snapshots(['snap1'])

    def test_get_snapshots_value_error(self):
        """get_snapshot should raise if the .json() call raised.
        """
        # mock return from get_all_snapshot_names.
        snapshot_names = {'snap1', 'snap2'}

        patch(
            'sat.fwclient.FUSClient.get_all_snapshot_names',
            return_value=snapshot_names).start()

        self.mock_get.return_value.json.side_effect = ValueError

        err_regex = r'The JSON payload was invalid'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_snapshots(['snap1'])

    def test_get_device_firmwares(self):
        """Positive test case for get_device_firmwares.
        """
        ret = {'devices': 'expected'}

        self.mock_get.return_value.json.return_value = ret

        actual = self.fus_client.get_device_firmwares()

        self.assertEqual('expected', actual)
        self.mock_get.assert_called_once_with('version', 'all')

    def test_get_device_firmwares_api_error(self):
        """It should raise if the FUS query fails.
        """
        self.mock_get.side_effect = APIError

        err_regex = r'Error contacting the FUS'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_device_firmwares()

    def test_get_device_firmwares_key_error(self):
        """It should raise if the FUS query fails.
        """
        badsnaps = {}

        self.mock_get.return_value.json.return_value = badsnaps

        err_regex = r'The JSON payload was missing an entry for "devices"'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_device_firmwares()

    def test_get_device_firmwares_value_error(self):
        """It should raise if invalid JSON was received.
        """
        self.mock_get.return_value.json.side_effect = ValueError

        err_regex = r'The JSON received was invalid'
        with self.assertRaisesRegex(APIError, err_regex):
            self.fus_client.get_device_firmwares()


if __name__ == '__main__':
    unittest.main()
