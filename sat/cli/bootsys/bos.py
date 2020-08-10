"""
Bootsys operations that use the Boot Orchestration Service (BOS).

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
from collections import defaultdict
import logging
from random import choices, randint
import shlex
import subprocess
from threading import Event, Thread
from time import sleep, time

from inflect import engine

from sat.apiclient import APIError, BOSClient, HSMClient
from sat.cli.bootsys.defaults import (
    CLE_BOS_TEMPLATE_REGEX,
    BOS_BOOT_TIMEOUT,
    BOS_SHUTDOWN_TIMEOUT,
    PARALLEL_CHECK_INTERVAL
)
from sat.config import get_config_value
from sat.session import SATSession
from sat.util import get_val_by_path, pester_choices

LOGGER = logging.getLogger(__name__)

SHUTDOWN_OPERATION = 'shutdown'
BOOT_OPERATION = 'boot'
SUPPORTED_BOS_OPERATIONS = (SHUTDOWN_OPERATION, BOOT_OPERATION)
INFLECTOR = engine()


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

    return not any(fatal_err_msg in line
                   for line in logs_proc.stdout.splitlines())


class BOSSessionThread(Thread):

    def __init__(self, session_template, operation, full_results_dict):
        """Create a new BOSSessionThread that creates and monitors a BOS session

        Args:
            session_template (str): the name of the session template to use to
                create the session.
            operation (str): the operation to use when creating the session from the
                session template.
            full_results_dict (dict): the dictionary where this thread should
                periodically post its results. This thread should *only* write
                its results as the value of the `session_template` key.
        """
        super().__init__()
        self._stop_event = Event()
        self.session_template = session_template
        self.operation = operation
        self.session_id = None
        self.boa_job_id = None
        self.results_dict = {
            'complete': False,
            'failed': False,
            'fail_msg': '',
            'session_id': None,
            'boa_job_id': None
        }
        full_results_dict[session_template] = self.results_dict
        self.bos_client = BOSClient(SATSession())

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
        self.results_dict['complete'] = True
        self.results_dict['failed'] = True
        self.results_dict['fail_msg'] = fail_msg

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
        the state and failure message in `self.results_dict`.

        Returns:
            None
        """
        try:
            response = self.bos_client.create_session(self.session_template,
                                                      self.operation).json()
        except (APIError, ValueError) as err:
            self.mark_failed('Failed to create BOS session: {}'.format(str(err)))
            return

        msg_template = ("Unable to get BOS session ID and BOA job ID from "
                        "response to session creation {}")
        try:
            link = response['links'][0]
        except KeyError:
            self.mark_failed(msg_template.format("due to missing 'links' key."))
        except IndexError:
            self.mark_failed(msg_template.format("due to empty 'links' array."))
        else:
            try:
                self.results_dict['session_id'] = self.session_id = link['href']
                self.results_dict['boa_job_id'] = self.boa_job_id = link['jobId']
            except KeyError as err:
                self.mark_failed(msg_template.format(
                    "due to missing '{}' key.".format(err)))

    def monitor_status_kubectl(self):
        """Monitor the status of the BOS session using a 'kubectl wait' command.

        Since the BOS status endpoint is broken and not yet available on many
        internal systems, use 'kubectl wait' on the BOA job ID to find out when
        the BOS session has completed, and use inspection of the job's logs with
        'kubectl logs' to determine if it was successful or not.

        Once the BOA job is completed, this method returns, and results are
        stored in self.results_dict to be examined by the coordinating thread.

        Returns:
            None
        """
        # Return code is 0 when condition is met, non-zero if timeout
        wait_cmd = shlex.split(
            'kubectl wait -n services --for=condition=complete '
            '--timeout=0 job/{}'.format(self.boa_job_id)
        )

        while not self.results_dict['complete'] and not self.stopped():
            sleep(self.check_interval)

            LOGGER.debug("Waiting for BOA k8s job with job ID %s to complete.",
                         self.boa_job_id)
            try:
                wait_proc = subprocess.run(wait_cmd, stdout=subprocess.PIPE,
                                           stderr=subprocess.PIPE, encoding='utf-8')
            except OSError as err:
                LOGGER.warning("Failed to run 'kubectl wait' command: %s", err)
                self.record_stat_failure()
                continue

            # This is either a timeout or some other failure
            if wait_proc.returncode != 0:
                if 'timed out waiting' not in wait_proc.stderr:
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
                self.results_dict['complete'] = True
            else:
                self.mark_failed(
                    'BOS session with id {} and session template {} '
                    'failed.'.format(self.session_id, self.session_template)
                )

    def monitor_status(self):
        """Monitor the status of the BOS session using a BOS status endpoint.

        This periodically issues a request to the session/{session_id}/status
        endpoint of the BOS API and checks the response to determine if the
        BOS session is complete and successful or failed.

        Once the BOS session is reported to be complete, this method returns,
        and results are stored in self.results_dict to be examined by the
        coordinating thread.

        Returns:
            None
        """
        while not self.results_dict['complete'] and not self.stopped():
            sleep(self.check_interval)

            LOGGER.debug("Querying status of BOS session with ID '%s'",
                         self.session_id)
            try:
                session_status = self.bos_client.get('session', self.session_id,
                                                     'status')
                # Reset because we had a successful query.
                self.consec_stat_fails = 0
            except APIError as err:
                LOGGER.warning('Failed to query session status: %s', err)
                self.record_stat_failure()
                continue

            # TODO: Currently broken by CASMCMS-5532
            complete = get_val_by_path(session_status, 'metadata.complete')
            error_count = get_val_by_path(session_status, 'metadata.error_count')

            if complete is None or error_count is None:
                LOGGER.warning("Session status missing key 'metadata.complete' "
                               "or 'metadata.error_count'.")
                self.record_stat_failure()
                continue

            if complete:
                if error_count == 0:
                    self.results_dict['complete'] = True
                else:
                    self.mark_failed(
                        'BOS session with id {} and session template {} failed '
                        'with error_count={}.'.format(
                            self.session_id, self.session_template, error_count)
                    )

    def create_session_fake(self):
        """Fake the creation of a new BOS session.

        This is helpful for demos of this functionality without actually kicking
        off a BOS session.
        """
        fake_session_id = ''.join(choices('abcdef0123456789', k=36))
        LOGGER.debug("Creating a fake BOS session from session template '%s' "
                     " with fake id %s.", self.session_template,
                     fake_session_id)
        self.results_dict['session_id'] = self.session_id = fake_session_id

    def monitor_status_fake(self):
        """Fake the monitoring of a BOS session.

        This is helpful for demos of this functionality without actually kicking
        off a BOS session.
        """
        rand_duration = randint(60, 120)
        sleep(rand_duration)
        self.results_dict['complete'] = True

    def run(self):
        """Run this thread's action.

        This thread will create a new BOS session against the given session
        template with the given operation, and then it will monitor the status
        of that session and periodically update the value stored under the key
        `self.session_template` in `self.results_dict`.
        """
        self.create_session()

        # TODO: Use monitor_status instead of monitor_status_kubectl when
        # CASMCMS-5532 is fixed
        # self.monitor_status()

        # Workaround that uses 'kubectl wait', 'kubectl get', and 'kubectl logs'
        self.monitor_status_kubectl()


