"""
Support for powering off NCNs with IPMI and computes/UANs with CAPMC.

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
import shlex
import subprocess

from inflect import engine

from sat.apiclient import APIError, CAPMCClient, CAPMCError, HSMClient
from sat.session import SATSession
from sat.cli.bootsys.waiting import GroupWaiter

LOGGER = logging.getLogger(__name__)


class IPMIPowerStateWaiter(GroupWaiter):
    """Implementation of a waiter for IPMI power states.

    Waits for all members to reach the given IPMI power state."""

    def __init__(self, members, power_state, timeout, username, password,
                 send_command=False, poll_interval=1):
        """Constructor for an IPMIPowerStateWaiter object.

        Args:
            power_state (str): either 'on' or 'off', corresponds the desired
                IPMI power state.
            send_command (bool): if True, send a 'power on' or 'power off' command
                to each node before waiting.
            username (str): the username to use when running ipmitool commands
            password (str): the password to use when running ipmitool commands
        """
        self.power_state = power_state
        self.username = username
        self.password = password
        self.send_command = send_command

        super().__init__(members, timeout, poll_interval=poll_interval)

    def condition_name(self):
        return 'IPMI power ' + self.power_state

    def get_ipmi_command(self, member, command):
        """Get the full command-line for an ipmitool command.

        Args:
            member (str): the host to query
            command (str): the ipmitool command to run, e.g. `chassis power status`

        Returns:
            The command to run, split into a list of args by shlex.split.
        """
        return shlex.split(
            'ipmitool -I lanplus -U {} -P {} -H {}-mgmt {}'.format(
                self.username, self.password, member, command
            )
        )

    def member_has_completed(self, member):
        """Check if a host is in the desired state.

        Return:
            If the powerstate of the host matches that which was given
            in the constructor, return True. Otherwise, return False.
        """
        ipmi_command = self.get_ipmi_command(member, 'chassis power status')
        try:
            proc = subprocess.run(ipmi_command, stdout=subprocess.PIPE,
                                  stderr=subprocess.PIPE, encoding='utf-8')
        except OSError as err:
            # TODO (SAT-552): Improve handling of ipmitool errors
            LOGGER.error('Unable to find ipmitool: %s', err)
            return False

        if proc.returncode:
            # TODO (SAT-552): Improve handling of ipmitool errors
            LOGGER.error('ipmitool command failed with code %s: stderr: %s',
                         proc.returncode, proc.stderr)
            return False

        return self.power_state in proc.stdout

    def pre_wait_action(self):
        """Send IPMI power commands to given hosts.

        This will issue IPMI power commands to put the given hosts in the power
        state given by `self.power_state`.

        Returns:
            None
        """
        LOGGER.debug("Entered pre_wait_action with self.send_command: %s.", self.send_command)
        if self.send_command:
            for member in self.members:
                LOGGER.info('Sending IPMI power %s command to host %s', self.power_state, member)
                ipmi_command = self.get_ipmi_command(member,
                                                     'chassis power {}'.format(self.power_state))
                try:
                    proc = subprocess.run(ipmi_command, stdout=subprocess.PIPE,
                                          stderr=subprocess.PIPE, encoding='utf-8')
                except OSError as err:
                    # TODO (SAT-552): Improve handling of ipmitool errors
                    LOGGER.error('Unable to find ipmitool: %s', err)
                    return

                if proc.returncode:
                    # TODO (SAT-552): Improve handling of ipmitool errors
                    LOGGER.error('ipmitool command failed with code %s: stderr: %s',
                                 proc.returncode, proc.stderr)
                    return


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

    role_nodes = hsm_client.get_component_xnames('Node', role)
    LOGGER.debug('Found %s node(s) with role %s: %s', len(role_nodes), role, role_nodes)
    if not role_nodes:
        return role_nodes

    nodes_by_power_state = capmc_client.get_xnames_power_state(role_nodes)
    power_state_nodes = nodes_by_power_state.get(power_state, [])
    LOGGER.debug('Found %s node(s) with power state %s: %s', len(power_state_nodes),
                 power_state, power_state_nodes)

    matching_nodes = [node for node in role_nodes if node in power_state_nodes]
    LOGGER.debug('Found %s node(s) with role %s and power state %s: %s',
                 len(matching_nodes), role, power_state, matching_nodes)

    return matching_nodes


class CAPMCPowerWaiter(GroupWaiter):
    """Waits for all members to reach the given power state in CAPMC."""

    def __init__(self, members, power_state, timeout, poll_interval=5):
        """Create a new CAPMCPowerStateWaiter.

        Args:
            members (list or set): the xnames to wait for.
            power_state (str): the power state to wait for the members to reach
            timeout (int): how long to wait for nodes to reach given power state
                before timing out.
            poll_interval (int): how long to wait between checks on power state
        """
        super().__init__(members, timeout, poll_interval)
        self.power_state = power_state
        self.capmc_client = CAPMCClient(SATSession())

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
            LOGGER.warning("Failed to query power state: %s", err)
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

    print(f'Forcing power off of {num_on_nodes} compute or application '
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
    print(f'Waiting {timeout} seconds until {num_wait_nodes} {inf.plural("node", num_wait_nodes)} '
          f'reach powered off state according to CAPMC.')

    waiter = CAPMCPowerWaiter(wait_nodes, 'off', timeout)
    timed_out_nodes = waiter.wait_for_completion()
    return timed_out_nodes, failed_nodes
