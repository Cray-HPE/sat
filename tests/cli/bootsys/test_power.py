#
# MIT License
#
# (C) Copyright 2020, 2024 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.bootsys.power module.
"""
import logging
import unittest
from unittest.mock import patch

from sat.apiclient import APIError
from sat.cli.bootsys.power import (PCSPowerWaiter,
                                   get_nodes_by_role_and_state)
from tests.common import ExtendedTestCase


class TestPCSPowerWaiter(ExtendedTestCase):
    """Tests for the PCSPowerWaiter."""

    def setUp(self):
        """Set up some patches and shared objects."""
        self.mock_pcs_client_cls = patch('sat.cli.bootsys.power.PCSClient').start()
        self.mock_pcs_client = self.mock_pcs_client_cls.return_value
        self.mock_sat_session = patch('sat.cli.bootsys.power.SATSession').start()

        self.members = {'x5000c0s0b0n0', 'x5000c0s1b0n0'}
        self.power_state = 'off'
        self.timeout = 60
        self.poll_interval = 5
        self.suppress_warnings = True
        self.waiter = PCSPowerWaiter(self.members, self.power_state,
                                     self.timeout, self.poll_interval, self.suppress_warnings)

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of a PCSPowerWaiter"""
        self.assertEqual(self.members, self.waiter.members)
        self.assertEqual(self.power_state, self.waiter.power_state)
        self.assertEqual(self.timeout, self.waiter.timeout)
        self.assertEqual(self.poll_interval, self.waiter.poll_interval)
        self.mock_pcs_client_cls.assert_called_once_with(self.mock_sat_session.return_value)
        self.assertEqual(self.mock_pcs_client, self.waiter.pcs_client)

    def test_condition_name(self):
        """Test the condition_name of the PCSPowerWaiter"""
        self.assertEqual(f'PCS power {self.power_state}', self.waiter.condition_name())

    def test_member_has_completed_complete(self):
        """Test member_has_completed when it has reached desired power state."""
        member = 'x5000c0s0b0n0'
        self.mock_pcs_client.get_xname_power_state.return_value = self.power_state
        self.assertTrue(self.waiter.member_has_completed(member))
        self.mock_pcs_client.get_xname_power_state.assert_called_once_with(member)

    def test_member_has_completed_incomplete(self):
        """Test member_has_completed when it has not reach desired power state."""
        member = 'x5000c0s0b0n0'
        power_state = 'on'
        self.mock_pcs_client.get_xname_power_state.return_value = power_state
        # This assertion ensures that later edits to these tests don't invalidate this test case
        self.assertNotEqual(power_state, self.power_state)
        self.assertFalse(self.waiter.member_has_completed(member))
        self.mock_pcs_client.get_xname_power_state.assert_called_once_with(member)

    def test_member_has_completed_api_error(self):
        """Test member_has_completed when the PCSClient raises and APIError."""
        member = 'x5000c0s0b0n0'
        api_err_msg = 'PCS failure'
        self.mock_pcs_client.get_xname_power_state.side_effect = APIError(api_err_msg)
        with self.assertLogs(level=logging.DEBUG) as cm:
            self.assertFalse(self.waiter.member_has_completed(member))
        self.assert_in_element(f'Failed to query power state: {api_err_msg}', cm.output)


class TestGetNodesByRoleAndState(unittest.TestCase):
    """Test the get_nodes_by_role_and_state function."""

    def setUp(self):
        """Set up some mocks."""
        self.compute_nodes = ['x1000c0s0b0n0', 'x1000c0s0b0n1']
        self.application_nodes = ['x3000c0s26b0n0', 'x3000c0s28b0n0']
        self.management_nodes = ['x3000c0s1b0n0', 'x3000c0s3b0n0', 'x3000c0s5b0n0', 'x3000c0s7b0n0']
        self.nodes_by_role = {
            'compute': self.compute_nodes,
            'application': self.application_nodes,
            'management': self.management_nodes
        }
        self.all_nodes_by_state = {
            'on': self.management_nodes + self.application_nodes[:1],
            'off': self.compute_nodes + self.application_nodes[1:]
        }

        def mock_get_xnames(params):
            return self.nodes_by_role.get(params.get('role'), [])

        def mock_get_xnames_power_state(xnames):
            return {
                'on': [node for node in self.all_nodes_by_state['on'] if node in xnames],
                'off': [node for node in self.all_nodes_by_state['off'] if node in xnames],
            }

        self.mock_hsm_client = patch('sat.cli.bootsys.power.HSMClient').start().return_value
        self.mock_hsm_client.get_component_xnames = mock_get_xnames
        self.mock_pcs_client = patch('sat.cli.bootsys.power.PCSClient').start().return_value
        self.mock_pcs_client.get_xnames_power_state = mock_get_xnames_power_state
        self.mock_sat_session = patch('sat.cli.bootsys.power.SATSession').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_none_matching_role(self):
        """Test get_nodes_by_role_and_state with none matching role."""
        self.assertEqual([], get_nodes_by_role_and_state('gpu', 'on'))

    def test_no_matching_role_and_state(self):
        """Test get_nodes_by_role_and_state when none w/ role are in power state."""
        self.assertEqual([], get_nodes_by_role_and_state('compute', 'on'))
        self.assertEqual([], get_nodes_by_role_and_state('management', 'off'))

    def test_matching_role_and_state(self):
        """Test get_nodes_by_role_and_state when some or all w/ role are in power state."""
        self.assertEqual(self.compute_nodes, get_nodes_by_role_and_state('compute', 'off'))
        self.assertEqual(self.management_nodes, get_nodes_by_role_and_state('management', 'on'))
        self.assertEqual(self.application_nodes[:1],
                         get_nodes_by_role_and_state('application', 'on'))
        self.assertEqual(self.application_nodes[1:],
                         get_nodes_by_role_and_state('application', 'off'))


if __name__ == '__main__':
    unittest.main()