def do_parallel_bos_operations(session_templates, operation):
    """Perform BOS operation against the session templates in parallel.

    Args:
        session_templates (list): A list of BOS session template names to use
            to create BOS sessions with the given `operation`.
        operation (str): The operation to perform on the given BOS session
            templates. Can be either 'shutdown' or 'boot'.

    Returns:
        None

    Raises:
        BOSFailure: if the given operation fails.
    """
    bos_session_threads = []
    results = {}
    template_plural = INFLECTOR.plural('session template', len(session_templates))
    session_plural = INFLECTOR.plural('session', len(session_templates))

    LOGGER.debug('Doing parallel %s with %s: %s', operation, template_plural,
                 ', '.join(session_templates))

    for session_template in session_templates:
        bos_session_threads.append(
            BOSSessionThread(session_template, operation, results)
        )

    start_time = time()
    elapsed_time = 0
    for thread in bos_session_threads:
        thread.start()

    print(f'Started {operation} operation on BOS '
          f'{template_plural}: {", ".join(session_templates)}.')
    bos_timeout = BOS_SHUTDOWN_TIMEOUT if operation == 'shutdown' else BOS_BOOT_TIMEOUT
    print(f'Waiting up to {bos_timeout} seconds for {session_plural} to complete.')

    active_session_templates = list(results.keys())
    failed_session_templates = []
    just_finished = []

    while active_session_templates and elapsed_time < bos_timeout:
        if just_finished:
            print(f'Still waiting on {session_plural} for {template_plural}: '
                  f'{", ".join(active_session_templates)}')
        just_finished = []

        for session_template in active_session_templates:
            session_results = results[session_template]

            if session_results['failed']:
                LOGGER.error(
                    "Operation '%s' failed on BOS session template '%s': %s",
                    operation, session_template, session_results['fail_msg']
                )
                failed_session_templates.append(session_template)
                just_finished.append(session_template)
            elif session_results['complete']:
                print(f'{operation.title()} with BOS session template '
                      f'{session_template} completed.')
                just_finished.append(session_template)

        for finished in just_finished:
            active_session_templates.remove(finished)

        sleep(PARALLEL_CHECK_INTERVAL)
        elapsed_time = time() - start_time

    if active_session_templates:
        LOGGER.error('BOS %s timed out after %s seconds for session %s: %s.',
                     operation, bos_timeout,
                     INFLECTOR.plural('template', len(active_session_templates)),
                     ', '.join(active_session_templates))

        failed_session_templates.extend(active_session_templates)

        for thread in bos_session_threads:
            thread.stop()

    for thread in bos_session_threads:
        thread.join()

    if failed_session_templates:
        raise BOSFailure(
            f'{operation.title()} failed or timed out for session '
            f'{INFLECTOR.plural("template", len(failed_session_templates))}: '
            f'{", ".join(failed_session_templates)}'
        )

    print('All BOS sessions completed.')


