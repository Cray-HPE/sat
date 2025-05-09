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
Unit tests for the sat.cli.bootsys.bos module.
"""

import logging
import math
import shlex
import subprocess
import unittest
from argparse import Namespace
from textwrap import indent
from typing import Any
from unittest.mock import MagicMock, Mock, call, patch

from sat.cli.bootsys.bos import (BOSFailure, BOSLimitString, BOSSessionThread,
                                 BOSV2SessionWaiter, boa_job_successful,
                                 do_bos_reboots, do_bos_shutdowns,
                                 get_session_templates)
from tests.common import ExtendedTestCase
from sat.waiting import WaitingFailure


class TestBOAJobSuccessful(ExtendedTestCase):
    """Tests for whether the BOA job is successful."""
    def setUp(self):
        """Create some mocks."""
        self.boa_job_id = 'boa-1234567890abcdef'
        self.boa_pods = ['{}-{}'.format(self.boa_job_id, i) for i in range(4)]
        self.boa_pod_logs = [
            'Starting a BOA job.',
            'Finishing a BOA job.'
        ]
        self.fatal_boa_message = (
            'Fatal conditions have been detected with this run of '
            'Boot Orchestration that are not expected to be '
            'recoverable through additional iterations.'
        )
        self.get_pod_err = None
        self.logs_err = None

        def mock_kubectl_run(cmd, **kwargs):
            """Mock running a kubectl command."""
            retval = Mock()

            # This is a 'kubectl get pod' command
            if 'get' in cmd and 'pod' in cmd:
                if self.get_pod_err:
                    raise self.get_pod_err

                retval.stdout = '\n'.join([
                    '{}   0/2   Completed   0    1h'.format(boa_pod)
                    for boa_pod in self.boa_pods
                ])

            # This is a 'kubectl logs' command
            elif 'logs' in cmd:
                if self.logs_err:
                    raise self.logs_err

                retval.stdout = '\n'.join(self.boa_pod_logs)

            return retval

        self.mock_run = patch('subprocess.run', side_effect=mock_kubectl_run).start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def assert_boa_logs(self, logs):
        """Helper to assert boa pod lines are logged."""
        max_lines_to_log = 50
        expected_log_message = (f'BOA job {self.boa_job_id} was not successful. '
                                f'Last 50 log lines from pod {self.boa_pods[-1]}:\n')
        expected_log_message += indent('\n'.join(self.boa_pod_logs[-max_lines_to_log:]), prefix='  ')
        expected_full_log_help = f'To see full logs, run: \'kubectl -n services logs -c boa {self.boa_pods[-1]}\''
        self.assert_in_element(expected_log_message, logs.output)
        self.assert_in_element(expected_full_log_help, logs.output)

    def test_successful_boa_job(self):
        """Test boa_job_successful on a successful BOA job."""
        self.assertTrue(boa_job_successful(self.boa_job_id))
        common_kwargs = {
            'stdout': subprocess.PIPE,
            'stderr': subprocess.PIPE,
            'check': True,
            'encoding': 'utf-8'
        }
        self.mock_run.assert_has_calls([
            call(shlex.split('kubectl -n services get pod --sort-by=.metadata.creationTimestamp '
                             '--no-headers --selector job-name={}'.format(self.boa_job_id)),
                 **common_kwargs),
            call(shlex.split('kubectl -n services logs -c boa {}'.format(self.boa_pods[-1])),
                 **common_kwargs)
        ])

    def test_successful_boa_job_empty_logs(self):
        """Test boa_job_successful with no boa pod logs."""
        self.boa_pod_logs = []
        self.assertTrue(boa_job_successful(self.boa_job_id))

    def test_no_boa_pods(self):
        """Test boa_job_successful with no matching boa pods."""
        self.boa_pods = []
        with self.assertRaisesRegex(BOSFailure,
                                    'no pods with job-name={}'.format(self.boa_job_id)):
            boa_job_successful(self.boa_job_id)

    def test_failed_boa_job(self):
        """Test boa_job_successful on a failed BOA job."""
        self.boa_pod_logs.append(self.fatal_boa_message)
        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertFalse(boa_job_successful(self.boa_job_id))
            self.assert_boa_logs(logs)

    def test_failed_boa_job_middle_log(self):
        """Test boa_job_successful on a failed BOA job with log in middle."""
        self.boa_pod_logs.insert(1, self.fatal_boa_message)
        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertFalse(boa_job_successful(self.boa_job_id))
            self.assert_boa_logs(logs)

    def test_failed_boa_job_many_log_lines(self):
        """Test boa_job_successful on a failed BOA job only logs num_lines_to_log lines"""
        self.boa_pod_logs = ['Reindexing BOA session templates'] * 100
        self.boa_pod_logs.append(self.fatal_boa_message)
        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertFalse(boa_job_successful(self.boa_job_id))
            self.assert_boa_logs(logs)

    def test_kubectl_get_failure(self):
        """Test boa_job_successful with 'kubectl get pod' failure."""
        errs = [subprocess.CalledProcessError(1, 'cmd'), OSError('no such command')]
        for err in errs:
            with self.subTest(err=err):
                self.get_pod_err = err
                with self.assertRaisesRegex(BOSFailure, 'failed to find pods'):
                    boa_job_successful(self.boa_job_id)

    def test_kubectl_logs_failure(self):
        """Test boa_job_successful with 'kubectl logs' failure."""
        errs = [subprocess.CalledProcessError(1, 'cmd'), OSError('no such command')]
        for err in errs:
            with self.subTest(err=err):
                self.logs_err = err
                with self.assertRaisesRegex(BOSFailure, 'failed to get logs of pod '
                                                        '{}'.format(self.boa_pods[-1])):
                    boa_job_successful(self.boa_job_id)


class TestBOSLimitString(unittest.TestCase):
    """Tests for the BOSLimitString class."""
    def setUp(self):
        self.blade_xname = 'x3000c0s0'
        self.nodes_on_blade_xnames = [f'{self.blade_xname}b0n{node}' for node in range(4)]
        self.mock_hsm_client = patch('sat.cli.bootsys.bos.HSMClient').start()
        self.mock_sat_session = patch('sat.cli.bootsys.bos.SATSession').start()
        self.mock_get_node_components = self.mock_hsm_client.return_value.get_node_components
        self.mock_get_node_components.return_value = [
            {'ID': xname} for xname in self.nodes_on_blade_xnames
        ]

    def tearDown(self):
        patch.stopall()

    def test_constructing_limit_string_manually(self):
        """Test the constructor of the BOSLimitString class"""
        xnames = ['x3000c0s0b0n0']
        roles = ['Application']
        limit_str = BOSLimitString(xnames, roles)

        for xname in xnames:
            self.assertIn(xname, str(limit_str))

        for role in roles:
            self.assertIn(role, str(limit_str))

    def test_expanding_a_limit_string(self):
        """Test constructing a BOSLimitString non-recursively from an existing limit string"""
        limit_str = BOSLimitString.from_string('x3000c0s0b0n0,Application', recursive=False)
        for item in ['x3000c0s0b0n0', 'Application']:
            self.assertIn(item, str(limit_str))

        self.mock_get_node_components.assert_not_called()

    def test_recursive_limit_string_expanding(self):
        """Test expanding a limit string to its constituent xnames"""
        blade_xname = 'x3000c0s0'
        limit_str = BOSLimitString.from_string(f'{blade_xname},Application', recursive=True)
        self.mock_get_node_components.assert_called_once_with(ancestor=blade_xname)
        for xname in self.nodes_on_blade_xnames + ['Application']:
            self.assertIn(xname, str(limit_str))

    def test_expanding_empty_component(self):
        """Test expanding component with no node descendants"""
        blade_xname = 'x3000c0s0'
        self.mock_get_node_components.return_value = []
        with self.assertRaises(BOSFailure):
            BOSLimitString.from_string(blade_xname, recursive=True)
        self.mock_get_node_components.assert_called_once_with(ancestor=blade_xname)

    def test_non_recursive_limit_string_with_non_node_xname(self):
        """Test that creating a limit string non-recursively only works with nodes"""
        blade_xname = 'x3000c0s0'
        with self.assertRaises(BOSFailure):
            BOSLimitString.from_string(blade_xname, recursive=False)


class TestBOSV2SessionWaiter(unittest.TestCase):
    """Test the BOSV2SessionWaiter class."""
    def setUp(self):
        self.session_id = 'abcdef-012345-678901-fdecba'

        self.mock_bos_client = MagicMock()
        self.mock_sat_session = patch('sat.cli.bootsys.bos.SATSession').start()
        self.mock_bos_client.get.return_value = MagicMock(ok=True, status_code=200, json=MagicMock(return_value={
            'status': 'complete',
            'managed_components_count': 10,
            'phases': {
                'percent_complete': 100.0,
                'percent_powering_on': 0.0,
                'percent_powering_off': 0.0,
                'percent_configuring': 0.0,
            },
            'percent_successful': 100.0,
            'percent_failed': 0.0,
            'percent_staged': 0.0,
            'error_summary': {},
            'timing': {
                'duration': '0:01:00',
                'end_time': '2022-01-01T00:00:00',
                'start_time': '2022-01-01T00:01:00',
            },
        }))

        patch('sat.cli.bootsys.bos.BOSClientCommon.get_bos_client', return_value=self.mock_bos_client).start()

        self.mock_session_thread = MagicMock(session_id=self.session_id)
        self.mock_session_thread.stopped.return_value = False

        self.waiter = BOSV2SessionWaiter(self.mock_session_thread, timeout=math.inf)

    def tearDown(self):
        patch.stopall()

    def test_session_is_completed(self):
        """Test that the waiter detects a completed session"""
        self.assertTrue(self.waiter.has_completed())

    def test_session_not_completed(self):
        """Test that the waiter detects a session that has not completed yet"""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'running',
            'phases': {
                'percent_complete': 50.0,
                'percent_powering_on': 20.0,
                'percent_powering_off': 0.0,
                'percent_configuring': 30.0,
            },
            'percent_successful': 50.0,
        })
        self.assertFalse(self.waiter.has_completed())

    def test_session_failed(self):
        """Test that the waiter detects when a session has failed"""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'running',
            'phases': {
                'percent_complete': 50.0,
                'percent_powering_on': 20.0,
                'percent_powering_off': 0.0,
                'percent_configuring': 30.0,
            },
            'percent_successful': 50.0,
            'percent_failed': 50.0,
        })
        self.assertFalse(self.waiter.has_completed())

    def test_session_superseded(self):
        """Test when the waiter's session has its managed components taken by another session"""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'complete',
            'managed_components_count': 0,
            'phases': {
                'percent_complete': 0,
                'percent_powering_on': 0,
                'percent_powering_off': 0,
                'percent_configuring': 0,
            },
            'percent_successful': 0,
            'percent_failed': 0,
        })
        with self.assertLogs(level='INFO'):
            self.assertTrue(self.waiter.has_completed())

    def test_staged_session_not_complete(self):
        """Test that a staged session still in pending state is not complete"""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'pending',
            'managed_components_count': 0,
            'phases': {
                'percent_complete': 0,
                'percent_powering_on': 0,
                'percent_powering_off': 0,
                'percent_configuring': 0,
            },
            'percent_successful': 0,
            'percent_failed': 0,
        })
        staged_waiter = BOSV2SessionWaiter(self.mock_session_thread, ['running', 'complete'],
                                           timeout=math.inf)

        self.assertFalse(staged_waiter.has_completed())

    def test_staged_session_running_complete(self):
        """Test that a staged session that has reached running state is complete."""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'running',
            'managed_components_count': 10,
            'phases': {
                'percent_complete': 0,
                'percent_powering_on': 0,
                'percent_powering_off': 0,
                'percent_configuring': 0,
            },
            'percent_successful': 0,
            'percent_failed': 0,
        })
        staged_waiter = BOSV2SessionWaiter(self.mock_session_thread, ['running', 'complete'],
                                           timeout=math.inf)

        self.assertTrue(staged_waiter.has_completed())

    def test_staged_session_empty_complete(self):
        """Test that a staged session with empty components in complete state is complete."""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'complete',
            'managed_components_count': 0,
            'phases': {
                'percent_complete': 0,
                'percent_powering_on': 0,
                'percent_powering_off': 0,
                'percent_configuring': 0,
            },
            'percent_successful': 0,
            'percent_failed': 0,
        })
        staged_waiter = BOSV2SessionWaiter(self.mock_session_thread, ['running', 'complete'],
                                           timeout=math.inf)

        with self.assertLogs(level='INFO'):
            self.assertTrue(staged_waiter.has_completed())

    def test_percent_complete_above_99(self):
        """Test that the waiter correctly handles percent_complete above 99 but below 100"""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'running',
            'phases': {
                'percent_complete': 99.6898,
                'percent_powering_on': 0.0,
                'percent_powering_off': 0.0,
                'percent_configuring': 0.0,
            },
            'percent_successful': 99.6898,
            'percent_failed': 0.0,
        })
        with self.assertLogs(level='INFO') as logs_cm:
            self.assertFalse(self.waiter.has_completed())
        self.assertEqual(2, len(logs_cm.records))
        self.assertEqual(
            logs_cm.records[1].message,
            f'Session {self.session_id}: 99.689800% components succeeded, '
            f'0.00% components failed'
        )

    def test_percent_complete_below_99(self):
        """Test that the waiter correctly handles percent_complete below 99"""
        self.mock_bos_client.get.return_value.json.return_value.update({
            'status': 'running',
            'phases': {
                'percent_complete': 78.5689,
                'percent_powering_on': 0.0,
                'percent_powering_off': 0.0,
                'percent_configuring': 0.0,
            },
            'percent_successful': 78.5689,
            'percent_failed': 0.0,
        })
        with self.assertLogs(level='INFO') as logs_cm:
            self.assertFalse(self.waiter.has_completed())
        self.assertEqual(2, len(logs_cm.records))
        self.assertEqual(
            logs_cm.records[1].message,
            f'Session {self.session_id}: 78.57% components succeeded, '
            f'0.00% components failed'
        )

    def test_session_status_404_error(self):
        """Test that the waiter raises WaitingFailure on a 404 error."""
        self.mock_bos_client.get.return_value.ok = False
        self.mock_bos_client.get.return_value.status_code = 404

        with self.assertRaises(WaitingFailure) as context:
            self.waiter.has_completed()

        self.assertEqual(
            str(context.exception),
            f'Failed to query session status: Session {self.session_id} does not exist.'
        )

    def test_session_status_503_error(self):
        """Test that the waiter logs a warning and continues on a 503 error."""
        self.mock_bos_client.get.side_effect = [
            MagicMock(ok=False, status_code=503, json=MagicMock(return_value={})),
            MagicMock(ok=True, status_code=200, json=MagicMock(return_value={
                'status': 'running',
                'managed_components_count': 10,
                'phases': {
                    'percent_complete': 75.0,
                    'percent_powering_on': 25.0,
                    'percent_powering_off': 0.0,
                    'percent_configuring': 50.0,
                },
                'percent_successful': 75.0,
                'percent_failed': 0.0,
            }))
        ]

        with self.assertLogs(level='WARNING') as logs_cm:
            result = self.waiter.has_completed()

        self.assertFalse(result)
        self.assertEqual(1, len(logs_cm.records))
        self.assertIn('Failed to query status of BOS session', logs_cm.records[0].message)

        # Ensuring it made the second call
        self.mock_bos_client.get.assert_called_with(
            self.mock_bos_client.session_path, self.session_id, 'status', raise_not_ok=False
        )


