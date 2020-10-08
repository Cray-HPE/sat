"""
Unit tests for the sat.cli.bootsys.bos module.

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

import shlex
import subprocess
import unittest
from unittest.mock import Mock, call, patch

from sat.cli.bootsys.bos import (
    BOSFailure,
    BOSSessionThread,
    boa_job_successful
)


class TestBOAJobSuccessful(unittest.TestCase):
    """Tests for whether the BOA job is successful."""
    def setUp(self):
        """Create some mocks."""
        self.boa_job_id = 'boa-1234567890abcdef'
        self.boa_pods = ['{}-{}'.format(self.boa_job_id, i) for i in range(4)]
        self.boa_pod_logs = [
            'Starting a BOA job.'
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
        self.assertFalse(boa_job_successful(self.boa_job_id))

    def test_failed_boa_job_middle_log(self):
        """Test boa_job_successful on a failed BOA job with log in middle."""
        self.boa_pod_logs.insert(1, self.fatal_boa_message)
        self.assertFalse(boa_job_successful(self.boa_job_id))

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


class TestBOSSessionThread(unittest.TestCase):
    """Test the BOSSessionThread class."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_bos_client = Mock()
        patch('sat.cli.bootsys.bos.BOSClient', return_value=self.mock_bos_client).start()
        patch('sat.cli.bootsys.bos.SATSession').start()

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

    def test_create_session(self):
        """Test create_session method of BOSSessionThread."""
        bos_thread = BOSSessionThread('cle-1.3.0', 'boot')
        bos_thread.create_session()
        self.assertEqual(self.mock_session_id, bos_thread.session_id)
        self.assertEqual(self.mock_create_response['links'][0]['jobId'],
                         bos_thread.boa_job_id)


if __name__ == '__main__':
    unittest.main()
