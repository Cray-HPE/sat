import logging
import sys
from collections import namedtuple

import inflect

from sat.apiclient import FabricControllerClient
from sat.cached_property import cached_property
from sat.cli.bootsys.state_recorder import HSNStateRecorder, StateError
from sat.cli.bootsys.util import run_ansible_playbook
from sat.cli.bootsys.waiting import GroupWaiter
from sat.session import SATSession
from sat.util import BeginEndLogger

LOGGER = logging.getLogger(__name__)
INF = inflect.engine()


# A representation of a port in a port set.
HSNPort = namedtuple('HSNPort', ('port_set', 'port_xname'))


class HSNBringupWaiter(GroupWaiter):
    """Run the HSN bringup script and wait for it to be brought up."""

    def __init__(self, timeout, poll_interval=1):
        """Create a new HSNBringupWaiter."""
        super().__init__(set(), timeout, poll_interval)
        self.fabric_client = FabricControllerClient(SATSession())
        self.hsn_state_recorder = HSNStateRecorder()
        # dict mapping from port set name to dict mapping from port xname to enabled status
        self.current_hsn_state = {}

    def condition_name(self):
        return "HSN bringup"

    def pre_wait_action(self):
        run_ansible_playbook('/opt/cray/crayctl/ansible_framework/main/ncmp_hsn_bringup.yaml',
                             exit_on_err=False)

        # Populate members with known members from fabric controller API
        self.members = {HSNPort(port_set, port_xname)
                        for port_set, port_xnames in self.fabric_client.get_fabric_edge_ports().items()
                        for port_xname in port_xnames}

    def on_check_action(self):
        """Get the latest HSN state from the fabric controller API."""
        self.current_hsn_state = self.fabric_client.get_fabric_edge_ports_enabled_status()

    @cached_property
    def stored_hsn_state(self):
        """dict: HSN state from the file where it was saved prior to shutdown

        Will be a dict mapping from the port set names ('fabric-ports', 'edge-ports')
        to a dict mapping from port xnames (str) to port enabled status (bool). Will
        be the empty dict if there is a failure to load the saved state.
        """
        try:
            return self.hsn_state_recorder.get_stored_state()
        except StateError as err:
            LOGGER.warning(f'Failed to get HSN state from prior to shutdown; '
                           f'will wait for all links to come up: {err}')
            return {}

    def member_has_completed(self, member):
        """Get whether the given member has completed.

        Args:
            member (HSNPort): the port to check for completion.

        Returns:
            True if the port status is enabled or if the port was disabled
            before the shutdown. False otherwise.
        """
        try:
            expected_state = self.stored_hsn_state[member.port_set][member.port_xname]
        except KeyError:
            # If the port was not known before shutdown, assume it should be enabled.
            # E.g., this could happen if a switch or cable was added while the system
            # was shut down.
            expected_state = True

        try:
            current_state = self.current_hsn_state[member.port_set][member.port_xname]
        except KeyError:
            # If no state is reported for this port, then it is not healthy
            return False

        # if expected state is true, then current state must be true
        return current_state or not expected_state


def do_hsn_bringup(args):
    """Bring up HSN and wait for it to be healthy.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    hsn_waiter = HSNBringupWaiter(args.hsn_timeout)
    with BeginEndLogger('bring up HSN and wait for healthy'):
        hsn_waiter.wait_for_completion()

    num_pending = len(hsn_waiter.pending)
    if hsn_waiter.pending:
        LOGGER.error(f'The following HSN {INF.plural("port", num_pending)} '
                     f'{INF.plural_verb("is", num_pending)} not enabled: '
                     f'{", ".join(port.port_xname for port in hsn_waiter.pending)}')
        sys.exit(1)