class TestBOSSessionThread(unittest.TestCase):
    """Test the BOSSessionThread class."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_bos_client = Mock()
        patch('sat.cli.bootsys.bos.BOSClientCommon.get_bos_client', return_value=self.mock_bos_client).start()
        patch('sat.cli.bootsys.bos.SATSession').start()
        self.mock_get_config_value = patch('sat.cli.bootsys.bos.get_config_value').start()

        self.mock_session_id = '0123456789abcdef'
        self.mock_create_response = {
            'operation': 'boot',  # Not used, doesn't have to match
            'templateUuid': 'template_uuid',  # Not used, doesn't have to match
            'links': [
                {
                    'href': f'v1/session/{self.mock_session_id}',
                    'jobId': f'boa-{self.mock_session_id}',
                    'rel': 'session',
                    'type': 'GET'
                }
            ]
        }
        self.mock_bos_client.create_session.return_value.json.return_value = self.mock_create_response

        self.mock_check_interval = patch(
            'sat.cli.bootsys.bos.PARALLEL_CHECK_INTERVAL', 3).start()

        self.mock_subprocess_run = patch('sat.cli.bootsys.bos.subprocess.run').start()
        # Possible return values from subprocess.run()
        self.error_response = Mock()
        self.error_response.returncode = 1
        self.error_response.stderr = 'timed out waiting for jobs/my-job'
        self.finished_response = Mock()
        self.finished_response.returncode = 0
        patch('sat.cli.bootsys.bos.sleep').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of a BOSSessionThread."""
        session_template = 'cle-1.3.0'
        operation = 'shutdown'

        bos_thread = BOSSessionThread(session_template, operation)

        self.assertEqual(session_template, bos_thread.session_template)
        self.assertEqual(operation, bos_thread.operation)
        self.assertEqual(False, bos_thread.complete)
        self.assertEqual(False, bos_thread.failed)
        self.assertEqual('', bos_thread.fail_msg)
        self.assertEqual(None, bos_thread.session_id)
        self.assertEqual(None, bos_thread.boa_job_id)
        self.assertEqual(3, bos_thread.max_consec_fails)
        self.assertEqual(0, bos_thread.consec_stat_fails)
        self.assertEqual(self.mock_check_interval, bos_thread.check_interval)
        self.assertFalse(bos_thread.stopped())

    def test_stop(self):
        """Test stop method of BOSSessionThread."""
        bos_thread = BOSSessionThread('cle-1.3.0', 'boot')
        self.assertFalse(bos_thread.stopped())
        bos_thread.stop()
        self.assertTrue(bos_thread.stopped())

    def test_mark_failed(self):
        """Test mark_failed method of BOSSessionThread."""
        session_template = 'uan'
        bos_thread = BOSSessionThread(session_template, 'boot')
        fail_msg = 'the bos session failed'
        bos_thread.mark_failed(fail_msg)
        self.assertTrue(bos_thread.failed)
        self.assertTrue(bos_thread.complete)
        self.assertEqual(fail_msg, bos_thread.fail_msg)

    def test_record_stat_failure(self):
        """Test record_stat_failure method of BOSSessionThread."""
        bos_thread = BOSSessionThread('uan', 'shutdown')
        with patch.object(bos_thread, 'mark_failed') as mock_mark_failed:
            for _ in range(bos_thread.max_consec_fails):
                bos_thread.record_stat_failure()
                mock_mark_failed.assert_not_called()

            bos_thread.record_stat_failure()
            mock_mark_failed.assert_called_once_with(
                'Aborting because session status query failed {} times in a '
                'row.'.format(bos_thread.max_consec_fails + 1)
            )

    def test_create_session_bos_v1(self):
        """Test create_session method of BOSSessionThread."""
        # TODO(CRAYSAT-1612): write a unit test for create_session with BOS v2 as well.
        self.mock_get_config_value.return_value = 'v1'
        bos_thread = BOSSessionThread('cle-1.3.0', 'boot')
        bos_thread.create_session()
        self.assertEqual(self.mock_session_id, bos_thread.session_id)
        self.assertEqual(self.mock_create_response['links'][0]['jobId'],
                         bos_thread.boa_job_id)

    @patch('sat.cli.bootsys.bos.boa_job_successful', return_value=True)
    def test_bos_v1_run(self, _):
        """Test the run() method of BOSSessionThread using BOS v1."""
        self.mock_get_config_value.return_value = 'v1'
        bos_thread = BOSSessionThread('cle-1.3.0', 'boot')
        bos_thread.max_consec_fails = 0
        self.mock_subprocess_run.side_effect = (
            self.error_response,
            self.finished_response
        )
        bos_thread.run()
        self.assertTrue(bos_thread.complete)
        self.assertFalse(bos_thread.failed)

    @patch('sat.cli.bootsys.bos.boa_job_successful', return_value=True)
    def test_bos_v1_run_new_k8s_cli(self, _):
        """Test the run() method of BOSSessionThread using BOS v1 with a newer k8s CLI."""
        self.mock_get_config_value.return_value = 'v1'
        self.error_response.stderr = 'condition not met for jobs/my-job'
        bos_thread = BOSSessionThread('cle-1.3.0', 'boot')
        bos_thread.max_consec_fails = 0
        self.mock_subprocess_run.side_effect = (
            self.error_response,
            self.finished_response
        )
        bos_thread.run()
        self.assertTrue(bos_thread.complete)
        self.assertFalse(bos_thread.failed)

    @patch('sat.cli.bootsys.bos.boa_job_successful', return_value=True)
    def test_bos_v1_run_kubectl_wait_error(self, _):
        """Test the run() method of BOSSessionThread when kubectl returns an error."""
        self.mock_get_config_value.return_value = 'v1'
        self.error_response.stderr = 'command not found: kubectl'
        bos_thread = BOSSessionThread('cle-1.3.0', 'boot')
        bos_thread.max_consec_fails = 0
        self.mock_subprocess_run.return_value = self.error_response
        with self.assertLogs(level=logging.WARNING) as logs:
            bos_thread.run()
        self.assertRegex(
            logs.records[0].message,
            r'The \'kubectl wait\' command failed instead of timing out.'
        )
        self.assertTrue(bos_thread.complete)
        self.assertTrue(bos_thread.failed)


