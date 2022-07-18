#
# MIT License
#
# (C) Copyright 2020-2022 Hewlett Packard Enterprise Development LP
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
Powers on and off liquid-cooled compute cabinets.
"""
import logging

from sat.apiclient import APIError, CAPMCClient, HSMClient
from sat.cli.bootsys.power import CAPMCPowerWaiter
from sat.config import get_config_value
from sat.hms_discovery import HMSDiscoveryCronJob, HMSDiscoveryError, HMSDiscoveryScheduledWaiter
from sat.session import SATSession
from sat.util import prompt_continue


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
    LOGGER.info(f'Powering off {len(node_xnames)} non-management nodes in air-cooled cabinets.')
    capmc_client = CAPMCClient(SATSession())
    try:
        capmc_client.set_xnames_power_state(node_xnames, 'off', force=True)
    except APIError as err:
        LOGGER.warning(f'Failed to power off all air-cooled non-management nodes: {err}')

    LOGGER.info(f'Waiting for {len(node_xnames)} non-management nodes in air-cooled cabinets '
                f'to reach powered off state.')
    capmc_waiter = CAPMCPowerWaiter(node_xnames, 'off',
                                    get_config_value('bootsys.capmc_timeout'))
    timed_out_xnames = capmc_waiter.wait_for_completion()

    if timed_out_xnames:
        LOGGER.error(f'The following non-management nodes failed to reach the powered off '
                     f'state after powering off with CAPMC: {timed_out_xnames}')
        raise SystemExit(1)

    LOGGER.info(f'All {len(node_xnames)} non-management nodes in air-cooled cabinets '
                f'reached powered off state according to CAPMC.')


def get_xnames_for_power_action(hsm_client):
    """Get xnames of RouterModules, ComputeModules, and Chassis.

    This helper function gets all the xnames used in a power action (turn on or
    turn off) individually since CAPMC does not support recursively powering off
    disabled components in Shasta v1.5. See CRAYSAT-920.

    Returns:
        [str]: all xnames for RouterModules, ComputeModules, and Chassis in
               the system.
    """
    return [component
            for component_type in ['RouterModule', 'ComputeModule', 'Chassis']
            for component in hsm_client.get_component_xnames({'type': component_type,
                                                              'class': 'Mountain',
                                                              'enabled': True})]


def do_liquid_cooled_cabinets_power_off(args):
    """Power off the liquid-cooled compute cabinets in the system.

    Args:
        args (argparse.Namespace): The parsed bootsys arguments.

    Returns:
        None
    """
    hsm_client = HSMClient(SATSession())
    try:
        xnames_to_power_off = get_xnames_for_power_action(hsm_client)
    except APIError as err:
        LOGGER.error(f'Failed to get the xnames of the liquid-cooled chassis and sub-components: {err}')
        raise SystemExit(1)

    LOGGER.info(f'Powering off all liquid-cooled chassis, compute modules, and router modules. '
                f'({len(xnames_to_power_off)} components total)')
    capmc_client = CAPMCClient(SATSession())
    try:
        capmc_client.set_xnames_power_state(xnames_to_power_off, 'off')
    except APIError as err:
        LOGGER.warning(f'Failed to power off all cabinets: {err}')
        if hasattr(err, '__cause__'):
            LOGGER.warning(f'Cause: {err.__cause__}')

    LOGGER.info(f'Waiting for {len(xnames_to_power_off)} components to reach '
                f'powered off state.')
    capmc_waiter = CAPMCPowerWaiter(xnames_to_power_off, 'off',
                                    get_config_value('bootsys.capmc_timeout'))
    timed_out_xnames = capmc_waiter.wait_for_completion()

    if timed_out_xnames:
        LOGGER.error(f'The following components failed to reach the powered off '
                     f'state after powering off with CAPMC: {timed_out_xnames}')
        raise SystemExit(1)

    LOGGER.info(f'All {len(xnames_to_power_off)} liquid-cooled chassis components reached powered off '
                f'state according to CAPMC.')


def do_cabinets_power_off(args):
    """Power off the compute cabinets in the system.

    Args:
        args (argparse.Namespace): The parsed bootsys arguments.

    Returns:
        None
    """
    if not args.disruptive:
        prompt_continue('powering off compute cabinets')

    LOGGER.info(f'Suspending {HMSDiscoveryCronJob.FULL_NAME} to ensure components '
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
    for all the compute modules of type "Mountain" to be powered on in CAPMC.

    Args:
        args (argparse.Namespace): The parsed bootsys arguments.

    Returns:
        None
    """
    LOGGER.info(f'Resuming {HMSDiscoveryCronJob.FULL_NAME}.')
    try:
        HMSDiscoveryCronJob().set_suspend_status(False)
    except HMSDiscoveryError as err:
        LOGGER.error(f'Failed to resume discovery: {err}')
        raise SystemExit(1)

    LOGGER.info(f'Waiting for {HMSDiscoveryCronJob.FULL_NAME} to be scheduled.')
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

    LOGGER.info('Waiting for ComputeModules in liquid-cooled cabinets to be powered on.')
    hsm_client = HSMClient(SATSession())
    try:
        xnames_to_power_on = get_xnames_for_power_action(hsm_client)
    except APIError as err:
        LOGGER.error(f'Failed to get list of ComputeModules to wait on: {err}')
        raise SystemExit(1)

    # Once ComputeModules are powered on, it is possible to boot nodes with BOS.
    # Suppress warnings about CAPMC state query errors because we expect the
    # compute modules to be unreachable until they are powered on.
    module_waiter = CAPMCPowerWaiter(xnames_to_power_on, 'on',
                                     get_config_value('bootsys.discovery_timeout'),
                                     suppress_warnings=True)
    modules_timed_out = module_waiter.wait_for_completion()

    if modules_timed_out:
        LOGGER.error(f'The following compute module(s) failed to reach a powered '
                     f'on state after resuming {HMSDiscoveryCronJob.FULL_NAME}: '
                     f'{", ".join(modules_timed_out)}')
        raise SystemExit(1)

    LOGGER.info('All ComputeModules have reached powered on state.')
