#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Client for querying the Cray Advanced Platform Monitoring and Control (CAPMC) API
"""
from collections import defaultdict
import logging

from sat.apiclient.gateway import APIError, APIGatewayClient

LOGGER = logging.getLogger(__name__)


class CAPMCError(APIError):
    """An error occurred in CAPMC."""
    def __init__(self, message, xname_errs=None):
        """Create a new CAPMCError with the given message and info about the failing xnames.

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


class CAPMCClient(APIGatewayClient):
    base_resource_path = 'capmc/capmc/v1/'

    def __init__(self, *args, suppress_warnings=False, **kwargs):
        """Initialize the CAPMCClient.

        Args:
            *args: args passed through to APIGatewayClient.__init__
            suppress_warnings (bool): if True, suppress warnings when a query to
                get_xname_status results in an error and node(s) in undefined
                state. As an example, this is useful when waiting for a BMC or
                node controller to be powered on since CAPMC will fail to query
                the power status until it is powered on.
            **kwargs: keyword args passed through to APIGatewayClient.__init__
        """
        self.suppress_warnings = suppress_warnings
        super().__init__(*args, **kwargs)

    def set_xnames_power_state(self, xnames, power_state, force=False, recursive=False, prereq=False):
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
            CAPMCError: if the attempt to power on/off the given xnames with CAPMC
                fails. This exception contains more specific information about
                the failure, which will be included in its __str__.
        """
        if power_state == 'on':
            path = 'xname_on'
        elif power_state == 'off':
            path = 'xname_off'
        else:
            raise ValueError(f'Invalid power state {power_state} given. Must be "on" or "off".')

        params = {'xnames': xnames, 'force': force, 'recursive': recursive, 'prereq': prereq}

        try:
            response = self.post(path, json=params).json()
        except APIError as err:
            raise CAPMCError(f'Failed to power {power_state} xname(s): {", ".join(xnames)}') from err
        except ValueError as err:
            raise CAPMCError(f'Failed to parse JSON in response from CAPMC API when powering '
                             f'{power_state} xname(s): {", ".join(xnames)}') from err

        if response.get('e'):
            raise CAPMCError(f'Power {power_state} operation failed for xname(s).',
                             xname_errs=response.get('xnames'))

    def get_xnames_power_state(self, xnames):
        """Get the power state of the given xnames from CAPMC.

        Args:
            xnames (list): the xnames (str) to get power state for.

        Returns:
            dict: a dictionary whose keys are the power states and whose values
                are lists of xnames in those power states.

        Raises:
            CAPMCError: if the request to get power state fails.
        """
        try:
            response = self.post('get_xname_status', json={'xnames': xnames}).json()
        except APIError as err:
            raise CAPMCError(f'Failed to get power state of xname(s): {", ".join(xnames)}') from err
        except ValueError as err:
            raise CAPMCError(f'Failed to parse JSON in response from CAPMC API '
                             f'when getting power state of xname(s): {", ".join(xnames)}') from err

        if response.get('e'):
            level = logging.DEBUG if self.suppress_warnings else logging.WARNING
            LOGGER.log(level,
                       'Failed to get power state of one or more xnames, e=%s, '
                       'err_msg="%s". xnames with undefined power state: %s',
                       response['e'], response.get("err_msg"), ", ".join(response.get('undefined', [])))

        # Take out the err code and err_msg if everything went well
        return {k: v for k, v in response.items() if k not in {'e', 'err_msg'}}

    def get_xname_power_state(self, xname):
        """Get the power state of a single xname from CAPMC.

        Args:
            xname (str): the xname to get power state of

        Returns:
            str: the power state of the node

        Raises:
            CAPMCError: if the request to CAPMC fails or the expected information
                is not returned by the CAPMC API.
        """
        xnames_by_power_state = self.get_xnames_power_state([xname])
        matching_states = [state for state, xnames in xnames_by_power_state.items()
                           if xname in xnames]
        if not matching_states:
            raise CAPMCError(f'Unable to determine power state of {xname}. Not '
                             f'present in response from CAPMC: {xnames_by_power_state}')
        elif len(matching_states) > 1:
            raise CAPMCError(f'Unable to determine power state of {xname}. CAPMC '
                             f'reported multiple power states: {", ".join(matching_states)}')
        else:
            return matching_states[0]
