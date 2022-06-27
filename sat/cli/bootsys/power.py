#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
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
Support for powering off computes/UANs with CAPMC.
"""
import logging

from inflect import engine

from sat.apiclient import APIError, CAPMCClient, CAPMCError, HSMClient
from sat.session import SATSession
from sat.waiting import GroupWaiter

LOGGER = logging.getLogger(__name__)


def get_nodes_by_role_and_state(role, power_state):
    """Get all the nodes matching the given role in HSM and power state in CAPMC.

    Args:
        role (str): the role to search for.
        power_state (str): the power state to search for.

    Returns
        list of str: a list of xnames that match the given `role` and
            `power_state`.

    Raises:
        APIError: if there is a failure to get the needed information from HSM
            or CAPMC.
    """
    hsm_client = HSMClient(SATSession())
    capmc_client = CAPMCClient(SATSession())

    role_nodes = hsm_client.get_component_xnames({'type': 'Node', 'role': role})
    LOGGER.debug('Found %s node(s) with role %s: %s', len(role_nodes), role, role_nodes)
    if not role_nodes:
        return role_nodes

    nodes_by_power_state = capmc_client.get_xnames_power_state(role_nodes)
    matching_nodes = nodes_by_power_state.get(power_state, [])
    LOGGER.debug('Found %s node(s) with role %s and power state %s: %s', len(matching_nodes),
                 role, power_state, matching_nodes)

    return matching_nodes


class CAPMCPowerWaiter(GroupWaiter):
    """Waits for all members to reach the given power state in CAPMC."""

    def __init__(self, members, power_state, timeout, poll_interval=5, suppress_warnings=False):
        """Create a new CAPMCPowerStateWaiter.

        Args:
            members (list or set): the xnames to wait for.
            power_state (str): the power state to wait for the members to reach
            timeout (int): how long to wait for nodes to reach given power state
                before timing out.
            poll_interval (int): how long to wait between checks on power state
            suppress_warnings (bool): if True, suppress warnings when a query to
                get_xname_status results in an error and node(s) in undefined
                state. As an example, this is useful when waiting for a BMC or
                node controller to be powered on since CAPMC will fail to query
                the power status until it is powered on.
        """
        super().__init__(members, timeout, poll_interval)
        self.power_state = power_state
        self.capmc_client = CAPMCClient(SATSession(), suppress_warnings=suppress_warnings)

    def condition_name(self):
        return 'CAPMC power ' + self.power_state

    def member_has_completed(self, member):
        """Return whether the member xname has reached the desired power state.

        Args:
            member (str): the xname to check

        Returns:
            bool: True if the xname has reached the desired power state
                according to CAPMC.
        """
        LOGGER.debug('Checking whether xname %s has reached desired power state %s',
                     member, self.power_state)
        try:
            current_state = self.capmc_client.get_xname_power_state(member)
        except APIError as err:
            # When cabinets are powered off, the query will respond with 400 bad request
            # until components are reachable.
            LOGGER.debug('Failed to query power state: %s', err)
            return False

        return current_state == self.power_state


def do_nodes_power_off(timeout):
    """Ensure the compute and application nodes (UANs) are powered off.

    Args:
        timeout (int): the timeout for waiting for nodes to reach powered off
            state according to CAPMC after turning off their power.

    Returns:
        A tuple of:
            timed_out_nodes: a set of nodes that timed out waiting to reach
                power state 'off' according to capmc.
            failed_nodes: a set of nodes that failed to power off with capmc
    """
    inf = engine()
    on_nodes = set(get_nodes_by_role_and_state('compute', 'on') +
                   get_nodes_by_role_and_state('application', 'on'))
    num_on_nodes = len(on_nodes)

    if not on_nodes:
        # All nodes are already off
        return set(), set()

    LOGGER.info(f'Forcing power off of {num_on_nodes} compute or application '
                f'{inf.plural("node")} still powered on: {", ".join(on_nodes)}')

    wait_nodes = on_nodes
    failed_nodes = set()
    capmc_client = CAPMCClient(SATSession())
    try:
        capmc_client.set_xnames_power_state(list(on_nodes), 'off', force=True)
    except CAPMCError as err:
        LOGGER.warning(err)
        if err.xnames:
            failed_nodes = set(err.xnames)
            # Only wait on the nodes that did not have an error powering off
            wait_nodes = set(on_nodes) - failed_nodes
        else:
            # This probably indicates all nodes failed to be powered off
            return set(), on_nodes

    num_wait_nodes = len(wait_nodes)
    LOGGER.info(f'Waiting {timeout} seconds until {num_wait_nodes} {inf.plural("node", num_wait_nodes)} '
                f'reach powered off state according to CAPMC.')

    waiter = CAPMCPowerWaiter(wait_nodes, 'off', timeout)
    timed_out_nodes = waiter.wait_for_completion()
    return timed_out_nodes, failed_nodes
