#
# MIT License
#
# (C) Copyright 2021, 2023 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cronjob module.
"""
import datetime
import unittest
from unittest.mock import MagicMock, patch

from croniter import croniter
from dateutil.tz import tzutc
from kubernetes.client import (BatchV1Api, V1CronJob, V1CronJobSpec,
                               V1CronJobStatus, V1JobTemplateSpec,
                               V1ObjectMeta)

from sat.cronjob import (cronjob_stuck, recreate_cronjob,
                         recreate_namespaced_stuck_cronjobs)


class TestRecreateCronjobs(unittest.TestCase):
    def setUp(self):
        now = datetime.datetime.now(tz=tzutc())

        # Truncate the current time to the "top of the hour" time. Since all
        # the schedule intervals used in the tests are factors of 60, the "top
        # of the hour" will always be a scheduled time.
        self.now = datetime.datetime(*now.timetuple()[:4], tzinfo=tzutc())
        self.mock_batch_api_client = MagicMock(autospec=BatchV1Api)

    @staticmethod
    def create_cronjob_with_schedule(schedule, last_schedule_time, name=None, namespace=None):
        template = V1JobTemplateSpec()
        spec = V1CronJobSpec(job_template=template, schedule=schedule)
        cronjob = V1CronJob(spec=spec)
        cronjob.metadata = V1ObjectMeta(name=name, namespace=namespace)
        cronjob.status = V1CronJobStatus()
        cronjob.status.last_schedule_time = last_schedule_time
        return cronjob

    def get_prev_and_most_recent(self, schedule, delta):
        it = croniter(schedule)
        it.set_current(self.now)
        prev = datetime.datetime.fromtimestamp(it.get_prev(), tz=tzutc())
        return prev, prev + delta

    def test_cron_job_is_stuck(self):
        """Test detecting if a cronjob is stuck"""
        schedule = '*/1 * * * *'
        prev, last_schedule_time = self.get_prev_and_most_recent(schedule, datetime.timedelta(minutes=-2))
        cj = self.create_cronjob_with_schedule(schedule, last_schedule_time)
        self.assertTrue(cronjob_stuck(cj, curr_time=prev))

    def test_cron_job_is_not_stuck(self):
        """Test detecting if a cronjob is not stuck"""
        schedule = '*/3 * * * *'
        prev, last_schedule_time = self.get_prev_and_most_recent(schedule, datetime.timedelta(minutes=-1))
        cj = self.create_cronjob_with_schedule(schedule, last_schedule_time)
        self.assertFalse(cronjob_stuck(cj, curr_time=prev))

    def test_new_cron_job_is_not_stuck(self):
        """Test that a newly created cronjob is not stuck"""
        schedule = '*/3 * * * *'
        prev, creation = self.get_prev_and_most_recent(schedule, datetime.timedelta(minutes=-1))
        cj = self.create_cronjob_with_schedule(schedule, None)
        cj.metadata.creation_timestamp = creation
        self.assertFalse(cronjob_stuck(cj, curr_time=prev))

    def test_suspended_cron_jobs_not_stuck(self):
        """Test that suspended cronjobs aren't marked as stuck"""
        schedule = '*/1 * * * *'
        prev, last_schedule_time = self.get_prev_and_most_recent(schedule, datetime.timedelta(minutes=-3))
        cj = self.create_cronjob_with_schedule(schedule, last_schedule_time)
        cj.spec.suspend = True
        self.assertFalse(cronjob_stuck(cj, curr_time=prev))

    def test_cron_job_recreation(self):
        """Test that recreated cron jobs are deleted then created"""
        name = 'test_cron_job'
        namespace = 'test'
        schedule = '*/1 * * * *'
        prev, last_schedule_time = self.get_prev_and_most_recent(schedule, datetime.timedelta(minutes=-3))
        cj = self.create_cronjob_with_schedule(schedule, last_schedule_time, name=name, namespace=namespace)
        recreate_cronjob(self.mock_batch_api_client, cj)
        self.mock_batch_api_client.delete_namespaced_cron_job.assert_called_once_with(name, namespace)
        self.mock_batch_api_client.create_namespaced_cron_job.assert_called_once_with(namespace, cj)

    def test_stuck_cron_jobs_recreated(self):
        """Test that stuck cronjobs are recreated"""
        name = 'test_cron_job'
        namespace = 'test'
        schedule = '*/1 * * * *'
        prev, last_schedule_time = self.get_prev_and_most_recent(schedule, datetime.timedelta(minutes=-3))
        cj = self.create_cronjob_with_schedule(schedule, last_schedule_time, name=name, namespace=namespace)
        self.mock_batch_api_client.list_namespaced_cron_job.return_value.items = [cj]
        with patch('sat.cronjob.cronjob_stuck', return_value=True) as mock_cronjob_stuck:
            recreate_namespaced_stuck_cronjobs(self.mock_batch_api_client, namespace)
            mock_cronjob_stuck.assert_called_once_with(cj)
        self.mock_batch_api_client.delete_namespaced_cron_job.assert_called_once_with(name, namespace)
        self.mock_batch_api_client.create_namespaced_cron_job.assert_called_once_with(namespace, cj)

    def test_normal_cron_jobs_left_alone(self):
        """Test that non-stuck cronjobs are not recreated"""
        name = 'test_normal_cron_job'
        namespace = 'test'
        schedule = '*/1 * * * *'
        prev, last_schedule_time = self.get_prev_and_most_recent(schedule, datetime.timedelta(seconds=-30))
        cj = self.create_cronjob_with_schedule(schedule, last_schedule_time, name=name, namespace=namespace)
        self.mock_batch_api_client.list_namespaced_cron_job.return_value.items = [cj]
        with patch('sat.cronjob.cronjob_stuck', return_value=False) as mock_cronjob_stuck:
            recreate_namespaced_stuck_cronjobs(self.mock_batch_api_client, namespace)
            mock_cronjob_stuck.assert_called_once_with(cj)
        self.mock_batch_api_client.delete_namespaced_cron_job.assert_not_called()
        self.mock_batch_api_client.create_namespaced_cron_job.assert_not_called()