class TestGetSessionTemplates(ExtendedTestCase):
    """Test the function which processes BOS template options and finds defaults."""
    def setUp(self):
        """Set up some mocks."""
        # The deprecated parameters have empty strings as their defaults, while
        # bos_templates has an empty list as its default.
        self.fake_config = {
            'cle_bos_template': '',
            'uan_bos_template': '',
            'bos_templates': []
        }
        patch('sat.cli.bootsys.bos.get_config_value', side_effect=self.fake_get_config_value).start()
        self.deprecated_warning = (
            'The --bos-templates/bos_templates option was not specified. Please '
            'use this option to specify session templates. Proceeding with session '
            'templates: {}'
        )

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def fake_get_config_value(self, query_string):
        """Mimic the behavior of get_config_value."""
        return self.fake_config[query_string.split('.')[-1]]

    def test_get_session_templates_defaults(self):
        """With no options, a BOSFailure should occur as no templates were given."""
        with self.assertRaisesRegex(BOSFailure, 'No BOS templates were specified.'):
            get_session_templates()

    def test_get_session_templates_bos_templates_option(self):
        """With only bos_templates option given, the value specified by the bos_templates option is used."""
        self.fake_config['bos_templates'] = ['cos-2.0.1', 'uan-2.0.1']
        expected = ['cos-2.0.1', 'uan-2.0.1']
        with patch('sat.cli.bootsys.bos.LOGGER') as mock_logger:
            actual = get_session_templates()
        mock_logger.warning.assert_not_called()
        self.assertCountEqual(expected, actual)

    def test_get_session_templates_just_one_template(self):
        """With just one template given with bos_templates, use it."""
        self.fake_config['bos_templates'] = ['cos-2.0.1']
        expected = ['cos-2.0.1']
        with patch('sat.cli.bootsys.bos.LOGGER') as mock_logger:
            actual = get_session_templates()
        mock_logger.warning.assert_not_called()
        self.assertCountEqual(expected, actual)

    def test_get_session_templates_bos_templates_and_cle_option(self):
        """With bos_templates and cle_bos_template, prefer bos_templates."""
        self.fake_config['bos_templates'] = ['cos-2.0.1', 'uan-2.0.1']
        self.fake_config['cle_bos_template'] = 'cos-9.9.9'
        expected = ['cos-2.0.1', 'uan-2.0.1']
        actual = get_session_templates()
        self.assertCountEqual(expected, actual)

    def test_get_session_templates_bos_templates_and_uan_option(self):
        """With bos_templates and uan_bos_template, prefer bos_templates."""
        self.fake_config['bos_templates'] = ['cos-2.0.1', 'uan-2.0.1']
        self.fake_config['uan_bos_template'] = 'uan-9.9.9'
        expected = ['cos-2.0.1', 'uan-2.0.1']
        actual = get_session_templates()
        self.assertCountEqual(expected, actual)

    def test_get_session_templates_all_options_given(self):
        """With all options given, bos_templates is preferred."""
        self.fake_config['bos_templates'] = ['cos-2.0.1', 'uan-2.0.1']
        self.fake_config['cle_bos_template'] = 'cos-9.9.9'
        self.fake_config['uan_bos_template'] = 'uan-9.9.9'
        expected = ['cos-2.0.1', 'uan-2.0.1']
        actual = get_session_templates()
        self.assertCountEqual(expected, actual)

    def test_get_session_templates_deprecated_options(self):
        """With only deprecated options given, use their values and log a warning."""
        self.fake_config['cle_bos_template'] = 'cos-2.0.1'
        self.fake_config['uan_bos_template'] = 'uan-2.0.1'
        expected = ['cos-2.0.1', 'uan-2.0.1']
        with self.assertLogs(level=logging.WARNING) as logs:
            actual = get_session_templates()
        self.assert_in_element(self.deprecated_warning.format(','.join(expected)), logs.output)
        self.assertCountEqual(expected, actual)


