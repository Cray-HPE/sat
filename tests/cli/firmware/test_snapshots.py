"""
Unit tests for sat.cli.firmware logic involving snapshots.

Copyright 2020 Cray Inc. All Rights Reserved.
"""

import unittest
from unittest import mock

import sat.cli.firmware.snapshots
from sat.apiclient import APIError


class TestFirmwareSnapshot(unittest.TestCase):
    """Snapshot-related tests for firmware."""

    def tearDown(self):
        mock.patch.stopall()

    def test_get_all_snapshot_names(self):
        """Verify that list snapshots returns a list of available snapshots

        The JSON return from the api needs to be a dict like...

            {'snapshots': [{'name': 'name1'}, {'name', 'name2'},...]}
        """
        mock_json = {
            'snapshots': [
                {'name': 'snap1'},
                {'name': 'snap2'},
            ]
        }

        mock_fw_response = mock.Mock()
        mock_fw_client = mock.Mock()

        # approximately the order in which this stuff is called.
        mock.patch(
            'sat.cli.firmware.snapshots.FirmwareClient',
            return_value=mock_fw_client).start()

        mock_fw_client.get.return_value = mock_fw_response
        mock_fw_response.json.return_value = mock_json

        known_snaps = sat.cli.firmware.snapshots.get_all_snapshot_names()

        self.assertTrue('snap1' in known_snaps)
        self.assertTrue('snap2' in known_snaps)

    def test_describe_snapshot(self):
        """Positive test case of _describe_snapshot.

        The only thing this function requries is that the firmware API
        return a dict that contains a 'devices' key at the top level, and
        the value associated with that key should be returned.
        """
        mock_json = {'devices': 'kablarg'}

        mock_fw_response = mock.Mock()
        mock_fw_client = mock.Mock()

        # approximately the order in which this stuff is called.
        mock.patch(
            'sat.cli.firmware.snapshots.FirmwareClient',
            return_value=mock_fw_client).start()

        mock_fw_client.get.return_value = mock_fw_response
        mock_fw_response.json.return_value = mock_json

        devices = sat.cli.firmware.snapshots._describe_snapshot('whatever')

        self.assertEqual('kablarg', devices)

    def test_describe_snapshots(self):
        """Positive test case of describe_snapshots.

        Snapshots that aren't known should not be returned.
        """
        known_snaps = {'snap1', 'snap2'}

        # every call to _describe_snapshot will return this
        mock_describe_snapshot_return = {'devices': 'kablarg'}

        mock_fw_response = mock.Mock()
        mock_fw_client = mock.Mock()

        mock.patch(
            'sat.cli.firmware.snapshots.FirmwareClient',
            return_value=mock_fw_client).start()

        mock.patch(
            'sat.cli.firmware.snapshots.get_all_snapshot_names',
            return_value=known_snaps).start()

        mock.patch(
            'sat.cli.firmware.snapshots._describe_snapshot',
            return_value=mock_describe_snapshot_return).start()

        mock_fw_client.get.return_value = mock_fw_response
        mock_fw_response.json.return_value = mock_describe_snapshot_return

        devices = sat.cli.firmware.snapshots.describe_snapshots(['snap1', 'snap2', 'snap3'])

        self.assertIn('snap1', devices)
        self.assertIn('snap2', devices)
        self.assertNotIn('snap3', devices)

    def test_get_all_snapshot_names_apierror(self):
        """get_all_snapshot_names should raise if the FW API raises.
        """
        mock_fw_client = mock.Mock()

        mock.patch(
            'sat.cli.firmware.snapshots.FirmwareClient',
            return_value=mock_fw_client).start()

        mock_fw_client.get.side_effect = APIError

        with self.assertRaises(APIError):
            sat.cli.firmware.snapshots.get_all_snapshot_names()

    def test_describe_snapshot_apierror(self):
        """Same as above, but wth describe_snapshot.
        """
        mock_fw_client = mock.Mock()

        # approximately the order in which this stuff is called.
        mock.patch(
            'sat.cli.firmware.snapshots.FirmwareClient',
            return_value=mock_fw_client).start()

        mock_fw_client.get.side_effect = APIError

        with self.assertRaises(APIError):
            sat.cli.firmware.snapshots._describe_snapshot('whatever')

    def test_describe_snapshots_apierror(self):
        """Same as above, but wth describe_snapshots.
        """
        mock_fw_client = mock.Mock()

        # approximately the order in which this stuff is called.
        mock.patch(
            'sat.cli.firmware.snapshots.FirmwareClient',
            return_value=mock_fw_client).start()

        mock_fw_client.get.side_effect = APIError

        with self.assertRaises(APIError):
            sat.cli.firmware.snapshots.describe_snapshots(['whatever'])

    def test_describe_snapshots_apierror2(self):
        """describe_snapshots should raise if get_all_snapshot_names raises.
        """
        mock_fw_client = mock.Mock()

        # approximately the order in which this stuff is called.
        mock.patch(
            'sat.cli.firmware.snapshots.FirmwareClient',
            return_value=mock_fw_client).start()

        mock.patch(
            'sat.cli.firmware.snapshots.get_all_snapshot_names',
            side_effect=APIError).start()

        with self.assertRaises(APIError):
            sat.cli.firmware.snapshots.describe_snapshots(['whatever'])


if __name__ == '__main__':
    unittest.main()
