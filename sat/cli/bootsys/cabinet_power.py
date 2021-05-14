"""
Powers on and off liquid-cooled compute cabinets.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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

from sat.apiclient import APIError, CAPMCClient, HSMClient
from sat.cli.bootsys.discovery import HMSDiscoveryCronJob, HMSDiscoveryError, HMSDiscoveryScheduledWaiter
from sat.cli.bootsys.power import CAPMCPowerWaiter
from sat.config import get_config_value
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)


def do_air_cooled_cabinets_power_off(args):
    """Power off the air-cooled cabinets without management nodes in the system.

    Args:
        args (argparse.Namespace): The parsed bootsys arguments.

    Returns:
        None
    """
    hsm_client = HSMClient(SATSession())
    try:
        river_nodes = hsm_client.get_component_xnames({'type': 'Node',
                                                       'class': 'River'})
    except APIError as err:
        LOGGER.error(f'Failed to get the xnames of the air-cooled components: {err}')
        raise SystemExit(1)

    try:
        river_mgmt_nodes = hsm_client.get_component_xnames({'type': 'Node',
                                                            'role': 'Management',
                                                            'class': 'River'})
    except APIError as err:
        LOGGER.error(f'Failed to get the xnames of the management nodes: {err}')
        raise SystemExit(1)

    node_xnames = list(set(river_nodes) - set(river_mgmt_nodes))
    print(f'Powering off {len(node_xnames)} non-management nodes in air-cooled cabinets.')
    capmc_client = CAPMCClient(SATSession())
    try:
        capmc_client.set_xnames_power_state(node_xnames, 'off', force=True)
    except APIError as err:
        LOGGER.warning(f'Failed to power off all air-cooled non-management nodes: {err}')

    print(f'Waiting for {len(node_xnames)} non-management nodes in air-cooled cabinets '
          f'to reach powered off state.')
    capmc_waiter = CAPMCPowerWaiter(node_xnames, 'off',
                                    get_config_value('bootsys.capmc_timeout'))
    timed_out_xnames = capmc_waiter.wait_for_completion()

    if timed_out_xnames:
        LOGGER.error(f'The following non-management nodes failed to reach the powered off '
                     f'state after powering off with CAPMC: {timed_out_xnames}')
        raise SystemExit(1)

    print(f'All {len(node_xnames)} non-management nodes in air-cooled cabinets '
          f'reached powered off state according to CAPMC.')


def do_liquid_cooled_cabinets_power_off(args):
    """Power off the liquid-cooled compute cabinets in the system.

    Args:
        args (argparse.Namespace): The parsed bootsys arguments.

    Returns:
        None
    """
    hsm_client = HSMClient(SATSession())
    try:
        chassis_xnames = hsm_client.get_component_xnames({'type': 'Chassis', 'class': 'Mountain'})
    except APIError as err:
        LOGGER.error(f'Failed to get the xnames of the liquid-cooled chassis: {err}')
        raise SystemExit(1)

    print(f'Powering off all {len(chassis_xnames)} liquid-cooled chassis.')
    capmc_client = CAPMCClient(SATSession())
    try:
        capmc_client.set_xnames_power_state(chassis_xnames, 'off', recursive=True)
    except APIError as err:
        LOGGER.warning(f'Failed to power off all cabinets: {err}')

    print(f'Waiting for {len(chassis_xnames)} liquid-cooled chassis to reach '
          f'powered off state.')
    capmc_waiter = CAPMCPowerWaiter(chassis_xnames, 'off',
                                    get_config_value('bootsys.capmc_timeout'))
    timed_out_xnames = capmc_waiter.wait_for_completion()

    if timed_out_xnames:
        LOGGER.error(f'The following chassis failed to reach the powered off '
                     f'state after powering off with CAPMC: {timed_out_xnames}')
        raise SystemExit(1)

    print(f'All {len(chassis_xnames)} liquid-cooled chassis reached powered off '
          f'state according to CAPMC.')


def do_cabinets_power_off(args):
    """Power off the compute cabinets in the system.

    Args:
        args (argparse.Namespace): The parsed bootsys arguments.

    Returns:
        None
    """

    print(f'Suspending {HMSDiscoveryCronJob.FULL_NAME} to ensure components '
          f'remain powered off.')
    try:
        HMSDiscoveryCronJob().set_suspend_status(True)
    except HMSDiscoveryError as err:
        LOGGER.error(f'Failed to suspend discovery: {err}')
        raise SystemExit(1)

    do_liquid_cooled_cabinets_power_off(args)
    do_air_cooled_cabinets_power_off(args)


def do_cabinets_power_on(args):
    """Power on the liquid-cooled compute cabinets in the system.

    Do not do this with a manual call to CAPMC. Instead, restart the
    hms-discovery cronjob in k8s, and let it do the power on for us. Then wait
    for all the compute node BMCs of type "Mountain" to be powered on in CAPMC.

    Args:
        args (argparse.Namespace): The parsed bootsys arguments.

    Returns:
        None
    """
    print(f'Resuming {HMSDiscoveryCronJob.FULL_NAME}.')
    try:
        HMSDiscoveryCronJob().set_suspend_status(False)
    except HMSDiscoveryError as err:
        LOGGER.error(f'Failed to resume discovery: {err}')
        raise SystemExit(1)

    print(f'Waiting for {HMSDiscoveryCronJob.FULL_NAME} to be scheduled.')
    try:
        hms_discovery_waiter = HMSDiscoveryScheduledWaiter()
    except HMSDiscoveryError as err:
        LOGGER.error(f'Failed to start waiting on HMS discovery job being '
                     f'rescheduled after resume: {err}')
        raise SystemExit(1)

    hms_discovery_scheduled = hms_discovery_waiter.wait_for_completion()
    if not hms_discovery_scheduled:
        LOGGER.error(f'The {HMSDiscoveryCronJob.FULL_NAME} was not scheduled '
                     f'within expected window after being resumed.')
        raise SystemExit(1)

    print('Waiting for NodeBMCs in liquid-cooled cabinets to be powered on.')
    hsm_client = HSMClient(SATSession())
    try:
        mtn_node_bmcs = hsm_client.get_component_xnames({'Type': 'NodeBMC',
                                                         'Class': 'Mountain'},
                                                        omit_empty=False)
    except APIError as err:
        LOGGER.error(f'Failed to get list of NodeBMCs to wait on: {err}')
        raise SystemExit(1)

    # Once NodeBMCs are powered on, it is possible to boot nodes with BOS.
    # Suppress warnings about CAPMC state query errors because we expect the
    # BMCs/node controllers to be unreachable until they are powered on.
    bmc_waiter = CAPMCPowerWaiter(mtn_node_bmcs, 'on',
                                  get_config_value('bootsys.discovery_timeout'),
                                  suppress_warnings=True)
    bmcs_timed_out = bmc_waiter.wait_for_completion()

    if bmcs_timed_out:
        LOGGER.error(f'The following compute node BMC(s) failed to reach a powered '
                     f'on state after resuming {HMSDiscoveryCronJob.FULL_NAME}: '
                     f'{", ".join(bmcs_timed_out)}')
        raise SystemExit(1)

    print('All NodeBMCs have reached powered on state.')