def get_template_nodes_by_state(session_template_data):
    """Get a mapping from states to node IDs for nodes in a session template.

    Args:
        session_template_data (dict): The session template data returned by BOS.

    Returns:
        A dictionary whose keys are the states of nodes and whose values are
        lists of xname strings representing the nodes in that state.

    Raises:
        BOSFailure: if data is missing from the `session_template`.
        HSMFailure: if unable to get state of nodes included in the boot sets of
            the BOS session template.
    """
    # The HSM query parameters corresponding to each possible boot set field
    hsm_params_by_bs_field = {
        'node_list': 'id',
        'node_roles_groups': 'role',
        'node_groups': 'group'
    }

    hsm_client = HSMClient(SATSession())

    st_name = session_template_data.get('name')

    try:
        boot_sets = session_template_data['boot_sets']
    except KeyError as err:
        raise BOSFailure("Session template '{}' is missing '{}' "
                         "key.".format(st_name, err))

    nodes_by_state = defaultdict(list)
    for bs_name, bs_data in boot_sets.items():
        for bs_field, hsm_param in hsm_params_by_bs_field.items():

            try:
                bs_field_data = bs_data[bs_field]
            except KeyError:
                # Boot sets may only have one of the keys specifying nodes
                continue

            msg_prefix = (
                "Failed to get state of nodes with {}={} for boot set '{}' of "
                "session template '{}'".format(hsm_param, bs_field_data,
                                               bs_name, st_name)
            )

            # Probably unlikely in practice to have one of the boot set fields
            # set to an empty list. If it does happen though, we would get back
            # all nodes from HSM, so skip these here instead.
            if not bs_field_data:
                LOGGER.info("BOS session template '%s' has '%s' set to "
                            "an empty list.", st_name, bs_field)
                continue

            try:
                hsm_resp_json = hsm_client.get(
                    'State', 'Components',
                    params={'type': 'Node', hsm_param: bs_field_data}
                ).json()
            except (APIError, ValueError) as err:
                raise HSMFailure('{}: {}'.format(msg_prefix, err))

            try:
                node_states = hsm_resp_json['Components']
            except KeyError as err:
                raise HSMFailure("{} due to missing '{}' key in HSM "
                                 "response.".format(msg_prefix, err))

            for node_state in node_states:
                try:
                    nodes_by_state[node_state['State']].append(node_state['ID'])
                except KeyError as err:
                    raise HSMFailure("{} due to missing '{}' key in node state"
                                     ": {}".format(msg_prefix, err, node_state))

    return dict(nodes_by_state)


