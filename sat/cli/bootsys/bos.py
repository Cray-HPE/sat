#
# MIT License
#
# (C) Copyright 2020-2024 Hewlett Packard Enterprise Development LP
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
Bootsys operations that use the Boot Orchestration Service (BOS).
"""
import logging
import math
import posixpath
import shlex
import subprocess
import sys
from argparse import Namespace
from collections import defaultdict
from random import choices, randint
from textwrap import dedent, indent
from threading import Event, Thread
from time import monotonic, sleep

from inflect import engine

from sat.apiclient import APIError, HSMClient
from sat.apiclient.bos import BOSClientCommon
from sat.cli.bootsys.defaults import PARALLEL_CHECK_INTERVAL
from sat.config import get_config_value
from sat.session import SATSession
from sat.util import pester, prompt_continue
from sat.waiting import Waiter, WaitingFailure
from sat.xname import XName

LOGGER = logging.getLogger(__name__)

SHUTDOWN_OPERATION = 'shutdown'
BOOT_OPERATION = 'boot'
REBOOT_OPERATION = 'reboot'
SUPPORTED_BOS_OPERATIONS = (
    SHUTDOWN_OPERATION, BOOT_OPERATION, REBOOT_OPERATION)
INFLECTOR = engine()


class BOSLimitString:
    """A simple class to encapsulate a BOS limit string."""

    def __init__(self, xnames, roles_groups):
        """Constructor for BOSLimitString

        Args:
            xnames (Iterable[str]): node xnames to include in limit string
            roles_groups (Iterable[str]): names of roles and groups to include
                in limit string
        """
        self.xnames = set(xnames)
        self.roles_groups = set(roles_groups)

    @classmethod
    def from_string(cls, limit, *, recursive):
        """Construct a BOSLimitString from a raw limit string.

        The rationale of the `recursive` argument to this function is that BOS
        limit strings must include specific node xnames, and will not work
        recursively -- giving a slot's xname, for instance, will result in a
        silent no-op. If a user wishes to power off a single blade, however, it
        is much simpler to use this recursive expander function instead of
        specifying each node individually.

        Args:
            limit (str): a comma-separated list of xnames, roles, and groups which
                can be passed to BOS in its limit parameter in the POST payload.
            recursive (bool): if True, replace all non-node xnames in the limit
                string with all node xnames under that xname. If False, leave all
                xnames verbatim.

        Returns:
            BOSLimitString: a BOSLimitString representing the given limit string

        Raises:
            BOSFailure: if a non-node xname is supplied when recursive is False, or
                a given xname is recursively expanded and no nodes are found
                under it, or there is a problem querying HSM to recursively
                expand an xname.
        """
        hsm_client = HSMClient(SATSession())
        xnames = set()
        roles_groups = set()

        for limit_str in limit.split(','):
            limit_xname = XName(limit_str)
            if not limit_xname.is_valid:
                roles_groups.add(limit_str)
                continue

            if limit_xname.get_type() == 'NODE':
                xnames.add(limit_str)
            else:
                if not recursive:
                    raise BOSFailure(f'xname {str(limit_xname)} refers to a component of type '
                                     f'{limit_xname.get_type().lower()}, not a node. Limits for non-recursive '
                                     f'BOS operations require node xnames.')

                try:
                    limit_node_xnames = hsm_client.get_node_components(ancestor=limit_str)
                except APIError as err:
                    raise BOSFailure(f'Could not retrieve node xnames from HSM: {err}') from err

                if not limit_node_xnames:
                    raise BOSFailure(f'Recursively expanding xname {limit_str} failed; '
                                     f'no node xnames were found.')

                for node_component in limit_node_xnames:
                    xnames.add(node_component['ID'])

        return cls(xnames, roles_groups)

    def __str__(self):
        return ','.join(self.xnames | self.roles_groups)


class BOSFailure(Exception):
    """An error occurred while using BOS to operate on computes and UANs."""
    pass


class HSMFailure(Exception):
    """An error occurred while using HSM to get information about node state."""
    pass


def boa_job_successful(boa_job_id):
    """Get whether the given BOA job was successful.

    Args:
        boa_job_id (str): The BOA job ID

    Returns:
        True if the given BOA job was successful, False otherwise.

    Raises:
        BOSFailure: if unable to determine success or failure of BOA job.
    """
    msg_prefix = ('Unable to determine success or failure of BOA job with ID '
                  '{}'.format(boa_job_id))

    get_pod_cmd = shlex.split(
        'kubectl -n services get pod --sort-by=.metadata.creationTimestamp '
        '--no-headers --selector job-name={}'.format(boa_job_id)
    )
    try:
        pods_proc = subprocess.run(get_pod_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, check=True,
                                   encoding='utf-8')
    except (subprocess.CalledProcessError, OSError) as err:
        raise BOSFailure('{}; failed to find pods: {}'.format(msg_prefix,
                                                              err))

    try:
        last_pod = pods_proc.stdout.splitlines()[-1].split()[0]
    except IndexError:
        raise BOSFailure('{}; no pods with job-name={}'.format(msg_prefix,
                                                               boa_job_id))

    LOGGER.info('Determining success of BOA job with ID %s by checking logs from pod %s', boa_job_id, last_pod)
    logs_cmd = shlex.split('kubectl -n services logs -c boa '
                           '{}'.format(last_pod))

    fatal_err_msg = ('Fatal conditions have been detected with this run of '
                     'Boot Orchestration that are not expected to be '
                     'recoverable through additional iterations.')

    try:
        logs_proc = subprocess.run(logs_cmd, stdout=subprocess.PIPE,
                                   stderr=subprocess.PIPE, check=True,
                                   encoding='utf-8')
    except (subprocess.CalledProcessError, OSError) as err:
        raise BOSFailure('{}; failed to get logs of pod {}: {}'.format(
            msg_prefix, last_pod, err))

    success = not any(fatal_err_msg in line
                      for line in logs_proc.stdout.splitlines())

    if not success:
        num_lines_to_log = 50
        lines_to_log = indent('\n'.join(logs_proc.stdout.splitlines()[-num_lines_to_log:]), prefix='  ')
        LOGGER.error(
            'BOA job %s was not successful. Last %s log lines from pod %s:\n%s',
            boa_job_id, num_lines_to_log, last_pod, lines_to_log
        )
        LOGGER.error('To see full logs, run: \'kubectl -n services logs -c boa %s\'', last_pod)

    return success


class BOSV2SessionWaiter(Waiter):
    """Waiter for monitoring the status of a BOS v2 session."""

    def __init__(self, bos_session_thread, target_states=None, *args, **kwargs):
        """
        Create a new BOSV2SessionWaiter.

        Args:
            bos_session_thread (BOSSessionThread): the BOS session thread
            target_states (list, optional): the list of acceptable target state
                strings. Defaults to ['complete']
        """
        super().__init__(*args, **kwargs)
        self.bos_client = BOSClientCommon.get_bos_client(SATSession(),
                                                         version='v2')
        self.bos_session_thread = bos_session_thread
        self.target_states = ['complete'] if target_states is None else target_states
        self.target_states_desc = INFLECTOR.join(self.target_states, conj='or')

        self.pct_successful = 0.0
        self.pct_failed = 0.0
        self.session_status = {}

    def condition_name(self):
        return f'session {self.bos_session_thread.session_id} reached target state {self.target_states_desc}'

    def has_completed(self):
        if self.bos_session_thread.stopped():
            return True

        try:
            LOGGER.info(
                'Waiting for BOS session %s to reach target state %s. Session template: %s',
                self.bos_session_thread.session_id, self.target_states_desc,
                self.bos_session_thread.session_template
            )

            response = self.bos_client.get(self.bos_client.session_path, self.bos_session_thread.session_id, 'status',
                                           raise_not_ok=False)

            if not response.ok:
                if response.status_code == 404:
                    raise WaitingFailure(
                        f'Failed to query session status: Session {self.bos_session_thread.session_id} does not exist.')
                else:
                    LOGGER.warning(
                        f'Failed to query status of BOS session {self.bos_session_thread.session_id}: '
                        f'{response.status_code} {response.reason}.')
                    return False

            try:
                self.session_status = response.json()
            except ValueError as err:
                LOGGER.warning(f'Failed to parse session status JSON: {err}')

            if (self.session_status['percent_successful'] != self.pct_successful
                    or self.session_status['percent_failed'] != self.pct_failed):
                # Only log progress update when components succeed or fail
                self.pct_successful = float(self.session_status['percent_successful'])
                self.pct_failed = float(self.session_status['percent_failed'])
                if 99 < self.pct_successful < 100:
                    LOGGER.info(
                        'Session %s: %.6f%% components succeeded, %.2f%% components failed',
                        self.bos_session_thread.session_id, self.pct_successful, self.pct_failed
                    )
                else:
                    LOGGER.info(
                        'Session %s: %.2f%% components succeeded, %.2f%% components failed',
                        self.bos_session_thread.session_id, self.pct_successful, self.pct_failed
                    )

            if self.session_status['status'] in self.target_states:
                if not self.session_status.get('managed_components_count'):
                    LOGGER.info(
                        'Session %s did not manage any components.',
                        self.bos_session_thread.session_id
                    )
                return True

            return False

        except KeyError as err:
            LOGGER.warning('BOS session status query response missing key %s', err)

        return False

    def post_wait_action(self):
        error_summary = self.session_status.get('error_summary')
        if error_summary:
            for err, summary in error_summary.items():
                LOGGER.error('%s: %s', err, summary)


class BOSSessionThread(Thread):

    def __init__(self, session_template, operation, limit=None, stage=False):
        """Create a new BOSSessionThread that creates and monitors a BOS session

        Args:
            session_template (str): the name of the session template to use to
                create the session.
            operation (str): the operation to use when creating the session from the
                session template.
            limit (str): a limit string to pass through to BOS as the `limit`
                parameter in the POST payload when creating the BOS session
            stage (bool): if True, create a 'staged' BOS session, which updates
                components' staged state rather than their desired state.
        """
        super().__init__()
        self._stop_event = Event()
        self.session_template = session_template
        self.limit = limit
        self.stage = stage
        self.operation = operation
        self.session_id = None
        self.boa_job_id = None
        self.complete = False
        self.failed = False
        self.fail_msg = ''
        self.bos_client = BOSClientCommon.get_bos_client(SATSession())
        self.bos_session_status = None

        # Keep track of how many times we fail to query status in a row.
        self.consec_stat_fails = 0
        # If we exceed this many consecutive failures, stop trying.
        self.max_consec_fails = 3
        # How long to wait in seconds between each session status check
        self.check_interval = PARALLEL_CHECK_INTERVAL

    def stop(self):
        """Stop the execution of this thread at the next opportunity."""
        self._stop_event.set()

    def stopped(self):
        """Return whether a stop of this thread was requested."""
        return self._stop_event.is_set()

    def mark_failed(self, fail_msg):
        """Mark this BOS Session as failed with a message.

        Args:
            fail_msg (str): the message to indicate what failed.

        Returns:
            None
        """
        self.complete = True
        self.failed = True
        self.fail_msg = fail_msg

    def record_stat_failure(self):
        """Record a status check failure, and set failed if max consecutive
        failures is exceeded.

        Returns:
            None
        """
        self.consec_stat_fails += 1
        if self.consec_stat_fails > self.max_consec_fails:
            self.mark_failed('Aborting because session status query failed {} '
                             'times in a row.'.format(self.consec_stat_fails))

    def create_session(self):
        """Create a BOS session with self.session_template and self.operation.

        If a fatal error occurs, the mark_failed method is called to update
        the complete, failed, and fail_msg attributes.

        Returns:
            None
        """
        bos_client_kwargs = {
            'session_template': self.session_template,
            'operation': self.operation,
            'limit': self.limit,
        }
        if self.stage:
            bos_client_kwargs['stage'] = self.stage
        try:
            response = self.bos_client.create_session(**bos_client_kwargs).json()
        except (APIError, ValueError) as err:
            self.mark_failed('Failed to create BOS session: {}'.format(str(err)))
            return

        msg_prefix = 'Unable to get BOS session ID '
        if get_config_value('bos.api_version') == 'v2':
            msg_prefix += 'from response to session creation'
            try:
                self.session_id = response['name']
            except KeyError as err:
                self.mark_failed(f'{msg_prefix} due to missing "{err}" key '
                                 'in BOS response')
        else:
            msg_prefix += 'and/or BOA job ID from response to session creation'
            try:
                link = response['links'][0]
            except KeyError:
                self.mark_failed(f"{msg_prefix} due to missing 'links' key.")
            except IndexError:
                self.mark_failed(f"{msg_prefix} due to empty 'links' array.")
            else:
                missing_keys = []
                try:
                    self.session_id = posixpath.basename(link['href'])
                except KeyError as err:
                    missing_keys.append(str(err))
                try:
                    self.boa_job_id = link['jobId']
                except KeyError as err:
                    missing_keys.append(str(err))
                if missing_keys:
                    self.mark_failed(f'{msg_prefix} due to missing key(s) in BOS '
                                     f'response: {", ".join(missing_keys)}')

    def monitor_status_kubectl(self):
        """Monitor the status of the BOS session using a 'kubectl wait' command.

        Since the BOS status endpoint is broken and not yet available on many
        internal systems, use 'kubectl wait' on the BOA job ID to find out when
        the BOS session has completed, and use inspection of the job's logs with
        'kubectl logs' to determine if it was successful or not.

        Once the BOA job is completed, this method returns, and results are
        stored in the thread attributes to be examined by the coordinating
        thread.

        Returns:
            None
        """
        # Return code is 0 when condition is met, non-zero if timeout
        wait_cmd = shlex.split(
            'kubectl wait -n services --for=condition=complete '
            '--timeout=0 job/{}'.format(self.boa_job_id)
        )

        LOGGER.info(dedent(f'''
            Waiting for BOA k8s job with id {self.boa_job_id} to complete. Session template: {self.session_template}.
            To monitor the progress of this job, run the following command in a separate window:
                'kubectl -n services logs -c boa -f --selector job-name={self.boa_job_id}'\
            '''))

        while not self.complete and not self.stopped():
            sleep(self.check_interval)

            LOGGER.info("Waiting for BOA k8s job with job ID %s to complete. Session template: %s",
                        self.boa_job_id, self.session_template)
            try:
                wait_proc = subprocess.run(wait_cmd, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, encoding='utf-8')
            except OSError as err:
                LOGGER.warning("Failed to run 'kubectl wait' command: %s", err)
                self.record_stat_failure()
                continue

            # Different versions of the k8s CLI say different things to mean "timed out".
            # Scraping the output of the k8s CLI is not ideal and this could be done differently
            # using `kubectl wait` without `timeout=0`. But, that would require a big refactor
            # and this is all going away with BOS v2.
            timed_out_output_messages = [
                'timed out waiting',
                'condition not met'
            ]
            # This is either a timeout or some other failure
            if wait_proc.returncode != 0:
                if not any(msg in wait_proc.stderr for msg in timed_out_output_messages):
                    LOGGER.warning("The 'kubectl wait' command failed instead "
                                   "of timing out. stderr: %s",
                                   wait_proc.stderr.strip())
                    self.record_stat_failure()
                else:
                    self.consec_stat_fails = 0
                continue

            self.consec_stat_fails = 0

            # Check if successful or failed with logs.
            try:
                success = boa_job_successful(self.boa_job_id)
            except BOSFailure as err:
                LOGGER.warning(str(err))
                self.record_stat_failure()
                continue

            if success:
                self.complete = True
            else:
                self.mark_failed(
                    'BOS session with id {} and session template {} '
                    'failed.'.format(self.session_id, self.session_template)
                )

    def monitor_status(self):
        """Monitor the status of the BOS session using a BOS v2 status endpoint.

        This periodically issues a request to the session/{session_id}/status
        endpoint of the BOS v2 API and checks the response to determine if the
        BOS session is complete and successful or failed.

        Once the BOS session is reported to be complete, this method returns,
        and results are stored in the thread attributes to be examined by the
        coordinating thread.

        Returns:
            None
        """
        target_states = ['complete']
        # If staged, a BOS session will enter 'running' state if it affects a
        # non-empty set of components. Otherwise (e.g. when the nodes specified
        # in the bootsets do not intersect with the limit parameter), it will go
        # straight to 'complete'.
        if self.stage:
            target_states.append('running')

        # Pass math.inf as the timeout since timeouts are handled by the
        # `do_parallel_bos_operations()` function, independent of the waiter
        # class here.
        waiter = BOSV2SessionWaiter(self, target_states=target_states,
                                    timeout=math.inf,
                                    poll_interval=PARALLEL_CHECK_INTERVAL)

        waiter.wait_for_completion()
        if waiter.failed:
            self.mark_failed(
                'BOS session with id {} and session template {} '
                'failed.'.format(self.session_id, self.session_template)
            )
        else:
            self.complete = True

        self.bos_session_status = waiter.session_status

    def create_session_fake(self):
        """Fake the creation of a new BOS session.

        This is helpful for demos of this functionality without actually kicking
        off a BOS session.
        """
        fake_session_id = ''.join(choices('abcdef0123456789', k=36))
        LOGGER.debug("Creating a fake BOS session from session template '%s' "
                     " with fake id %s.", self.session_template,
                     fake_session_id)
        self.session_id = fake_session_id

    def monitor_status_fake(self):
        """Fake the monitoring of a BOS session.

        This is helpful for demos of this functionality without actually kicking
        off a BOS session.
        """
        rand_duration = randint(60, 120)
        sleep(rand_duration)
        self.complete = True

    def run(self):
        """Run this thread's action.

        This thread will create a new BOS session against the given session
        template with the given operation, and then it will monitor the status
        of that session and periodically update the complete, failed, and
        fail_msg attributes as appropriate.
        """
        self.create_session()

        # Return without attempting to monitor status if session creation failed
        if self.failed:
            return

        if get_config_value('bos.api_version') == 'v2':
            self.monitor_status()
        else:
            # Use 'kubectl wait', 'kubectl get', and 'kubectl logs' for BOS v1
            # due to initial trouble with status endpoint (CASMCMS-5532).
            self.monitor_status_kubectl()


def do_parallel_bos_operations(session_templates, operation, timeout, limit=None, stage=False):
    """Perform BOS operation against the session templates in parallel.

    Args:
        session_templates (list): A list of BOS session template names to use
            to create BOS sessions with the given `operation`.
        operation (str): The operation to perform on the given BOS session
            templates. Can be either 'shutdown' or 'boot'.
        timeout (int): The timeout for the BOS operation
        limit (str): a string containing a comma-separated list of xnames,
            roles, and groups to operate upon. This string will be passed
            through verbatim to BOS in the POST payload when sessions are
            created.
        stage (bool): if True, create a 'staged' BOS session, which updates
            components' staged state rather than their desired state.

    Returns:
        None

    Raises:
        BOSFailure: if the given operation fails.
    """
    template_plural = INFLECTOR.plural('session template', len(session_templates))
    session_plural = INFLECTOR.plural('session', len(session_templates))

    LOGGER.debug('Doing parallel %s with %s: %s', operation, template_plural,
                 ', '.join(session_templates))

    bos_session_threads = [BOSSessionThread(session_template, operation, limit=limit, stage=stage)
                           for session_template in session_templates]

    starting_verb = 'Staging' if stage else 'Starting'
    LOGGER.info(f'{starting_verb} {operation} operation on BOS '
                f'{template_plural}: {", ".join(session_templates)}.')

    start_time = monotonic()
    elapsed_time = 0
    for thread in bos_session_threads:
        thread.start()

    completed_state = 'stage' if stage else 'complete'
    completed_state_past_tense = 'staged' if stage else 'completed'
    if timeout == -1:
        LOGGER.info(f'Waiting for {session_plural} to {completed_state}.')
    else:
        LOGGER.info(f'Waiting up to {timeout} seconds for {session_plural} to {completed_state}.')

    active_threads = {t.session_template: t for t in bos_session_threads}
    failed_session_templates = []
    just_finished = []

    while active_threads and (timeout == -1 or elapsed_time < timeout):
        if just_finished:
            LOGGER.info(f'Still waiting on session(s) for template(s): '
                        f'{", ".join(active_threads.keys())}')
        just_finished = []

        for session_template, thread in active_threads.items():
            if thread.failed:
                LOGGER.error(
                    "Operation '%s' failed on BOS session template '%s': %s",
                    operation, session_template, thread.fail_msg
                )
                failed_session_templates.append(session_template)
                just_finished.append(session_template)
            elif thread.complete:
                LOGGER.info(f'{operation.title()} with BOS session template '
                            f'{session_template} {completed_state_past_tense}.')
                just_finished.append(session_template)

        for finished in just_finished:
            del active_threads[finished]

        sleep(PARALLEL_CHECK_INTERVAL)
        elapsed_time = monotonic() - start_time

    if active_threads:
        LOGGER.error('BOS %s timed out after %s seconds for session %s: %s.',
                     operation, timeout,
                     INFLECTOR.plural('template', len(active_threads)),
                     ', '.join(active_threads.keys()))

        failed_session_templates.extend(active_threads.keys())

        for thread in active_threads.values():
            thread.stop()

    some_sessions_failed = False
    for thread in bos_session_threads:
        thread.join()

        if thread.bos_session_status:
            LOGGER.info(
                'Session %s: %.2f%% components succeeded, %.2f%% components failed',
                thread.session_id,
                thread.bos_session_status['percent_successful'],
                thread.bos_session_status['percent_failed']
            )
            error_summary = thread.bos_session_status.get('error_summary', {})
            if error_summary:
                some_sessions_failed = True

            for error_message, components in error_summary.items():
                LOGGER.warning(
                    '%s (%d components): %s',
                    error_message,
                    int(components['count']),
                    str(components['list']),
                )

    if failed_session_templates:
        raise BOSFailure(
            f'{operation.title()} failed or timed out for session '
            f'{INFLECTOR.plural("template", len(failed_session_templates))}: '
            f'{", ".join(failed_session_templates)}'
        )

    if some_sessions_failed:
        LOGGER.warning('One or more BOS sessions had errors; see previous logs for details.')
    else:
        LOGGER.info(f'All BOS sessions {completed_state_past_tense}.')


def _update_nodes_by_state(nodes_by_state, hsm_client, hsm_params):
    """Update the nodes_by_state dictionary given an HSM client and query parameters.

    Args:
        nodes_by_state (defaultdict): The nodes_by_state dictionary to modify
            in place.
        hsm_client (HSMClient): The client used to query HSM.
        hsm_params (dict): A dictionary of query parameters to their values.

    Returns:
        None. Modifies nodes_by_state in place.

    Raises:
        HSMFailure: If the query fails or is missing a required field.
    """

    try:
        hsm_resp_json = hsm_client.get(
            'State', 'Components',
            params=hsm_params,
        ).json()
    except (APIError, ValueError) as err:
        raise HSMFailure(err)

    try:
        node_states = hsm_resp_json['Components']
    except KeyError as err:
        raise HSMFailure("Missing '{}' key in HSM response.".format(err))

    for node_state in node_states:
        try:
            nodes_by_state[node_state['State']].append(node_state['ID'])
        except KeyError as err:
            raise HSMFailure("Missing '{}' key in node state: {}".format(err, node_state))


def get_session_templates():
    """Get the list of names of session templates on which we should operate.

    This is based on the bos_templates config file option, which can be
    overridden by the --bos-templates command-line option. This is expected
    to be a list, and this function removes duplicates from the list.

    If this option was not specified, then get_session_templates_deprecated() is
    used to find suitable COS and UAN session templates based on deprecated
    options.

    Returns:
        A list of session template names on which the operation should be
        performed.

    Raises:
        BOSFailure: if no BOS templates were specified (from
            get_session_templates_deprecated)
    """
    bos_templates = get_config_value('bootsys.bos_templates')
    if bos_templates:
        session_templates = list(set(bos_templates))
        LOGGER.info(
            'Using session templates provided by --bos-templates/bos_templates option: %s',
            session_templates
        )
    else:
        session_templates = get_session_templates_deprecated()

    return session_templates


def get_session_templates_deprecated():
    """Get default COS and UAN session templates.

    This function gets default COS and UAN session templates based on the
    deprecated 'cle_bos_template' and 'uan_bos_template' options, or their
    defaults.

    This function always logs a warning that it is preferred for the admin
    to use the `--bos-templates` argument or its configuration file equivalent.

    If the configured COS and UAN templates are the same then just one
    session template is returned. If either template is specified as an empty
    string or unspecified, then it is omitted from the list of session
    templates.

    Returns:
        A list of names of BOS session templates.

    Raises:
        BOSFailure: if no BOS templates were specified.
    """
    cos_bos_template = get_config_value('bootsys.cle_bos_template')
    uan_bos_template = get_config_value('bootsys.uan_bos_template')
    if cos_bos_template and cos_bos_template == uan_bos_template:
        # It is expected that computes and UANs use different session templates,
        # but if they are the same, don't do the operation twice against it.
        LOGGER.info('The COS BOS template and UAN BOS template are the same '
                    '(%s), so only one session will be created.', cos_bos_template)
        session_templates = [cos_bos_template]
    else:
        # If either cos_bos_template or uan_bos_template are unspecified or
        # empty strings, omit them.
        session_templates = [template for template in
                             (cos_bos_template, uan_bos_template) if template]

    if not session_templates:
        raise BOSFailure(
            'No BOS templates were specified. Specify one with --bos-templates.'
        )

    LOGGER.warning(
        'The --bos-templates/bos_templates option was not specified. Please '
        'use this option to specify session templates. Proceeding with session '
        'templates: %s', ','.join(session_templates)
    )
    return session_templates


def do_bos_operations(operation, timeout, limit=None, recursive=False, stage=False):
    """Perform a BOS operation on the compute node and UAN session templates.

    Args:
        operation (str): The operation to perform on the compute node and UAN
            session templates. Valid operations are 'boot' and 'shutdown'.
        timeout (int): The timeout for the BOS operation.
        limit (str): a limit string to pass through to BOS to limit the operation
            to specific xnames.
        recursive (bool): if True, expand non-node xnames in the limit string
            to the set of all nodes contained in the given xname. If False, do not
            expand xnames.
        stage (bool): if True, create a 'staged' BOS session, which updates
            components' staged state rather than their desired state.

    Returns:
        None

    Raises:
        BOSFailure: if there was a failure in getting BOS session templates or
            in performing the operations, or if there was a failure querying HSM
            for the current state of nodes in the BOS session templates, and the
            failure action is 'abort'.
        ValueError: if given an invalid value for `operation`.
    """
    if stage and get_config_value('bos.api_version').lower() == 'v1':
        raise BOSFailure(f'--staged-session option may not be used with BOS v1.')

    if limit is not None:
        bos_limit_str = BOSLimitString.from_string(limit, recursive=recursive)

        # This prompting is inspired by the idea described here:
        # https://rachelbythebay.com/w/2020/10/26/num/
        #
        # Essentially, the idea is that if we're going to end up targeting a bunch
        # of nodes, the user should have an idea of the magnitude of their action.
        # This should help prevent mistakes such as shutting down a whole cabinet
        # instead of a single blade, for instance.
        num_affected_xnames = len(bos_limit_str.xnames)
        if recursive and num_affected_xnames:
            try:
                continue_ok = pester(
                    f'The recursive BOS operation will affect {num_affected_xnames} nodes; '
                    f'enter the number of affected nodes to continue',
                    valid_answer=None,
                    human_readable_valid='enter number to continue, anything else to abort',
                    parse_answer=lambda answer: int(answer) == num_affected_xnames
                )
            except ValueError:
                continue_ok = False

            if not continue_ok:
                LOGGER.info('Did not enter the correct number of nodes; aborting.')
                return

        LOGGER.debug('Using limit string for BOS %s operation: %s',
                     operation, str(bos_limit_str))
        limit = str(bos_limit_str)

    if operation not in SUPPORTED_BOS_OPERATIONS:
        raise ValueError(f"Invalid operation '{operation}' given. Valid "
                         f"operations: {', '.join(SUPPORTED_BOS_OPERATIONS)}")

    session_templates = get_session_templates()
    # TODO (SAT-509): Validate computes and UANs in session templates

    do_parallel_bos_operations(
        session_templates, operation, timeout, limit=limit, stage=stage
    )


def do_bos_shutdowns(args):
    """Shut down compute nodes and UANs using BOS.
    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.

    Returns: None
    """
    if not (args.disruptive or args.staged_session):
        prompt_continue('shutdown of nodes using BOS')

    try:
        do_bos_operations('shutdown', get_config_value('bootsys.bos_shutdown_timeout'),
                          limit=args.bos_limit, recursive=args.recursive, stage=args.staged_session)
    except BOSFailure as err:
        LOGGER.error(err)
        sys.exit(1)


def do_bos_boots(args):
    """Boot compute nodes and UANs using BOS.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.

    Returns: None
    """
    try:
        do_bos_operations('boot', get_config_value('bootsys.bos_boot_timeout'),
                          limit=args.bos_limit, recursive=args.recursive, stage=args.staged_session)
    except BOSFailure as err:
        LOGGER.error(err)
        sys.exit(1)


def do_bos_reboots(args: Namespace):
    """Reboots compute nodes and UANs using BOS.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.

    Returns: None
    """
    if not (args.disruptive or args.staged_session):
        prompt_continue('reboot of nodes using BOS')

    try:
        boot_timeout = get_config_value("bootsys.bos_boot_timeout")
        shutdown_timeout = get_config_value("bootsys.bos_shutdown_timeout")
        total_timeout = boot_timeout + shutdown_timeout
        if total_timeout < -1:
            total_timeout = -1
        do_bos_operations(
            "reboot",
            total_timeout,
            limit=args.bos_limit,
            recursive=args.recursive,
            stage=args.staged_session
        )
    except BOSFailure as err:
        LOGGER.error(err)
        sys.exit(1)
