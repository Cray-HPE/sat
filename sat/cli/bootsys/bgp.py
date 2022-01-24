"""
Resets BGP peering sessions and waits for them to be established.

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
import re
import sys

from sat.waiting import Waiter
from sat.config import get_config_value
from sat.util import BeginEndLogger

LOGGER = logging.getLogger(__name__)


class BGPSpineStatusWaiter(Waiter):
    """Waits for the BGP peers to become established."""

    def condition_name(self):
        return "Spine BGP routes established"

    @staticmethod
    def all_established(stdout):
        """Very simple check to ensure all peers are established.

        This parses the peer states using a basic regular expression
        which matches the state/peer pairs, and then checks if they
        are all "ESTABLISHED".

        Args:
            stdout (str): The stdout of the BGP status commands executed
                across all spine switches.

        Returns:
            True if it is believed that all peers have been established,
                or False otherwise.
        """
        status_pair_re = r'(ESTABLISHED|ACTIVE|OPENSENT|OPENCONFIRM|IDLE)/[0-9]+'
        return stdout and all(status == 'ESTABLISHED' for status in
                              re.findall(status_pair_re, stdout))

    @staticmethod
    def get_spine_status():
        """Simple helper function to get spine BGP status.

        Raises:
            NotImplementedError: this method is not currently implemented.
        """
        # TODO: Once new automation exists for obtaining spine status, call it here
        raise NotImplementedError('Retrieval of spine BGP status not implemented.')

    def pre_wait_action(self):
        # Do one quick check for establishment prior to waiting, and
        # reset the BGP routes if need be.
        spine_bgp_status = BGPSpineStatusWaiter.get_spine_status()
        self.completed = BGPSpineStatusWaiter.all_established(spine_bgp_status)
        if not self.completed:
            LOGGER.info('Screen scrape indicated BGP peers are idle. Resetting.')
            # TODO: Add something here to reset BGP peering sessions

    def has_completed(self):
        spine_status_output = BGPSpineStatusWaiter.get_spine_status()
        if spine_status_output is None:
            LOGGER.error('Failed to get BGP status.')
            return False
        return BGPSpineStatusWaiter.all_established(spine_status_output)


def do_bgp_check(args):
    """Check whether BGP peering sessions are established, resetting if necessary.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    LOGGER.info('Checking for BGP peering sessions established and re-establishing if necessary.')
    with BeginEndLogger('Wait for BGP peering sessions established'):
        bgp_waiter = BGPSpineStatusWaiter(get_config_value('bootsys.bgp_timeout'))
        if not bgp_waiter.wait_for_completion():
            sys.exit(1)
        else:
            LOGGER.info('All BGP peering sessions established.')
