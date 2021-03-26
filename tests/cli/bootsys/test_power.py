"""
Unit tests for the sat.cli.bootsys.power module.

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
import logging
import unittest
from unittest.mock import call, patch

from sat.apiclient import APIError
from sat.cli.bootsys.power import (
    CAPMCError,
    CAPMCPowerWaiter,
    do_nodes_power_off,
    get_nodes_by_role_and_state)
from tests.common import ExtendedTestCase


class TestCAPMCPowerWaiter(ExtendedTestCase):
    """Tests for the CAPMCPowerWaiter."""

    def setUp(self):
        """Set up some patches and shared objects."""
        self.mock_capmc_client_cls = patch('sat.cli.bootsys.power.CAPMCClient').start()
        self.mock_capmc_client = self.mock_capmc_client_cls.return_value
        self.mock_sat_session = patch('sat.cli.bootsys.power.SATSession').start()

        self.members = {'x5000c0s0b0n0', 'x5000c0s1b0n0'}
        self.power_state = 'off'
        self.timeout = 60
        self.poll_interval = 5
        self.suppress_warnings = True
        self.waiter = CAPMCPowerWaiter(self.members, self.power_state,
                                       self.timeout, self.poll_interval, self.suppress_warnings)

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of a CAPMCPowerWaiter"""
        self.assertEqual(self.members, self.waiter.members)
        self.assertEqual(self.power_state, self.waiter.power_state)
        self.assertEqual(self.timeout, self.waiter.timeout)
        self.assertEqual(self.poll_interval, self.waiter.poll_interval)
        self.mock_capmc_client_cls.assert_called_once_with(self.mock_sat_session.return_value,
                                                           suppress_warnings=self.suppress_warnings)
        self.assertEqual(self.mock_capmc_client, self.waiter.capmc_client)

    def test_condition_name(self):
        """Test the condition_name of the CAPMCPowerWaiter"""
        self.assertEqual(f'CAPMC power {self.power_state}', self.waiter.condition_name())

    def test_member_has_completed_complete(self):
        """Test member_has_completed when it has reached desired power state."""
        member = 'x5000c0s0b0n0'
        self.mock_capmc_client.get_xname_power_state.return_value = self.power_state
        self.assertTrue(self.waiter.member_has_completed(member))
        self.mock_capmc_client.get_xname_power_state.assert_called_once_with(member)

    def test_member_has_completed_incomplete(self):
        """Test member_has_completed when it has not reach desired power state."""
        member = 'x5000c0s0b0n0'
        power_state = 'on'
        self.mock_capmc_client.get_xname_power_state.return_value = power_state
        # This assertion ensures that later edits to these tests don't invalidate this test case
        self.assertNotEqual(power_state, self.power_state)
        self.assertFalse(self.waiter.member_has_completed(member))
        self.mock_capmc_client.get_xname_power_state.assert_called_once_with(member)

    def test_member_has_completed_api_error(self):
        """Test member_has_completed when the CAPMCClient raises and APIError."""
        member = 'x5000c0s0b0n0'
        api_err_msg = 'CAPMC failure'
        self.mock_capmc_client.get_xname_power_state.side_effect = APIError(api_err_msg)
        with self.assertLogs(level=logging.DEBUG) as cm:
            self.assertFalse(self.waiter.member_has_completed(member))
        self.assert_in_element(f'Failed to query power state: {api_err_msg}', cm.output)


