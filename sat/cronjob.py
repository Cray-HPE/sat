#
# MIT License
#
# (C) Copyright 2020-2023 Hewlett Packard Enterprise Development LP
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
Utilities for handling Kubernetes cronjobs.
"""
import copy
import datetime
import logging

import croniter
from dateutil.tz import tzutc
from kubernetes.client import ApiException

LOGGER = logging.getLogger(__name__)


def cronjob_stuck(cronjob, curr_time=None):
    """Determine if a cronjob is not being scheduled.

    A cronjob is considered "stuck" if it is not suspended, but its last
    scheduled time is before the expected most recent scheduled time,
    based on its cron schedule. If the job is suspended, we expect it not
    to be scheduled, so we don't treat it as "stuck".

    Args:
        cronjob (V1CronJob): the cron job object from the Kubernetes API
        curr_time (datetime): if not None, use this as the current time.
            Mostly used for testing.

    Returns:
        Whether the cronjob's last scheduled job was before the
        calculated most recent scheuled time based on the cron
        schedule string for the cron job.
    """
    if cronjob.spec.suspend:
        return False
    it = croniter.croniter(cronjob.spec.schedule)
    if curr_time is not None:
        it.set_current(curr_time)
    if cronjob.status.last_schedule_time is None:
        last_sched = cronjob.metadata.creation_timestamp
    else:
        last_sched = cronjob.status.last_schedule_time
    prev_expected_sched = datetime.datetime.fromtimestamp(it.get_prev(), tz=tzutc())
    return last_sched < prev_expected_sched


def recreate_cronjob(batch_api, cronjob):
    """Delete and recreate a cronjob in Kubernetes.

    Args:
        batch_api (kubernetes.client.BatchV1Api): the Kubernetes API client
        cronjob (V1CronJob): the cronjob object representing the cronjob to be recreated

    Returns:
        V1CronJob: the newly created cronjob

    Raises:
        kubernetes.client.ApiException: if a problem occurs while communicating
            with the Kubernetes API
    """
    cronjob = copy.deepcopy(cronjob)
    name = cronjob.metadata.name
    namespace = cronjob.metadata.namespace
    cronjob.metadata.resource_version = None
    try:
        batch_api.delete_namespaced_cron_job(name, namespace)
    except ApiException as err:
        if err.status != 404:
            raise

    return batch_api.create_namespaced_cron_job(namespace, cronjob)


def recreate_namespaced_stuck_cronjobs(batch_api, namespace):
    """Find cronjobs that are not being scheduled and recreate them.

    Args:
        batch_api (kubernetes.client.BatchV1Api): the Kubernetes API client
        namespace (str): the namespace to search for cronjobs

    Returns:
        None

    Raises:
        kubernetes.client.ApiException: if the Kubernetes API can't be accessed
    """
    for cronjob in batch_api.list_namespaced_cron_job(namespace).items:
        if cronjob_stuck(cronjob):
            LOGGER.warning('Jobs for cronjob "%s" in namespace "%s" do not appear to be '
                           'scheduled on time according to the cron job\'s schedule; '
                           'recreating cron job.',
                           cronjob.metadata.name, cronjob.metadata.namespace)
            try:
                recreate_cronjob(batch_api, cronjob)
            except ApiException as err:
                LOGGER.warning('An error occurred while re-creating cronjob "%s" in namespace "%s": %s',
                               cronjob.metadata.name, cronjob.metadata.namespace, err)