class TestGetTemplatesNeedingOperation(ExtendedTestCase):
    """
    Tests for the get_templates_needing_operation() function.
    """
    def setUp(self) -> None:
        """Set up some mocks."""
        self.mock_bos_client: Mock = Mock()
        patch('sat.cli.bootsys.bos.BOSClientCommon.get_bos_client',
              return_value=self.mock_bos_client).start()
        self.mock_hsm_client = patch('sat.cli.bootsys.bos.HSMClient').start().return_value
        self.mock_hsm_components = [
            {
                'ID': 'x3000c0s0b0n1',
                'Role': 'Application',
                'SubRole': 'UAN',
                'State': 'Ready',
                'Type': 'Node'
            },
            {
                'ID': 'x3000c0s1b0n1',
                'Role': 'Application',
                'SubRole': 'Other',
                'State': 'Ready',
                'Type': 'Node'
            },
            {
                'ID': 'x3000c0s2b0n1',
                'Role': 'Compute',
                'State': 'Ready',
                'Type': 'Node'
            },
            {
                'ID': 'x3000c0s3b0n1',
                'Role': 'Compute',
                'State': 'Ready',
                'Type': 'Node'
            }
        ]

        self.mock_hsm_client.get.side_effect = self.fake_get_hsm_components
        patch('sat.cli.bootsys.bos.SATSession').start()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    @staticmethod
    def fake_get_nodes_by_state(states: list[str]) -> dict[Any, list[Any]]:
        nodes_by_state: dict[Any, list[Any]] = dict()
        for state in states:
            nodes_by_state[state] = list("some data")
        return nodes_by_state

    @staticmethod
    def _match_param(param_value, component_value):
        """Helper for fake_get_hsm_components."""
        if isinstance(param_value, list):
            return component_value in param_value
        else:
            return component_value == param_value

    def fake_get_hsm_components(self, *_, params):
        """Fake the behavior of HSMClient.get('State', 'Components', params={...})."""
        # When SAT queries HSM, it uses lowercase query parameters, which HSM handles.
        lowercase_to_uppercase_hsm_format = {
            'role': 'Role',
            'subrole': 'SubRole',
            'id': 'ID',
            'type': 'Type'
        }
        matching_components = [
            component for component in self.mock_hsm_components
            if all(
                self._match_param(param_value, component.get(lowercase_to_uppercase_hsm_format[param_name]))
                for param_name, param_value in params.items()
            )
        ]

        resp = Mock()
        resp.json.return_value = {'Components': matching_components}
        return resp


