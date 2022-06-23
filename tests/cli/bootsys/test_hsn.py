#
# MIT License
#
# (C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.bootsys.hsn module.
"""
import unittest
from unittest.mock import patch

from sat.cli.bootsys.hsn import HSNBringupWaiter, HSNPort
from sat.cli.bootsys.state_recorder import StateError


class TestHSNBringupWaiter(unittest.TestCase):
    """Test the HSN bringup waiter"""
    def setUp(self):
        self.mock_session = patch('sat.cli.bootsys.hsn.SATSession').start()
        mock_fabric_client_cls = patch('sat.cli.bootsys.hsn.FabricControllerClient').start()
        self.mock_fabric_client = mock_fabric_client_cls.return_value
        self.mock_fabric_client.get_fabric_edge_ports.return_value = {
            'fabric-ports': [
                'x3000c0r24j4p0',
                'x3000c0r24j4p1',
                'x3000c0r24j8p0',  # exists, does not have status, was present and enabled before shutdown
                'x3000c0r24j8p1'   # exists, is enabled, was not present before shutdown
            ],
            'edge-ports': [
                'x3000c0r24j14p0',
                'x3000c0r24j14p1',
                'x3000c0r24j16p0',  # exists, does not have status, was present and disabled before shutdown
                'x3000c0r24j16p1',  # exists, is disabled, was not present before shutdown
            ]
        }
        self.mock_fabric_client.get_fabric_edge_ports_enabled_status.return_value = {
            'fabric-ports': {
                'x3000c0r24j4p0': True,
                'x3000c0r24j4p1': False,
                # 'x3000c0r24j8p0' intentionally omitted
                'x3000c0r24j8p1': True
            },
            'edge-ports': {
                'x3000c0r24j14p0': True,
                'x3000c0r24j14p1': False,
                # 'x3000c0r24j16p0' intentionally omitted
                'x3000c0r24j16p1': False
            }
        }

        mock_hsn_recorder_cls = patch('sat.cli.bootsys.hsn.HSNStateRecorder').start()
        self.mock_hsn_recorder = mock_hsn_recorder_cls.return_value
        self.mock_hsn_recorder.get_stored_state.return_value = {
            'fabric-ports': {
                'x3000c0r24j4p0': True,
                'x3000c0r24j4p1': False,
                'x3000c0r24j8p0': True
                # 'x3000c0r24j8p1' intentionally omitted
            },
            'edge-ports': {
                'x3000c0r24j14p0': True,
                'x3000c0r24j14p1': True,
                'x3000c0r24j16p0': False
                # 'x3000c0r24j16p1' intentionally omitted
            }
        }

        self.timeout = 1
        self.poll_interval = 1
        self.waiter = HSNBringupWaiter(self.timeout, poll_interval=self.poll_interval)

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of an HSNBringupWaiter."""
        self.assertEqual(self.timeout, self.waiter.timeout)
        self.assertEqual(self.poll_interval, self.waiter.poll_interval)
        self.assertEqual(self.mock_fabric_client, self.waiter.fabric_client)
        self.assertEqual(self.mock_hsn_recorder, self.waiter.hsn_state_recorder)
        self.assertEqual({}, self.waiter.current_hsn_state)

    def test_on_check_action(self):
        """Test that on_check_action calls appropriate fabric client method."""
        self.waiter.on_check_action()
        self.mock_fabric_client.get_fabric_edge_ports_enabled_status.assert_called_once_with()

    def test_stored_hsn_state(self):
        """Test that the stored_hsn_state gets its info from the HSNStateRecorder and caches itself."""
        expected = {'port-set': {'port-xname': 'x5000c0r1j4p0'}}
        self.mock_hsn_recorder.get_stored_state.side_effect = [expected, {}]
        self.assertEqual(expected, self.waiter.stored_hsn_state)
        # It should be cached, so it should not change
        self.assertEqual(expected, self.waiter.stored_hsn_state)
        self.mock_hsn_recorder.get_stored_state.assert_called_once_with()

    def test_stored_hsn_state_error(self):
        """Test stored_hsn_state when the HSNStateRecorder has an error."""
        expected = {}
        self.mock_hsn_recorder.get_stored_state.side_effect = StateError
        self.assertEqual(expected, self.waiter.stored_hsn_state)
        self.mock_hsn_recorder.get_stored_state.assert_called_once_with()

    def test_pre_wait_action(self):
        """Test that the pre_wait_action sets up members."""
        expected_members = {
            HSNPort('fabric-ports', 'x3000c0r24j4p0'),
            HSNPort('fabric-ports', 'x3000c0r24j4p1'),
            HSNPort('fabric-ports', 'x3000c0r24j8p0'),
            HSNPort('fabric-ports', 'x3000c0r24j8p1'),
            HSNPort('edge-ports', 'x3000c0r24j14p0'),
            HSNPort('edge-ports', 'x3000c0r24j14p1'),
            HSNPort('edge-ports', 'x3000c0r24j16p0'),
            HSNPort('edge-ports', 'x3000c0r24j16p1')
        }
        self.waiter.pre_wait_action()

        self.assertEqual(expected_members, self.waiter.members)

    def test_ports_basic_enabled(self):
        """Test that enabled ports present before shutdown have completed."""
        ports = [
            HSNPort('fabric-ports', 'x3000c0r24j4p0'),
            HSNPort('edge-ports', 'x3000c0r24j14p0')
        ]
        # Have to call this to get self.waiter.current_hsn_state updated
        self.waiter.on_check_action()
        for port in ports:
            self.assertTrue(self.waiter.member_has_completed(port))

    def test_port_disabled_before_and_after(self):
        """Test that a disabled port that was disabled before shutdown is complete."""
        self.waiter.on_check_action()
        self.assertTrue(self.waiter.member_has_completed(HSNPort('fabric-ports', 'x3000c0r24j4p1')))

    def test_port_enabled_before_disabled_after(self):
        """Test that a disabled port that was enabled before shutdown is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('edge-ports', 'x3000c0r24j14p1')))

    def test_port_enabled_before_missing_after(self):
        """Test that a port that was enabled before shutdown, now missing status is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('fabric-ports', 'x3000c0r24j8p0')))

    def test_port_missing_before_enabled_after(self):
        """Test that a port that was missing before shutdown, enabled after is complete."""
        self.waiter.on_check_action()
        self.assertTrue(self.waiter.member_has_completed(HSNPort('fabric-ports', 'x3000c0r24j8p1')))

    def test_port_disabled_before_missing_after(self):
        """Test that a port that was disabled before shutdown, missing after is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('edge-ports', 'x3000c0r24j16p0')))

    def test_port_missing_before_disabled_after(self):
        """Test that a port that was missing before shutdown, disabled after is not complete."""
        self.waiter.on_check_action()
        self.assertFalse(self.waiter.member_has_completed(HSNPort('edge-ports', 'x3000c0r24j16p1')))
