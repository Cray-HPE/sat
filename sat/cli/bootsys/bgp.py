"""
Resets BPG peering sessions and waits for them to be established.

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
import re
import sys

from sat.cli.bootsys.util import run_ansible_playbook
from sat.cli.bootsys.waiting import Waiter
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
            stdout (str): The stdout of the 'spine-bgp-status.yml'
                ansible playbook

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

        Runs run_ansible_playbook() with the spine-bgp-status.yml playbook.

        Args: None.
        Returns: The stdout resulting when running the spine-bgp-status.yml
            playbook or None if it fails.
        """
        return run_ansible_playbook('/opt/cray/crayctl/ansible_framework/main/spine-bgp-status.yml',
                                    exit_on_err=False)

    def pre_wait_action(self):
        # Do one quick check for establishment prior to waiting, and
        # reset the BGP routes if need be.
        spine_bgp_status = BGPSpineStatusWaiter.get_spine_status()
        self.completed = BGPSpineStatusWaiter.all_established(spine_bgp_status)
        if not self.completed:
            LOGGER.info('Screen scrape indicated BGP peers are idle. Resetting.')
            run_ansible_playbook('/opt/cray/crayctl/ansible_framework/main/metallb-bgp-reset.yml',
                                 exit_on_err=False)

    def has_completed(self):
        spine_status_output = BGPSpineStatusWaiter.get_spine_status()
        if spine_status_output is None:
            LOGGER.error('Failed to run spine-bgp-status.yml playbook.')
            return False
        return BGPSpineStatusWaiter.all_established(spine_status_output)


def do_bgp_check(args):
    """Run BGP playbooks and wait for BGP peering sessions to be established.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    with BeginEndLogger('Wait for BGP peering sessions established'):
        bgp_waiter = BGPSpineStatusWaiter(get_config_value('bootsys.bgp_timeout'))
        if not bgp_waiter.wait_for_completion():
            sys.exit(1)
