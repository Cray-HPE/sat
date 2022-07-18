#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.diag.fox module
"""

import json
import logging
import unittest
from unittest import mock
import uuid

from tests.test_util import ExtendedTestCase
from tests.cli.diag.fakes import (
    delayed_launch,
    failed_launch,
    job_that_completes,
    job_that_runs_forever,
    job_with_exception,
    MOCK_HMJTD_COMPLETE_RESPONSE,
    MOCK_HMJTD_ERROR_RESPONSE,
    MOCK_HMJTD_NEW_RESPONSE,
    MOCK_HMJTD_RUNNING_RESPONSE,
    positive_ints_generator,
)

from sat.cli.diag.fox import RunningDiagPool


class TestRunningDiagPool(ExtendedTestCase):
    def setUp(self):
        """Set up mocks"""
        # mock SATSession to skip a warning when creating a SATSession to pass to FoxClient()
        mock.patch('sat.cli.diag.fox.SATSession').start()
        self.mock_fox_client_cls = mock.patch('sat.cli.diag.fox.FoxClient').start()
        self.mock_fox_client = self.mock_fox_client_cls.return_value
        self.mock_fox_client.get_job_launch_status.return_value = json.loads(MOCK_HMJTD_NEW_RESPONSE)
        self.mock_fox_client.get_job_status_for_xname.return_value = json.loads(MOCK_HMJTD_COMPLETE_RESPONSE)
        self.xnames = ['x1000c0r1b0']
        self.timeout = 10
        self.interval = 0
        # mock time so that two successive calls to time.time() report one second having passed
        self.mock_time = mock.patch('sat.cli.diag.fox.time').start()
        self.mock_time.time.side_effect = positive_ints_generator()

    def tearDown(self):
        """Stop mocks"""
        mock.patch.stopall()

    def _create_diag_pool(self):
        """Create a RunningDiagPool."""
        self.mock_fox_client.initiate_diag.return_value = uuid.uuid4()
        return RunningDiagPool(
            xnames=self.xnames,
            diag_command='runMemTester',
            diag_args='-h',
            poll_interval=self.interval,
            timeout=self.timeout
        )

    def test_init(self):
        """Test creating a diag creates a DiagStatus for each xname"""
        rdp = self._create_diag_pool()
        self.mock_fox_client_cls.assert_called_once()
        self.assertEqual([diag.xname for diag in rdp], self.xnames)
        self.assertEqual(rdp.timeout, self.timeout)
        self.assertEqual(rdp.interval, self.interval)

    def test_poll_diag_statuses(self):
        """Polling updates the diag status when the job completes instantaneously"""
        rdp = self._create_diag_pool()
        rdp.poll_diag_statuses()
        self.assertTrue(all(diag.complete for diag in rdp))
        self.assertTrue(all(diag.taskstate == 'Completed' for diag in rdp))

    def test_poll_timeout(self):
        """When the diag is running forever, we set the diag status to 'Timed Out'"""
        rdp = self._create_diag_pool()
        self.mock_fox_client.get_job_status_for_xname.return_value = json.loads(MOCK_HMJTD_RUNNING_RESPONSE)
        with self.assertLogs(level=logging.ERROR) as logs:
            rdp.poll_until_complete()
        self.assertTrue(all(diag.taskstate == 'Timed Out' for diag in rdp))
        self.assert_in_element('runMemTester on x1000c0r1b0 exceeded timeout (10 seconds).', logs.output)

    def test_poll_diag_statuses_between_intervals(self):
        """When the interval has not yet passed, do not poll."""
        self.interval = 2
        rdp = self._create_diag_pool()
        rdp.poll_diag_statuses()
        self.mock_fox_client.get_job_status_for_xname.assert_not_called()

    def test_poll_diag_statuses_complete(self):
        """Polling updates the diag status when the job completes after one poll where it didn't"""
        rdp = self._create_diag_pool()
        self.mock_fox_client.get_job_status_for_xname.side_effect = [
            json.loads(MOCK_HMJTD_RUNNING_RESPONSE), json.loads(MOCK_HMJTD_COMPLETE_RESPONSE)
        ]
        rdp.poll_until_complete()
        self.assertTrue(all(diag.taskstate == 'Completed' for diag in rdp))

    def test_poll_diag_failed_launch(self):
        """When a diag fails to launch, it is ignored."""
        self.mock_fox_client.get_job_launch_status.return_value = json.loads(MOCK_HMJTD_ERROR_RESPONSE)
        with self.assertLogs(level=logging.ERROR) as logs:
            rdp = self._create_diag_pool()
            rdp.poll_until_launched()
        self.assert_in_element('Error on x1000c0r1b0: [Redacted for simplicity.]', logs.output)
        rdp.poll_until_complete()
        self.assertListEqual([diag for diag in rdp], [])

    def test_poll_diag_delayed_launch(self):
        """When a diag takes a couple tries to launch, it should complete normally."""
        self.mock_fox_client.get_job_launch_status.side_effect = [
            {}, json.loads(MOCK_HMJTD_NEW_RESPONSE)
        ]
        rdp = self._create_diag_pool()
        rdp.poll_until_launched()
        self.assertTrue(all(diag.taskstate == 'New' for diag in rdp))
        rdp.poll_until_complete()
        self.assertTrue(all(diag.taskstate == 'Completed' for diag in rdp))
        self.assertEqual(len([diag for diag in rdp]), 1)

    def test_multiple_xname_diags(self):
        """Diags on two xnames should result in separate diag statuses"""
        self.xnames = ['x1000c0r1b0', 'x1000c0r2b0']
        fake_responses = {
            'x1000c0r1b0': job_that_completes(),
            'x1000c0r2b0': job_that_completes()
        }
        self.mock_fox_client.get_job_status_for_xname.side_effect = lambda jobid, xname: next(fake_responses[xname])
        rdp = self._create_diag_pool()
        rdp.poll_until_complete()
        self.assertTrue(all(diag.taskstate == 'Completed' for diag in rdp))
        self.assertEqual(len([diag for diag in rdp]), 2)

    def test_multiple_xname_diags_one_timeout(self):
        """Test diags on two xnames where one times out."""
        self.xnames = ['x1000c0r1b0', 'x1000c0r2b0']
        fake_responses = {
            'x1000c0r1b0': job_that_completes(),
            'x1000c0r2b0': job_that_runs_forever()
        }
        self.mock_fox_client.get_job_status_for_xname.side_effect = lambda job_id, xname: next(fake_responses[xname])
        rdp = self._create_diag_pool()
        with self.assertLogs(level=logging.ERROR) as logs:
            rdp.poll_until_complete()
        completed_diag = [diag for diag in rdp if diag.xname == 'x1000c0r1b0'][0]
        failed_diag = [diag for diag in rdp if diag.xname == 'x1000c0r2b0'][0]
        self.assertEqual(completed_diag.taskstate, 'Completed')
        self.assertEqual(failed_diag.taskstate, 'Timed Out')
        self.assert_in_element('runMemTester on x1000c0r2b0 exceeded timeout (10 seconds)', logs.output)

    def test_multiple_xname_diags_one_exception(self):
        """Test diags on two xnames where one encounters an 'exception'."""
        self.xnames = ['x1000c0r1b0', 'x1000c0r2b0']
        fake_responses = {
            'x1000c0r1b0': job_that_completes(),
            'x1000c0r2b0': job_with_exception()
        }
        self.mock_fox_client.get_job_status_for_xname.side_effect = lambda job_id, xname: next(fake_responses[xname])
        rdp = self._create_diag_pool()
        rdp.poll_until_complete()
        completed_diag = [diag for diag in rdp if diag.xname == 'x1000c0r1b0'][0]
        failed_diag = [diag for diag in rdp if diag.xname == 'x1000c0r2b0'][0]
        self.assertEqual(completed_diag.taskstate, 'Completed')
        self.assertEqual(failed_diag.taskstate, 'Exception')

    def test_multiple_xname_diags_one_failed_launch(self):
        """Test one out of two diags failed to launch that the failed one is removed."""
        self.xnames = ['x1000c0r1b0', 'x1000c0r2b0']
        fake_launch_responses = {
            'x1000c0r1b0': delayed_launch(),
            'x1000c0r2b0': failed_launch()
        }
        self.mock_fox_client.get_job_launch_status.side_effect = lambda job_id, xname: next(
            fake_launch_responses[xname]
        )
        with self.assertLogs(level=logging.ERROR) as logs:
            rdp = self._create_diag_pool()
            rdp.poll_until_launched()
        rdp.poll_until_complete()
        all_diags = [diag for diag in rdp]
        self.assertEqual(all_diags[0].xname, 'x1000c0r1b0')
        self.assertEqual(len(all_diags), 1)
        self.assert_in_element('Error on x1000c0r2b0: [Redacted for simplicity.]', logs.output)


if __name__ == '__main__':
    unittest.main()