class TestDoBosShutdowns(ExtendedTestCase):
    """Tests for the do_bos_shutdowns() function."""
    def setUp(self):
        self.mock_prompt = patch('sat.cli.bootsys.bos.prompt_continue').start()
        self.mock_do_bos_ops = patch('sat.cli.bootsys.bos.do_bos_operations').start()
        self.mock_get_config = patch('sat.cli.bootsys.bos.get_config_value', return_value=60).start()

        self.limit = None
        self.args = Namespace(bos_limit=self.limit, recursive=False, staged_session=False)
        self.args.disruptive = False

    def tearDown(self):
        patch.stopall()

    def test_do_bos_shutdowns_prompt(self):
        """Test running BOS shutdown with prompting to continue."""
        do_bos_shutdowns(self.args)
        self.mock_prompt.assert_called_once()
        self.mock_do_bos_ops.assert_called_once_with(
            'shutdown', 60, limit=self.limit, recursive=False, stage=False)

    def test_do_bos_shutdowns_without_prompt(self):
        """Test running BOS shutdown without prompting."""
        self.args.disruptive = True
        do_bos_shutdowns(self.args)

        self.mock_prompt.assert_not_called()
        self.mock_do_bos_ops.assert_called_once_with(
            'shutdown', 60, limit=self.limit, recursive=False, stage=False)


