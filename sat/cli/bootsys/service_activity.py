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
Various checks on system services to ensure idleness before shutdown.
"""
from abc import ABC, abstractmethod
from collections import OrderedDict
import logging
import socket
import sys
import warnings

from inflect import engine
from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException
from kubernetes.config import load_kube_config
from kubernetes.config.config_exception import ConfigException
from paramiko.ssh_exception import SSHException
from yaml import YAMLLoadWarning

from sat.apiclient import (
    APIError,
    CFSClient,
    CRUSClient,
    NMDClient
)
from sat.apiclient.bos import BOSClientCommon
from sat.cli.bootsys.util import get_mgmt_ncn_groups, get_ssh_client
from sat.config import get_config_value
from sat.constants import MISSING_VALUE
from sat.apiclient import FASClient
from sat.report import Report
from sat.session import SATSession
from sat.util import get_new_ordered_dict, get_val_by_path


LOGGER = logging.getLogger(__name__)
INFLECTOR = engine()


class ServiceCheckError(Exception):
    """Indicates that we could not get status about the sessions for a service."""
    pass


class ActivityChecker(ABC):
    """An abstract base class for checking arbitrary activities."""
    def __init__(self):
        """Create a new ActivityChecker."""
        # The name of the service
        self.service_name = ''
        # The singular noun describing the sessions
        self.session_name = 'session'
        self.status_command_args = ''

    def get_err(self, msg):
        """Return a ServiceCheckError with a an error message.

        Args:
            msg (str): the message string to pass to the ServiceCheckError
                constructor.

        Returns:
            A ServiceCheckError with a consistently formatted message that
                includes the name of the sessions.
        """
        return ServiceCheckError(
            "Unable to get {}: {}".format(self.active_sessions_desc, msg)
        )

    @property
    def report_title(self):
        """str: The title for a report describing active sessions."""
        # This a title-cased version of the active_sessions_desc property below.
        # title() of that property is wrong because it converts the service name
        # to have an uppercase letter followed by lowercase, e.g. FAS -> Fas.
        return 'Active {} {}'.format(self.service_name.upper(),
                                     INFLECTOR.plural(self.session_name).title())

    @property
    def active_sessions_desc(self):
        """str: The description to use when referring to active sessions."""
        return 'active {} {}'.format(self.service_name.upper(),
                                     INFLECTOR.plural(self.session_name))

    @property
    def more_details(self):
        """str: A string describing how to get further details about running activities."""
        if self.status_command_args:
            return "For more details, execute '{}'.".format(self.status_command_args)
        return ""

    @abstractmethod
    def get_active_sessions(self):
        """Get the active sessions (or equivalent) from the service.

        Individual sessions are encoded as OrderedDicts, the keys of which
        correspond to table headings with values corresponding to row values in
        the table. The returned OrderedDicts are printed to stdout as a
        prettytable.

        Returns:
            A list of OrderedDicts representing the active sessions.

        Raises:
            ServiceCheckError: if unable to get the sessions.
        """
        return []


# noinspection PyAbstractClass
class ServiceActivityChecker(ActivityChecker):
    """An abstract base class for checking service activity.

    This class should be used for checking services accessible from the cray
    cli.
    """

    def __init__(self):
        """Create a new ServiceActivityChecker."""
        super().__init__()
        # cray CLI args to get more information about a specific session
        self.cray_cli_args = ''
        # The field name that identifies a session
        self.id_field_name = ''

    @property
    def cray_cli_command(self):
        """str: The cray CLI command to get more info about a session."""
        return 'cray {} {}'.format(self.cray_cli_args,
                                   self.id_field_name.upper())

    @property
    def more_details(self):
        return "For more details, execute '{}'.".format(self.cray_cli_command)


class SDUActivityChecker(ActivityChecker):
    """A class that checks for SDU being used to actively dump system state."""
    def __init__(self):
        """Create a new SDUActivityChecker."""
        super().__init__()
        self.service_name = 'SDU'
        self.session_name = 'session'

        self.ssh_client = get_ssh_client()
        mgmt_ncns, _ = get_mgmt_ncn_groups()
        self.remote_manager_ncns = mgmt_ncns['managers']

        self.active_sdu_sessions = []

    def get_active_sessions(self):
        """Get any active SDU sessions.

        Returns:
            A list of OrderedDicts representing the active SDU sessions.

        Raises:
            ServiceCheckError: if unable to get the active SDU sessions.
        """
        self.active_sdu_sessions = []

        for ncn in self.remote_manager_ncns:
            try:
                self.ssh_client.connect(ncn)
                command = 'sdu bash pgrep sdu'
                LOGGER.debug("Running command %s on NCN \"%s\"", command, ncn)
                channel = self.ssh_client.get_transport().open_session()
                channel.exec_command(command)

                self.interpret_return_value(ncn, channel.recv_exit_status(), channel.makefile_stderr().read())
            except (SSHException, socket.error) as err:
                raise self.get_err(f'Unable to connect to management NCN "{ncn}": {str(err)}')
            finally:
                self.ssh_client.close()

        return self.active_sdu_sessions

    def interpret_return_value(self, ncn, retval, stderr):
        """Helper function to perform actions based on SDU status.

        If the return code of `sdu bash pgrep sdu` is 0, there is an SDU
        session running on the host which executed the command. This session
        will be added to the list of active sessions.

        If the return code is 1, there is no session running. If the return
        code is 125, this signifies that there is an issue connecting to the
        container. If the return code is 127, the command was not found (i.e.
        SDU is not installed on the given host.) For any of these conditions, a
        warning will be printed, but no active session is added.

        If any other return code is given, this is treated as an error. Some
        return codes are known errors, and a proper error message will be
        supplied in those cases.

        Args:
            ncn (str): the hostname of the NCN being checked for an SDU session
            retval (int): the return code of the sdu/pgrep process checking for SDU
                sessions
            stderr (bytes): the raw contents of stderr from the sdu/pgrep process

        Raises:
            ServiceCheckError: if an error occurred while checking for an SDU session.
        """
        if retval == 0:
            LOGGER.debug("Active SDU session found on %s (pgrep returned 0)", ncn)
            self.active_sdu_sessions.append(OrderedDict([('ncn', ncn)]))
        elif retval == 1:
            LOGGER.debug("No SDU session detected on %s (pgrep returned 1)", ncn)
        elif retval == 125:
            LOGGER.warning("The cray-sdu-rda container is not running on %s.", ncn)
        elif retval == 127:
            LOGGER.warning("The `sdu` command was not found on %s.", ncn)
        else:
            stderr_contents = stderr.decode().strip()
            err_details = f'(return code: {retval}, stderr: "{stderr_contents}")'
            errmsg = {
                2:   f"Syntax error on pgrep commandline on {ncn}. {stderr_contents}",
                3:   f"Fatal error running pgrep on {ncn}. {stderr_contents}",
            }.get(retval, f"An unknown error occurred while checking {ncn}. {err_details}")

            raise self.get_err(errmsg)


class BOSV1ActivityChecker(ServiceActivityChecker):
    """A class that checks for active BOS sessions when BOS v1 is in use."""

    def __init__(self):
        """Create a new BOSActivityChecker."""
        super().__init__()

        self.service_name = 'BOS'
        self.session_name = 'session'
        self.cray_cli_args = 'bos v1 session describe'
        self.id_field_name = 'session_id'

    def get_active_sessions(self):
        """Get any active BOS sessions.

        Returns:
            A list of OrderedDicts representing the active BOS sessions.

        Raises:
            ServiceCheckError: if unable to get the active BOS sessions.
        """
        bos_client = BOSClientCommon.get_bos_client(SATSession(), version='v1')

        active_sessions = []
        bos_session_fields = ['bos_launch', 'operation', 'stage',
                              'session_template_id']
        try:
            session_ids = bos_client.get('session').json()
        except (APIError, ValueError) as err:
            raise self.get_err(str(err))

        # BOS is not currently very helpful in its status reporting. There is no way
        # to tell whether a BOS session is in progress, failed, or done just by
        # doing a GET on the session ID. This is being improved in CASM-1348, but
        # for now, we have to look at BOA pod status.
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            raise self.get_err(
                'Failed to load kubernetes config to get BOA pod status: '
                '{}'.format(err)
            )
        k8s_client = CoreV1Api()

        for session_id in session_ids:
            session_info = {}
            try:
                session_info = bos_client.get('session', session_id).json()
            except (APIError, ValueError) as err:
                # This is not really fatal, but reduces the info we can provide
                LOGGER.warning('Unable to get details about BOS session %s: %s',
                               session_id, err)

            label_selector = 'job-name=boa-{}'.format(session_id)
            try:
                pods = k8s_client.list_namespaced_pod(
                    'services',
                    label_selector=label_selector
                ).items
            except ApiException as err:
                raise self.get_err(
                    'Unable to get BOA pod status for BOS session {}'
                    ': {}'.format(session_id, err)
                )

            for pod in pods:
                # Per k8s API docs, there are 5 possible phases: Pending,
                # Running, Succeeded, Failed, and Unknown.
                if pod.status.phase in ('Pending', 'Running'):
                    session_info[self.id_field_name] = session_id
                    active_sessions.append(
                        get_new_ordered_dict(
                            session_info,
                            [self.id_field_name] + bos_session_fields,
                            MISSING_VALUE
                        )
                    )
                    # Avoid adding the same session twice in case multiple pods
                    # for the BOS session are in Pending/Running phase
                    break

        return active_sessions


class BOSV2ActivityChecker(ServiceActivityChecker):
    """A class that checks for active BOS sessions when BOS v2 is in use."""

    def __init__(self):
        super().__init__()
        self.service_name = 'BOS'
        self.session_name = 'session'
        self.cray_cli_args = 'bos v2 sessions describe'
        self.id_field_name = 'name'

    def get_active_sessions(self):
        """Get any active BOS sessions.

        Returns:
            A list of OrderedDicts representing the active BOS sessions.

        Raises:
            ServiceCheckError: if unable to get the active BOS sessions.
        """
        # In BOS v2, BOA no longer exists, but we can query session status
        # information.
        bos_v2_paths = [
            'name',
            'operation',
            'status.status',
            'template_name',
        ]
        bos_client = BOSClientCommon.get_bos_client(SATSession(), version='v2')

        try:
            return [
                get_new_ordered_dict(session, bos_v2_paths, MISSING_VALUE)
                for session in bos_client.get_sessions()
                if get_val_by_path(session, 'status.status') != 'complete'
            ]
        except APIError as err:
            LOGGER.warning('Could not query BOS for sessions: %s', err)
            raise self.get_err(str(err)) from err


class CFSActivityChecker(ServiceActivityChecker):
    """A class that checks for active CFS sessions."""

    def __init__(self):
        """Create a new CFSActivityChecker."""
        super().__init__()
        self.service_name = 'CFS'
        self.session_name = 'session'
        self.cray_cli_args = 'cfs sessions describe'
        # Despite each CFS session having an 'id', the field we want here is
        # 'name' which is what the admin can use to query information about it.
        self.id_field_name = 'name'

    def get_active_sessions(self):
        """Get any active Configuration Framework Service (CFS) sessions.

        Returns:
            A list of dictionaries representing the active CFS sessions.

        Raises:
            ServiceCheckError: if unable to get the active CFS sessions.
        """
        cfs_client = CFSClient(SATSession())
        try:
            sessions = cfs_client.get('sessions').json()
        except (APIError, ValueError) as err:
            raise self.get_err(str(err))

        cfs_session_fields = [
            self.id_field_name,
            'status.session.status',
            'status.session.startTime',
            'status.session.succeeded',
            'status.session.job'
        ]

        return [
            get_new_ordered_dict(session, cfs_session_fields, MISSING_VALUE)
            for session in sessions
            # Possible values are 'pending', 'running', or 'complete'
            if get_val_by_path(session, 'status.session.status') != 'complete'
        ]


class CRUSActivityChecker(ServiceActivityChecker):
    """A class that checks for active CRUS sessions."""

    def __init__(self):
        """Create a new CRUSActivityChecker."""
        super().__init__()
        self.service_name = 'CRUS'
        self.session_name = 'upgrade'
        self.cray_cli_args = 'crus session describe'
        self.id_field_name = 'upgrade_id'

    def get_active_sessions(self):
        """Get any active Compute Rolling Upgrade Service (CRUS) upgrades.

        Returns:
            A list of dictionaries representing the active CRUS upgrades.

        Raises:
            ServiceCheckError: if unable to get the active CRUS upgrades.
        """
        crus_client = CRUSClient(SATSession())
        try:
            upgrades = crus_client.get('session').json()
        except (APIError, ValueError) as err:
            raise self.get_err(str(err))

        crus_upgrade_fields = [
            self.id_field_name,
            'state',
            'completed',
            'kind',
            'upgrade_template_id'
        ]

        return [
            get_new_ordered_dict(upgrade, crus_upgrade_fields, MISSING_VALUE)
            for upgrade in upgrades if not upgrade.get('completed')
        ]


class FirmwareActivityChecker(ServiceActivityChecker):
    """A class that checks for active FAS sessions."""

    def __init__(self):
        """Create a new FirmwareActivityChecker"""
        super().__init__()
        self.fw_client = FASClient(SATSession())

        self.service_name = 'FAS'
        self.session_name = 'action'
        self.cray_cli_args = 'firmware actions describe'
        self.id_field_name = 'actionID'

    def get_active_sessions(self):
        """Check for active firmware updates in FAS.

        Returns:
            A list of dicts representing the active firmware upgrades/actions.

        Raises:
            ServiceCheckError: if unable to get the active firmware updates or
                actions.
        """
        try:
            active_updates = self.fw_client.get_active_actions()
        except APIError as err:
            raise self.get_err(str(err))

        fw_session_fields = [self.id_field_name, 'startTime', 'state',
                             'snapshotID', 'dryrun']

        return [
            get_new_ordered_dict(update, fw_session_fields, MISSING_VALUE)
            for update in active_updates
        ]


class NMDActivityChecker(ServiceActivityChecker):
    """A class that checks for active NMD sessions."""

    def __init__(self):
        """Create a new NMDActivityChecker."""
        super().__init__()
        self.service_name = 'NMD'
        self.session_name = 'dump'
        self.cray_cli_args = 'nmd dumps describe'
        self.id_field_name = 'requestID'

    def get_active_sessions(self):
        """Get any active Node Memory Dump (NMD) dumps.

        Returns:
            A list of dicts representing the active NMD dumps.

        Raises:
            ServiceCheckError: if unable to get the active NMD dumps.
        """
        nmd_client = NMDClient(SATSession())
        try:
            dumps = nmd_client.get('dumps').json()
        except (APIError, ValueError) as err:
            raise self.get_err(str(err))

        nmd_dump_fields = [self.id_field_name, 'info.state', 'info.xname',
                           'info.created']

        return [
            get_new_ordered_dict(dump, nmd_dump_fields, MISSING_VALUE)
            for dump in dumps
            # Possible values for 'state': waiting, dump, done, error, cancel
            if dump.get('info', {}).get('state') in ('waiting', 'dump')
        ]


def _report_active_sessions(service_activity_checkers):
    """Reports on the active sessions of various services on the system.

    Prints information about active sessions of the various services.

    Args:
        service_activity_checkers: A list of ServiceActivityChecker objects to
            be queried for service activity.

    Returns:
        A tuple of:
            active_services (list): A list of the names of the active services.
            failed_services (list): A list of the names of the failed services.
    """
    active_services = []
    failed_services = []

    for checker in service_activity_checkers:
        LOGGER.info('Checking for {}.'.format(checker.active_sessions_desc))
        try:
            sessions = checker.get_active_sessions()
        except ServiceCheckError as err:
            LOGGER.error(str(err))
            failed_services.append(checker.service_name)
            continue

        # get_active_sessions should return a list of dicts with common keys
        try:
            headings = list(sessions[0].keys())
        except IndexError:
            # no active sessions, so continue
            LOGGER.info("Found no {}.".format(checker.active_sessions_desc))
            continue

        active_services.append(checker.service_name)

        log_msg = "Found {} {}. Details shown below.".format(
            len(sessions),
            INFLECTOR.singular_noun(checker.active_sessions_desc,
                                    count=len(sessions))
        )
        if checker.more_details:
            log_msg += " " + checker.more_details

        LOGGER.info(log_msg)
        report = Report(headings, title=checker.report_title)
        report.add_rows(sessions)
        print(report)

    return active_services, failed_services


def do_service_activity_check(args):
    """Check for service activity and exit if services are active.

    Prints information about any active services and any errors encountered and
    exits the program if there are active services preventing shutdown.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootsys subcommand.

    Returns:
        None.

    Raises:
        SystemExit: if there are active services preventing a system shutdown
            or there was a failure to query one or more services for active
            sessions.
    """
    bos_checker_cls = \
        BOSV1ActivityChecker if get_config_value('bos.api_version') == 'v1' \
        else BOSV2ActivityChecker

    service_activity_checkers = [
        bos_checker_cls(),
        CFSActivityChecker(),
        CRUSActivityChecker(),
        FirmwareActivityChecker(),
        NMDActivityChecker(),
        SDUActivityChecker()
    ]

    active, failed = _report_active_sessions(service_activity_checkers)

    if failed:
        LOGGER.error(f'Failed to get active sessions for the following '
                     f'{INFLECTOR.plural("service", len(failed))}: '
                     f'{", ".join(failed)}')

    if active:
        print(f'Active sessions exist for the following '
              f'{INFLECTOR.plural("service", len(active))}: '
              f'{", ".join(active)}. Allow the sessions to complete or '
              f'cancel them before proceeding.')
        sys.exit(1)
    elif failed:
        print('No active sessions found in the services which could be '
              'successfully queried. Review the errors above before '
              'proceeding with the shutdown procedure.')
        sys.exit(1)
    else:
        print('No active sessions exist. It is safe to proceed with the '
              'shutdown procedure.')
