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
Unit tests for the sat.cli.bootsys.discovery module.
"""
import unittest
from datetime import datetime, timedelta
from unittest.mock import MagicMock, Mock, patch

from dateutil.tz import tzutc
from kubernetes.client.rest import ApiException
from kubernetes.config import ConfigException

from sat.hms_discovery import (HMSDiscoveryCronJob, HMSDiscoveryError,
                               HMSDiscoveryScheduledWaiter,
                               HMSDiscoverySuspendedWaiter)


class TestHMSDiscoveryCronJob(unittest.TestCase):
    """Tests for the HMSDiscoveryCronJob class."""

    def setUp(self):
        """Set up some mocks."""
        self.mock_load_api = patch('sat.hms_discovery.load_kube_api').start()
        self.mock_batch_api = self.mock_load_api.return_value
        self.hdcj = HMSDiscoveryCronJob()

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_k8s_batch_api_success(self):
        """Test the k8s_batch_api property"""
        batch_api_return_vals = [Mock(), Mock()]
        self.mock_load_api.side_effect = batch_api_return_vals

        k8s_batch_api = self.hdcj.k8s_batch_api
        # Call it again to check that it is cached properly
        second_k8s_batch_api = self.hdcj.k8s_batch_api

        self.mock_load_api.assert_called_once()
        self.assertEqual(batch_api_return_vals[0], k8s_batch_api)
        self.assertEqual(k8s_batch_api, second_k8s_batch_api)

    def test_k8s_batch_api_config_exception(self):
        """Test the k8s_batch_api property when loading config file raises ConfigException"""
        self.mock_load_api.side_effect = ConfigException

        with self.assertRaisesRegex(HMSDiscoveryError, 'Failed to load kubernetes config'):
            _ = self.hdcj.k8s_batch_api

    def test_data_success(self):
        """Test the data property in successful case."""
        data = self.hdcj.data

        self.mock_batch_api.read_namespaced_cron_job.assert_called_once_with(
            HMSDiscoveryCronJob.HMS_DISCOVERY_NAME, HMSDiscoveryCronJob.HMS_DISCOVERY_NAMESPACE
        )
        self.assertEqual(self.mock_batch_api.read_namespaced_cron_job.return_value, data)

    def test_data_api_exception(self):
        """Test the data property with the k8s client raising an ApiException."""
        self.mock_batch_api.read_namespaced_cron_job.side_effect = ApiException

        with self.assertRaisesRegex(HMSDiscoveryError, 'Failed to get data'):
            _ = self.hdcj.data

    def test_schedule_interval(self):
        """Test the schedule_interval property returns the correct intervals for various schedules"""
        schedules_and_intervals = [
            ('*/3 * * * *', 180),
            ('*/15 * * * *', 900),
            ('0 */3 * * *', 10800),
            ('5 0 * * *', 86400),
        ]

        for schedule, interval in schedules_and_intervals:
            mock_cron_job = Mock()
            mock_cron_job.spec.schedule = schedule
            self.mock_batch_api.read_namespaced_cron_job.return_value = mock_cron_job
            self.assertEqual(interval, self.hdcj.schedule_interval)

    def test_get_last_schedule_time(self):
        """Test get last_schedule_time method."""
        self.assertEqual(
            self.mock_batch_api.read_namespaced_cron_job.return_value.status.last_schedule_time,
            self.hdcj.get_last_schedule_time()
        )

    def test_get_suspend_status(self):
        """Test get_suspend_status method."""
        self.assertEqual(
            self.mock_batch_api.read_namespaced_cron_job.return_value.spec.suspend,
            self.hdcj.get_suspend_status()
        )

    @patch('sat.hms_discovery.HMSDiscoveryCronJob.get_suspend_status')
    def test_suspend_already_suspended(self, mock_get_suspend_status):
        """Test suspending when already suspended."""
        mock_get_suspend_status.return_value = True
        self.hdcj.set_suspend_status(True)

        self.mock_batch_api.patch_namespaced_cron_job.assert_not_called()

    @patch('sat.hms_discovery.HMSDiscoveryCronJob.get_suspend_status')
    def test_suspend_already_not_suspended(self, mock_get_suspend_status):
        """Test setting suspend status to False when already not suspended."""
        mock_get_suspend_status.return_value = False
        self.hdcj.set_suspend_status(False)

        self.mock_batch_api.patch_namespaced_cron_job.assert_not_called()

    @patch('sat.hms_discovery.HMSDiscoveryCronJob.get_suspend_status')
    def test_suspend_when_not_suspended(self, mock_get_suspend_status):
        """Test suspending when not currently suspended."""
        mock_get_suspend_status.return_value = False
        self.hdcj.set_suspend_status(True)

        self.mock_batch_api.patch_namespaced_cron_job.assert_called_once_with(
            HMSDiscoveryCronJob.HMS_DISCOVERY_NAME,
            HMSDiscoveryCronJob.HMS_DISCOVERY_NAMESPACE,
            {'spec': {'suspend': True}}
        )

    @patch('sat.hms_discovery.HMSDiscoveryCronJob.get_suspend_status')
    def test_resume_when_suspended(self, mock_get_suspend_status):
        """Test resuming when currently suspended."""
        mock_get_suspend_status.return_value = True
        self.hdcj.set_suspend_status(False)

        self.mock_batch_api.patch_namespaced_cron_job.assert_called_once_with(
            HMSDiscoveryCronJob.HMS_DISCOVERY_NAME,
            HMSDiscoveryCronJob.HMS_DISCOVERY_NAMESPACE,
            {'spec': {'suspend': False}}
        )

    @patch('sat.hms_discovery.HMSDiscoveryCronJob.get_suspend_status')
    def test_set_suspend_api_exception(self, mock_get_suspend_status):
        """Test suspending when already suspended."""
        mock_get_suspend_status.return_value = False
        self.mock_batch_api.patch_namespaced_cron_job.side_effect = ApiException
        expected_regex = f'Failed to suspend {HMSDiscoveryCronJob.FULL_NAME}'

        with self.assertRaisesRegex(HMSDiscoveryError, expected_regex):
            self.hdcj.set_suspend_status(True)

    def test_get_latest_next_schedule_time(self):
        """Test get_latest_next_schedule_time."""

        # Create subclass of `datetime` to pass the `issubclass` check in `croniter._get_next`
        class MockDateTime(datetime):
            @classmethod
            def now(cls, *args, **kwargs):
                return datetime(2020, 12, 31, 10, 0, 0)

        self.mock_batch_api.read_namespaced_cron_job.return_value.spec = Mock(schedule='*/3 * * * *')
        expected = datetime(2020, 12, 31, 10, 3, 0)

        with patch('sat.hms_discovery.datetime', MockDateTime):
            # Call it twice to ensure it returns the same thing the second time
            # rather than the next expected schedule time.
            next_time = self.hdcj.get_latest_next_schedule_time()
            same_next_time = self.hdcj.get_latest_next_schedule_time()

        self.assertEqual(expected, next_time)
        self.assertEqual(expected, same_next_time)

    def test_is_not_active_with_no_jobs(self):
        """Test that the job is considered not active if there are not running jobs"""
        self.mock_batch_api.read_namespaced_cron_job.return_value.status.active = []
        self.assertFalse(self.hdcj.is_active())

    def test_is_active_when_jobs_active(self):
        """Test that the job is considered active if there are running jobs"""
        self.mock_batch_api.read_namespaced_cron_job.return_value.status.active = [
            Mock(name=f'discovery-job-{n}')
            for n in range(5)
        ]
        self.assertTrue(self.hdcj.is_active())


class TestHMSDiscoveryScheduledWaiter(unittest.TestCase):
    """Test the HMSDiscoveryScheduledWaiter class."""

    def setUp(self):
        """Set up mocks."""
        self.mock_datetime = patch('sat.hms_discovery.datetime').start()

        self.poll_interval = 5
        self.grace_period = 30
        self.start_time = datetime(2020, 10, 31, 8, 0, 0, tzinfo=tzutc())
        self.mock_datetime.now.return_value = self.start_time

        self.next_sched_time = datetime(2020, 10, 31, 8, 3, 0, tzinfo=tzutc())
        self.mock_hd_cron_job = patch('sat.hms_discovery.HMSDiscoveryCronJob').start().return_value
        self.mock_hd_cron_job.schedule_interval = 180

        self.hd_waiter = HMSDiscoveryScheduledWaiter(self.poll_interval, self.grace_period)

    def tearDown(self):
        """Stop all patches."""
        patch.stopall()

    def test_init(self):
        """Test creation of an HMSDiscoveryScheduledWaiter."""
        self.assertEqual(self.mock_hd_cron_job.schedule_interval + self.grace_period,
                         self.hd_waiter.timeout)
        self.assertEqual(self.poll_interval, self.hd_waiter.poll_interval)
        self.assertEqual(self.start_time, self.hd_waiter.start_time)
        self.assertEqual(self.mock_hd_cron_job, self.hd_waiter.hd_cron_job)

    def test_init_start_time(self):
        """Test creation of an HMSDiscoveryScheduledWaiter with overridden start_time"""
        start_time = datetime(2018, 6, 7, 8, 45, 0, tzinfo=tzutc())
        hd_waiter = HMSDiscoveryScheduledWaiter(start_time=start_time)
        self.assertEqual(start_time, hd_waiter.start_time)

    def test_condition_name(self):
        """Test the condition_name method of the HMSDiscoveryScheduledWaiter."""
        self.assertEqual('HMS Discovery Scheduled', self.hd_waiter.condition_name())

    def test_has_completed_false(self):
        """Test has_completed method of HMSDiscoveryScheduledWaiter when it has not completed."""
        # Make it look like the cronjob was last scheduled before we started waiting
        last_schedule_time = self.start_time - timedelta(minutes=30)
        self.mock_hd_cron_job.get_last_schedule_time.return_value = last_schedule_time
        self.assertFalse(self.hd_waiter.has_completed())

    def test_has_completed_true(self):
        """Test has_completed method of HMSDiscoveryScheduledWaiter when it has completed."""
        # Make it look like the cronjob started right when expected.
        mock_job = MagicMock()
        mock_job.metadata.creation_timestamp = self.start_time + timedelta(minutes=3)
        self.mock_hd_cron_job.get_jobs.return_value = [mock_job]

        self.assertTrue(self.hd_waiter.has_completed())

    def test_has_completed_error(self):
        """Test has_completed method of HMSDiscoveryScheduledWaiter when an error occurs."""
        msg = 'k8s failure'
        self.mock_hd_cron_job.get_jobs.side_effect = ApiException(msg)
        with self.assertLogs(level='WARNING'):
            self.assertFalse(self.hd_waiter.has_completed())


class TestHMSDiscoverySuspendedWaiter(unittest.TestCase):
    """Tests for the HMSDiscoverySuspendedWaiter class"""
    def setUp(self):
        self.mock_hd_cron_job = patch('sat.hms_discovery.HMSDiscoveryCronJob').start().return_value

    def test_cron_job_is_suspended(self):
        """Test that the cron job is suspended and has no running jobs"""
        self.mock_hd_cron_job.get_suspend_status.return_value = True
        self.mock_hd_cron_job.is_active.return_value = False
        self.assertTrue(HMSDiscoverySuspendedWaiter(10).has_completed())

    def test_cron_job_suspended_with_running_jobs(self):
        """Test that the waiter continues waiting when the cron job is suspended and but has running jobs"""
        self.mock_hd_cron_job.get_suspend_status.return_value = True
        self.mock_hd_cron_job.is_active.return_value = True
        self.assertFalse(HMSDiscoverySuspendedWaiter(10).has_completed())

    def test_cron_job_not_suspended(self):
        """Test that the waiter continues waiting when the cron job is not suspended"""
        for is_active in [False, True]:
            with self.subTest(is_active=is_active):
                self.assertFalse(HMSDiscoverySuspendedWaiter(10).has_completed())


if __name__ == '__main__':
    unittest.main()