class TestDoNodesPowerOff(ExtendedTestCase):
    """Test the do_nodes_power_off function."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_capmc_client = patch('sat.cli.bootsys.power.CAPMCClient').start().return_value
        self.mock_sat_session = patch('sat.cli.bootsys.power.SATSession').start()

        self.timeout = 10  # does not actually affect duration; just for asserts
        self.compute_nodes = ['x1000c0s0b0n0', 'x1000c0s0b0n1']
        self.application_nodes = ['x3000c0s24b1n0', 'x3000c0s24b2n0']
        self.all_nodes = set(self.compute_nodes + self.application_nodes)
        self.timed_out_nodes = set()

        def mock_get_nodes(role, _):
            if role == 'compute':
                return self.compute_nodes
            elif role == 'application':
                return self.application_nodes
            else:
                return []

        self.mock_get_nodes = patch('sat.cli.bootsys.power.get_nodes_by_role_and_state',
                                    mock_get_nodes).start()

        self.mock_capmc_waiter_cls = patch('sat.cli.bootsys.power.CAPMCPowerWaiter').start()
        self.mock_capmc_waiter = self.mock_capmc_waiter_cls.return_value
        self.mock_capmc_waiter.wait_for_completion.return_value = self.timed_out_nodes

        self.mock_print = patch('builtins.print').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def assert_print_calls(self, num_wait=None, include_wait_call=True):
        """Assert that the expected print calls are made.

        Args:
            num_wait (int): the number of nodes waited on. defaults to
                len(self.all_nodes)
            include_wait_call (bool): whether to include a print statement
                for a wait.
        """
        num_wait = num_wait if num_wait is not None else len(self.all_nodes)
        calls = [call(f'Forcing power off of {len(self.all_nodes)} compute or application '
                      f'nodes still powered on: {", ".join(self.all_nodes)}')]
        if include_wait_call:
            calls.append(call(f'Waiting {self.timeout} seconds until {num_wait} nodes '
                              f'reach powered off state according to CAPMC.'))
        self.mock_print.assert_has_calls(calls)

    def assert_capmc_client_call(self):
        """Assert the call is made to the CAPMCClient to power off nodes."""
        self.mock_capmc_client.set_xnames_power_state.assert_called_once_with(
            list(self.all_nodes), 'off', force=True
        )

    def test_do_nodes_power_off_already_off(self):
        """Test do_nodes_power_off when all nodes are already off."""
        self.compute_nodes = []
        self.application_nodes = []
        timed_out, failed = do_nodes_power_off(self.timeout)

        self.assertEqual(set(), timed_out)
        self.assertEqual(set(), failed)

        self.mock_capmc_client.set_xnames_power_state.assert_not_called()
        self.mock_capmc_waiter_cls.assert_not_called()

    def test_do_nodes_power_off_success(self):
        """Test do_nodes_power_off in the successful case."""
        timed_out, failed = do_nodes_power_off(self.timeout)

        self.assert_capmc_client_call()
        self.assertEqual(set(), timed_out)
        self.assertEqual(set(), failed)
        self.mock_capmc_waiter_cls.assert_called_once_with(
            self.all_nodes, 'off', self.timeout
        )
        self.mock_capmc_waiter.wait_for_completion.assert_called_once_with()
        self.assert_print_calls()

    def test_do_nodes_power_off_one_failed(self):
        """Test do_nodes_power_off when one fails to power off and the rest succeed."""
        expected_failed = {self.compute_nodes[0]}
        failed_xname_errs = [
            {
                'e': 1,
                'err_msg': 'NodeBMC unreachable',
                'xname': self.compute_nodes[0]
            }
        ]
        capmc_err_msg = 'Power off operation failed.'
        capmc_err = CAPMCError(capmc_err_msg, xname_errs=failed_xname_errs)
        self.mock_capmc_client.set_xnames_power_state.side_effect = capmc_err

        with self.assertLogs(level=logging.WARNING) as cm:
            timed_out, failed = do_nodes_power_off(self.timeout)

        self.assert_in_element(f'{capmc_err_msg}\n'
                               f'xname(s) ({self.compute_nodes[0]}) failed with '
                               f'e={failed_xname_errs[0]["e"]} and '
                               f'err_msg="{failed_xname_errs[0]["err_msg"]}"',
                               cm.output)
        self.assert_capmc_client_call()
        self.assertEqual(set(), timed_out)
        self.assertEqual(expected_failed, failed)
        self.mock_capmc_waiter_cls.assert_called_once_with(
            self.all_nodes - expected_failed, 'off', self.timeout
        )
        self.mock_capmc_waiter.wait_for_completion.assert_called_once_with()
        self.assert_print_calls(num_wait=len(self.all_nodes - expected_failed))

    def test_do_nodes_power_off_capmc_failed(self):
        """Test do_nodes_power_off when the CAPMC power off request fails."""
        capmc_err_msg = 'CAPMC did not respond'
        capmc_err = CAPMCError(capmc_err_msg)
        expected_failed = self.all_nodes
        self.mock_capmc_client.set_xnames_power_state.side_effect = capmc_err

        with self.assertLogs(level=logging.WARNING) as cm:
            timed_out, failed = do_nodes_power_off(self.timeout)

        self.assert_in_element(capmc_err_msg, cm.output)
        self.assert_capmc_client_call()
        self.assertEqual(set(), timed_out)
        self.assertEqual(expected_failed, failed)
        self.mock_capmc_waiter_cls.assert_not_called()
        self.assert_print_calls(include_wait_call=False)

    def test_do_nodes_power_off_one_timed_out(self):
        """Test do_node_power_off when one node times out."""
        expected_timed_out = {self.compute_nodes[0]}
        self.mock_capmc_waiter.wait_for_completion.return_value = expected_timed_out

        timed_out, failed = do_nodes_power_off(self.timeout)

        self.assert_capmc_client_call()
        self.assertEqual(expected_timed_out, timed_out)
        self.assertEqual(set(), failed)
        self.mock_capmc_waiter_cls.assert_called_once_with(self.all_nodes, 'off', self.timeout)
        self.assert_print_calls()


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
        self.mock_capmc_client = patch('sat.cli.bootsys.power.CAPMCClient').start().return_value
        self.mock_capmc_client.get_xnames_power_state = mock_get_xnames_power_state
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