class TestDoBosReboots(ExtendedTestCase):
    """Tests for the do_bos_reboots() function."""

    def setUp(self):
        self.mock_prompt = patch('sat.cli.bootsys.bos.prompt_continue').start()
        self.mock_do_bos_ops = patch(
            'sat.cli.bootsys.bos.do_bos_operations').start()
        self.mock_get_config = patch(
            'sat.cli.bootsys.bos.get_config_value', side_effect=[60, 90]).start()

        self.limit = None
        self.args = Namespace(bos_limit=self.limit, recursive=False, staged_session=False)
        self.args.disruptive = False

    def tearDown(self):
        patch.stopall()

    def test_do_bos_reboots_prompt(self):
        """Test running BOS shutdown with prompting to continue."""
        do_bos_reboots(self.args)
        self.mock_prompt.assert_called_once()
        self.mock_do_bos_ops.assert_called_once_with(
            'reboot', 150, limit=self.limit, recursive=False, stage=False)

    def test_do_bos_reboots_without_prompt(self):
        """Test running BOS shutdown without prompting."""
        self.args.disruptive = True
        do_bos_reboots(self.args)

        self.mock_prompt.assert_not_called()
        self.mock_do_bos_ops.assert_called_once_with(
            'reboot', 150, limit=self.limit, recursive=False, stage=False)


if __name__ == '__main__':
    unittest.main()
