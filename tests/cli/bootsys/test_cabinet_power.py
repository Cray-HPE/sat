#
# MIT License
#
# (C) Copyright 2021, 2023 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.bootsys.cabinet_power module.
"""
import logging
import unittest
from argparse import Namespace
from unittest.mock import call, patch

from sat.cli.bootsys.cabinet_power import do_air_cooled_cabinets_power_off, do_cabinets_power_off

from tests.common import ExtendedTestCase


class TestAirCooledCabinetsPowerOff(unittest.TestCase):
    """Tests for do_air_cooled_cabinets_power_off function."""

    def setUp(self):
        self.args = Namespace()
        patch_prefix = 'sat.cli.bootsys.cabinet_power'
        self.mock_sat_session = patch(f'{patch_prefix}.SATSession').start().return_value
        self.mock_hsm_client = patch(f'{patch_prefix}.HSMClient').start().return_value
        self.mock_capmc_client = patch(f'{patch_prefix}.CAPMCClient').start().return_value
        self.mock_capmc_waiter = patch(f'{patch_prefix}.CAPMCPowerWaiter').start().return_value

        # Mock as if we have nodes in slots 1-15 as Management nodes, and the node in slot 17 not
        self.mock_river_nodes = [f'x3000c0s{slot}b0n0' for slot in [1, 3, 5, 7, 9, 11, 13, 15, 17]]
        self.num_non_mgmt_river_nodes = 1
        self.mock_river_mgmt_nodes = self.mock_river_nodes[:-self.num_non_mgmt_river_nodes]
        self.mock_river_non_mgmt_nodes = self.mock_river_nodes[-self.num_non_mgmt_river_nodes:]
        self.timed_out_xnames = []

        def mock_get_component_xnames(params):
            if params.get('class') == 'River':
                if params.get('role') == 'Management':
                    return self.mock_river_mgmt_nodes
                else:
                    return self.mock_river_nodes
            else:
                return []

        self.mock_hsm_client.get_component_xnames.side_effect = mock_get_component_xnames
        self.mock_capmc_waiter.wait_for_completion.return_value = self.timed_out_xnames

    def tearDown(self):
        patch.stopall()

    def assert_hsm_client_calls(self):
        """Helper function to assert the expected HSMClient method calls are made."""
        river_call_params = {'type': 'Node', 'class': 'River'}
        mgmt_call_params = {'type': 'Node', 'class': 'River', 'role': 'Management'}

        self.mock_hsm_client.get_component_xnames.assert_has_calls([
            call(river_call_params),
            call(mgmt_call_params)
        ])

    def test_do_ac_cab_off_non_empty_success(self):
        """Test do_air_cooled_cabinets_power_off with a non-empty set of non-mgmt river nodes"""
        with self.assertLogs(level=logging.INFO) as logs_cm:
            do_air_cooled_cabinets_power_off(self.args)

        self.assert_hsm_client_calls()
        self.mock_capmc_client.set_xnames_power_state.assert_called_once_with(
            self.mock_river_non_mgmt_nodes, 'off', force=True
        )
        self.mock_capmc_waiter.wait_for_completion.assert_called_once_with()
        self.assertEqual(3, len(logs_cm.records))
        self.assertRegex(logs_cm.records[0].message,
                         f'Powering off {self.num_non_mgmt_river_nodes}')
        self.assertRegex(logs_cm.records[1].message,
                         f'Waiting for {self.num_non_mgmt_river_nodes}')
        self.assertRegex(logs_cm.records[2].message,
                         f'All {self.num_non_mgmt_river_nodes}.*reached powered off')

    def test_do_ac_cab_off_non_empty_failure(self):
        """Test do_air_cooled_cabinets_power_off with a non-empty set of non-mgmt river nodes failing"""
        self.timed_out_xnames.append(self.mock_river_non_mgmt_nodes[0])

        with self.assertLogs(level=logging.ERROR) as logs_cm:
            with self.assertRaises(SystemExit):
                do_air_cooled_cabinets_power_off(self.args)

        self.assert_hsm_client_calls()
        self.mock_capmc_client.set_xnames_power_state.assert_called_once_with(
            self.mock_river_non_mgmt_nodes, 'off', force=True
        )
        self.mock_capmc_waiter.wait_for_completion.assert_called_once_with()
        self.assertEqual(1, len(logs_cm.records))
        self.assertRegex(logs_cm.records[0].message,
                         'non-management nodes failed to reach the powered off state.*'
                         f'{self.timed_out_xnames}')

    def test_do_ac_cab_off_empty(self):
        """Test do_air_cooled_cabinets_power_off with an empty set of non-mgmt river nodes"""
        self.mock_river_mgmt_nodes = self.mock_river_nodes
        self.mock_river_non_mgmt_nodes = []

        with self.assertLogs(level=logging.INFO) as logs_cm:
            do_air_cooled_cabinets_power_off(self.args)

        self.assert_hsm_client_calls()
        self.mock_capmc_client.set_xnames_power_state.assert_not_called()
        self.mock_capmc_waiter.wait_for_completion.assert_not_called()
        self.assertEqual(logs_cm.records[0].message,
                         'No non-management nodes in air-cooled cabinets to power off.')


class TestCabinetsPowerOff(ExtendedTestCase):
    """Tests for the cabinet power off process."""
    def setUp(self):
        self.mock_liquid_cooled = patch('sat.cli.bootsys.cabinet_power.do_liquid_cooled_cabinets_power_off').start()
        self.mock_air_cooled = patch('sat.cli.bootsys.cabinet_power.do_air_cooled_cabinets_power_off').start()
        self.mock_cron_job = patch('sat.cli.bootsys.cabinet_power.HMSDiscoveryCronJob').start()
        self.mock_prompt = patch('sat.cli.bootsys.cabinet_power.prompt_continue').start()

        self.args = Namespace()
        self.args.disruptive = False

    def tearDown(self):
        patch.stopall()

    def test_do_cabinets_power_off(self):
        """Test do_cabinets_power_off() with default parameters."""
        do_cabinets_power_off(self.args)
        self.mock_prompt.assert_called_once()

        self.mock_cron_job.assert_called_once_with()
        self.mock_cron_job.return_value.set_suspend_status.assert_called_once_with(True)

        self.mock_liquid_cooled.assert_called_once_with(self.args)
        self.mock_air_cooled.assert_called_once_with(self.args)

    def test_do_cabinets_power_off_without_prompting(self):
        """Test do_cabinets_power_off() wihtout prompting to continue."""
        self.args.disruptive = True
        do_cabinets_power_off(self.args)
        self.mock_prompt.assert_not_called()

        self.mock_cron_job.assert_called_once_with()
        self.mock_cron_job.return_value.set_suspend_status.assert_called_once_with(True)

        self.mock_liquid_cooled.assert_called_once_with(self.args)
        self.mock_air_cooled.assert_called_once_with(self.args)