def handle_state_check_failure(failed_st, operation, fail_action):
    """Handle a failure to check state for session templates.

    Args:
        failed_st (list): A list of session template names for which we failed
            to query state.
        operation (str): The operation being attempted on the session templates.
        fail_action (str): The action to take if there are any session templates
            for which we failed to query state of the nodes in them.

    Returns:
        A list of failed templates that should still have the operation
        performed on them.

    Raises:
        BOSFailure: if there are failed session templates, and the chosen action
            is to abort.
        ValueError: if called with a `fail_action` other than 'abort', 'skip',
            'prompt', or 'force'.
    """
    if not failed_st:
        return []

    fail_msg = 'Failed to get state of nodes in session {}: {}'.format(
        INFLECTOR.plural('template', len(failed_st)), ', '.join(failed_st)
    )

    if fail_action == 'abort':
        raise BOSFailure('{}. Aborting {} attempt.'.format(fail_msg, operation))
    elif fail_action == 'skip':
        LOGGER.warning('%s. Skipping %s.', fail_msg, operation)
        return []
    elif fail_action == 'prompt':
        prompt = '{}. How would you like to proceed? '.format(fail_msg)
        response = pester_choices(prompt, ('skip', 'abort', 'force')) or 'abort'
        return handle_state_check_failure(failed_st, operation, response)
    elif fail_action == 'force':
        LOGGER.warning('%s. Forcing %s.', fail_msg, operation)
        return failed_st
    else:
        raise ValueError("Unrecognized action '{}' for handling state check "
                         "failure.".format(fail_action))


def get_templates_needing_operation(session_templates, operation):
    """
    Get the session templates that still need the given `operation` performed.

    Args:
        session_templates (list): A list of BOS session template names to check.
        operation (str): Check whether this operation needs to be performed on
            any of the nodes in the boot sets within the session templates.

    Returns:
        A list of the session template names which still need the action to be
        performed.

    Raises:
        ValueError: if the provided `operation` is invalid, i.e. not one of the
            values 'shutdown' or 'boot'.
        BOSFailure: if BOS fails to return information about any of the
            session templates or HSM fails to give us information about the
            states of nodes in the BOS session template boot sets.
    """
    # Get the state nodes should be in after the operation is performed
    if operation == BOOT_OPERATION:
        end_state = 'Ready'
    elif operation == SHUTDOWN_OPERATION:
        end_state = 'Off'
    else:
        raise ValueError("Unknown operation '{}'".format(operation))

    bos_client = BOSClient(SATSession())

    needed_st = []
    failed_st = []
    for session_template in session_templates:
        LOGGER.debug("Checking whether nodes in session template '%s' need "
                     "operation '%s' performed.", session_template, operation)
        try:
            st_data = bos_client.get('sessiontemplate', session_template).json()
        except (APIError, ValueError) as err:
            LOGGER.error("Failed to get info about session template '%s': "
                         "%s", session_template, err)
            failed_st.append(session_template)
            continue

        try:
            nodes_by_state = get_template_nodes_by_state(st_data)
        except (BOSFailure, HSMFailure) as err:
            LOGGER.error("Failed to get state of nodes in session template "
                         "'%s': %s", session_template, err)
            failed_st.append(session_template)
            continue

        if list(nodes_by_state.keys()) != [end_state]:
            needed_st.append(session_template)

    # Let BOSFailure raise
    needed_st.extend(handle_state_check_failure(
        failed_st, operation,
        get_config_value('bootsys.state_check_fail_action')
    ))

    return needed_st


