#
# MIT License
#
# (C) Copyright 2021-2024 Hewlett Packard Enterprise Development LP
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
"""
Basic client library for PCS.
"""
from collections import defaultdict

from csm_api_client.service.gateway import APIError, APIGatewayClient
from csm_api_client.service.hsm import HSMClient
from sat.xname import XName


class PCSError(APIError):
    """An error occurred in PCS."""

    def __init__(self, message, xname_errs=None):
        """Create a new PCSError with the given message and info about the failing xnames.

        Args:
            message (str): the error message
            xname_errs (list): a list of dictionaries representing the failures for
                the individual components that failed. Each dict should have the
                following keys:
                    e: the error code
                    err_msg: the error message
                    xname: the actual xname which failed
        """
        self.message = message
        self.xname_errs = xname_errs if xname_errs is not None else []
        self.xnames = [xname_err['xname'] for xname_err in self.xname_errs
                       if 'xname' in xname_err]

    def __str__(self):
        """Convert to str."""
        if not self.xname_errs:
            return self.message
        else:
            # A mapping from a tuple of (err_code, err_msg) to a list of xnames
            # with that combination of err_code and err_msg.
            xnames_by_err = defaultdict(list)
            for xname_err in self.xname_errs:
                xnames_by_err[(xname_err.get('e'), xname_err.get('err_msg'))].append(xname_err.get('xname'))

            xname_err_summary = '\n'.join([f'xname(s) ({", ".join(xnames)}) failed with '
                                           f'e={err_info[0]} and err_msg="{err_info[1]}"'
                                           for err_info, xnames in xnames_by_err.items()])

            return f'{self.message}\n{xname_err_summary}'


class PCSClient(APIGatewayClient):
    """Client for the Power Control Service."""
    base_resource_path = 'power-control/v1/'

    def set_xnames_power_state(self, xnames, power_state, force=False, recursive=False):
        """Set the power state of the given xnames.

        Args:
            xnames (list): the xnames (str) to perform the power operation
                against.
            power_state (str): the desired power state. Either "on" or "off".
            force (bool): if True, disable checks and force the power operation.
            recursive (bool): if True, power on component and its descendants.
            prereq (bool): if True, power on component and its ancestors.

        Returns:
            None

        Raises:
            ValueError: if the given `power_state` is not one of 'on' or 'off'
            PCSError: if the attempt to power on/off the given xnames with PCS
                fails. This exception contains more specific information about
                the failure, which will be included in its __str__.
        """
        allowed_states = {'on', 'off', 'soft-off', 'soft-restart', 'hard-restart', 'init', 'force-off'}
        power_state = power_state.lower()
        if power_state not in allowed_states:
            allowed_states_str = ", ".join("\"" + state + "\"" for state in allowed_states)
            raise ValueError(f'Invalid power state {power_state} given. Must be {allowed_states_str}')

        if force:
            if power_state in {'off', 'soft-off'}:
                power_state = 'force-off'
            elif power_state == 'soft-restart':
                power_state = 'hard-restart'

        target_xnames = set(xnames)
        if recursive:
            hsm_client = HSMClient(self.session)

            try:
                for xname in xnames:
                    xname_instance = XName(xname)
                    if xname_instance.get_type() == 'Chassis':
                        target_xnames.update(
                            hsm_client.query_components(
                                xname,
                                type=['chassis', 'computemodule', 'node', 'routermodule']
                            )
                        )
                    elif xname_instance.get_type() == 'ComputeModule':
                        target_xnames.update(hsm_client.query_components(xname, type=['computemodule', 'node']))
            except APIError as err:
                raise PCSError(f'Could not retrieve descendant components for xnames: {err}') from err

        params = {
            'operation': power_state,
            'taskDeadlineMinutes': -1,
            'location': [
                {'xname': xname}
                for xname in target_xnames
            ]
        }
        try:
            self.post('transitions', json=params).json()
        except APIError as err:
            raise PCSError(f'Power {power_state} operation failed for xname(s).',
                           xname_errs=xnames) from err

    def get_xnames_power_state(self, xnames):
        """Get the power state of the given xnames from PCS.

        Args:
            xnames (list): the xnames (str) to get power state for.

        Returns:
            dict: a dictionary whose keys are the power states and whose values
                are lists of xnames in those power states.

        Raises:
            PCSError: if the request to get power state fails.
        """
        xnames = set(xnames)
        try:
            resp = self.get('power-status', params={'xname': xnames}).json().get('status')
            nodes_by_power_state = defaultdict(list)
            for node in resp:
                nodes_by_power_state[node['powerState']].append(node['xname'])
            return nodes_by_power_state
        except APIError as err:
            raise PCSError(f'Failed to get power state of xname(s): {", ".join(xnames)}') from err

    def get_xname_power_state(self, xname):
        """Get the power state of a single xname from PCS.

        Args:
            xname (str): the xname to get power state of

        Returns:
            str: the power state of the node

        Raises:
            PCSError: if the request to PCS fails or the expected information
                is not returned by the PCS API.
        """
        try:
            resp = self.get('power-status', params={'xname': xname}).json().get('status')
        except APIError as err:
            raise PCSError(f'Failed to get power state for xname {xname}: {err}') from err

        matching_states = [node['powerState'] for node in resp
                           if node['xname'] == xname]
        if not matching_states:
            raise PCSError(f'Unable to determine power state of {xname}. Not '
                           f'present in response from PCS: {resp}')
        elif len(matching_states) > 1:
            raise PCSError(f'Unable to determine power state of {xname}. PCS '
                           f'reported multiple power states: {", ".join(matching_states)}')
        return matching_states.pop()
