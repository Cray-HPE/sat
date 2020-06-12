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

from unittest.mock import Mock, patch
import unittest

import requests

import sat.apiclient
from sat.apiclient import APIError, APIGatewayClient
from sat.fwclient import FASClient, FUSClient
import sat.config


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


if __name__ == '__main__':
    unittest.main()