def find_cle_bos_template():
    """Find the CLE BOS session template for booting/shutting down computes.

    Returns:
        The name of the CLE BOS session template.

    Raises:
        BOSFailure: if there was a failure to get the CLE session template due
            to a failure within BOS or inability to find a session template
            matching the CLE regex.
    """
    matching_templates = []

    LOGGER.debug('Querying BOS to find CLE session template.')
    bos_client = BOSClient(SATSession())
    try:
        session_templates = bos_client.get('sessiontemplate').json()
    except (APIError, ValueError) as err:
        raise BOSFailure('Failed to get list of BOS session templates to '
                         'determine CLE session template: {}'.format(err))

    for session_template in session_templates:
        try:
            name = session_template['name']
        except KeyError as err:
            LOGGER.warning("Encountered BOS session template with no '%s' key. "
                           "Skipping.", err)
            continue

        LOGGER.debug("Checking BOS session template with name '%s' against "
                     "regex '%s'.", name, CLE_BOS_TEMPLATE_REGEX.pattern)

        if CLE_BOS_TEMPLATE_REGEX.match(name):
            LOGGER.debug("Found matching BOS session template with name '%s'.",
                         name)
            matching_templates.append(name)

    if not matching_templates:
        raise BOSFailure("Unable to find CLE BOS session template matching "
                         "regex '{}'.".format(CLE_BOS_TEMPLATE_REGEX.pattern))
    elif len(matching_templates) > 1:
        raise BOSFailure("Found multiple potential CLE BOS session templates "
                         "based on match against regex '{}': {}. Use the "
                         "'--cle-bos-template' option to specify the one to "
                         "use.".format(CLE_BOS_TEMPLATE_REGEX.pattern,
                                       ', '.join(matching_templates)))

    return matching_templates[0]


def get_session_templates():
    """Get the list of names of session templates on which we should operate.

    This is based on the config file options, which can be overridden by
    command-line options. If the empty string is specified for the UAN template,
    that template will be omitted. In addition, if the templates are the same,
    the returned list will not repeat the name of that session template.

    Returns:
        A list of session template names on which the operation should be
        performed.

    Raises:
        BOSFailure: if failure to get find a CLE BOS template
    """
    cle_bos_template = get_config_value('bootsys.cle_bos_template')
    if not cle_bos_template:
        # Let any exceptions raise to caller
        cle_bos_template = find_cle_bos_template()

    # Default handled by `get_config_value`
    uan_bos_template = get_config_value('bootsys.uan_bos_template')

    if cle_bos_template == uan_bos_template:
        # It is expected that computes and UANs use different session templates,
        # but if they are the same, don't do the operation twice against it.
        LOGGER.info('The cle_bos_template and uan_bos_template are the same '
                    '(%s), so only one session will be created.', cle_bos_template)
        session_templates = [cle_bos_template]
    # Not all systems may have UANs
    elif uan_bos_template == '':
        LOGGER.info('Skipping operation on UANs since the empty string was '
                    'specified for the uan_bos_template.')
        session_templates = [cle_bos_template]
    else:
        session_templates = [cle_bos_template, uan_bos_template]

    return session_templates


def do_bos_operations(operation):
    """Perform a BOS operation on the compute node and UAN session templates.

    Args:
        operation (str): The operation to perform on the compute node and UAN
            session templates. Valid operations are 'boot' and 'shutdown'.

    Returns:
        None

    Raises:
        BOSFailure: if there was a failure in getting BOS session templates or
            in performing the operations, or if there was a failure querying HSM
            for the current state of nodes in the BOS session templates, and the
            failure action is 'abort'.
        ValueError: if given an invalid value for `operation`.
    """
    if operation not in SUPPORTED_BOS_OPERATIONS:
        raise ValueError(f"Invalid operation '{operation}' given. Valid "
                         f"operations: {', '.join(SUPPORTED_BOS_OPERATIONS)}")

    session_templates = get_session_templates()
    # TODO (SAT-509): Validate computes and UANs in session templates

    LOGGER.debug(f"Checking whether session "
                 f"{INFLECTOR.plural('template', len(session_templates))} "
                 f"still need the '{operation}' operation performed: "
                 f"{', '.join(session_templates)}")

    # This will raise a BOSFailure if node status check fails, and the action
    # specified on the command-line or in the config file is 'abort'.
    templates_to_use = get_templates_needing_operation(session_templates, operation)
    LOGGER.debug(f"Found {INFLECTOR.no('session template', len(templates_to_use))} "
                 f"needing '{operation} performed"
                 f"{': ' + ', '.join(templates_to_use) if templates_to_use else '.'}")

    if templates_to_use:
        # Let any exceptions raise to caller
        do_parallel_bos_operations(templates_to_use, operation)
