"""
Functionality related to the hms-discovery cronjob in k8s.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
from datetime import datetime
import logging
import warnings
from yaml import YAMLLoadWarning

from croniter import croniter
from dateutil.tz import tzutc
from kubernetes.config import ConfigException, load_kube_config
from kubernetes.client import BatchV1beta1Api
from kubernetes.client.rest import ApiException

from sat.cached_property import cached_property
from sat.waiting import Waiter

LOGGER = logging.getLogger(__name__)


class HMSDiscoveryError(Exception):
    """An error while querying or modifying the hms-discovery cronjob"""
    pass


class HMSDiscoveryCronJob:
    """An object representing the HMS Discovery cronjob in k8s."""

    # Constants for the namespace and name of the k8s cronjob.
    HMS_DISCOVERY_NAMESPACE = 'services'
    HMS_DISCOVERY_NAME = 'hms-discovery'
    FULL_NAME = f'cronjob {HMS_DISCOVERY_NAME} in namespace {HMS_DISCOVERY_NAMESPACE}'

    @cached_property
    def k8s_batch_api(self):
        """BatchV1beta1Api: the k8s batch API client

        Raises:
            HMSDiscoveryError: if there is an error loading k8s config
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            raise HMSDiscoveryError('Failed to load kubernetes config: {}'.format(err)) from err

        return BatchV1beta1Api()

    # Intentionally not cached so we can get live state
    @property
    def data(self):
        """V1beta1CronJob: the data describing the cronjob.

        Raises:
            HMSDiscoveryError: if there is an error loading k8s config or querying
                the k8s API for the suspended status of the cronjob.
        """
        try:
            return self.k8s_batch_api.read_namespaced_cron_job(self.HMS_DISCOVERY_NAME,
                                                               self.HMS_DISCOVERY_NAMESPACE)
        except ApiException as err:
            raise HMSDiscoveryError(f'Failed to get data for '
                                    f'{self.FULL_NAME}: {err}') from err

    def get_last_schedule_time(self):
        """Get the last scheduled time, i.e. the last time k8s scheduled the job.

        Returns:
            datetime: the last time the HMS discovery cronjob was scheduled, or
            None if there is no last scheduled time.

        Raises:
            HMSDiscoveryError: if there is an error loading k8s config or querying
                the k8s API for the last scheduled time of the cronjob.
        """
        return self.data.status.last_schedule_time

    def get_suspend_status(self):
        """Returns whether the hms-discovery cronjob is currently suspended or not.

        Returns:
            bool: True if the 'hms-discovery' job in the 'services' namespace is
                currently suspended and False if it is not suspended.

        Raises:
            HMSDiscoveryError: if there is an error loading k8s config or querying
                the k8s API for the suspended status of the cronjob.
        """
        return self.data.spec.suspend

    def is_active(self):
        """Returns whether there are any running jobs for this cron job.

        Returns:
            bool: True if there is a running job associated with this cron job, and False otherwise

        Raises:
            HMSDiscoveryError: if there is an error loading k8s config or querying
                the k8s API for running jobs.
        """
        return bool(self.data.status.active)

    def set_suspend_status(self, suspend_status):
        """Set the suspend status of the hms-discovery cronjob.

        Checks whether the cronjob suspend status is already in desired state before
        making the API request to set it.

        Args:
            suspend_status (bool): True to set the cronjob to a suspended state,
                False to remove the cronjob from the suspended state.

        Returns:
            None

        Raises:
            HMSDiscoveryError: if there is an error loading k8s config or querying
                or setting the suspend status of the cronjob with the k8s API.
        """
        if self.get_suspend_status() == suspend_status:
            LOGGER.info(f'The {self.FULL_NAME} is already '
                        f'{"" if suspend_status else "not "}suspended.')
            return

        operation_name = 'suspend' if suspend_status else 'resume'
        LOGGER.debug(f'Issuing request to k8s API to {operation_name} {self.FULL_NAME}.')
        patch_body = {'spec': {'suspend': suspend_status}}
        try:
            self.k8s_batch_api.patch_namespaced_cron_job(self.HMS_DISCOVERY_NAME,
                                                         self.HMS_DISCOVERY_NAMESPACE,
                                                         patch_body)
        except ApiException as err:
            raise HMSDiscoveryError(f'Failed to {operation_name} {self.FULL_NAME}: {err}') from err

        LOGGER.debug(f'Successfully issued request to k8s API to {operation_name} {self.FULL_NAME}.')

    def get_latest_next_schedule_time(self):
        """Get the latest possible next schedule time.

        This is computed by assuming the current time is when the cron job
        scheduling starts and then getting the next time it should run according
        to its cron schedule.

        Returns:
            datetime: a datetime object representing the latest possible time
                that the cronjob would be scheduled.

        Raises:
            HMSDiscoveryError: if there is an error loading k8s config or querying
                the k8s API for the schedule of the cronjob.
        """
        ci = croniter(self.data.spec.schedule, start_time=datetime.now(tz=tzutc()))
        return ci.get_next(datetime)


class HMSDiscoveryScheduledWaiter(Waiter):
    """Waiter for HMS discovery cronjob to be scheduled by k8s."""

    def __init__(self, poll_interval=5, grace_period=60):
        """Create a new HMSDiscoveryScheduledWaiter.

        Timeout is computed automatically based on the latest possible time
        that k8s would schedule the cronjob based on its configured schedule.

        Args:
            poll_interval (int): see `Waiter.__init__`
            grace_period (int): the number of seconds after the expected next
                scheduled time to wait for the job to be scheduled.

        Raises:
            HMSDiscoveryError: if there is an error querying the k8s API for the
                schedule of the cronjob.
        """
        self.hd_cron_job = HMSDiscoveryCronJob()

        # This call can raise HMSDiscoveryError
        next_time = self.hd_cron_job.get_latest_next_schedule_time()
        self.start_time = datetime.now(tz=tzutc())
        timeout = (next_time - self.start_time).seconds + grace_period

        super().__init__(timeout, poll_interval)

    def condition_name(self):
        return 'HMS Discovery Scheduled'

    def has_completed(self):
        """Return whether the HMS Discovery job has been scheduled.

        This is determined by whether its last scheduled time ever surpasses the
        time we started this waiter.
        """
        try:
            last_schedule_time = self.hd_cron_job.get_last_schedule_time()
        except HMSDiscoveryError as err:
            LOGGER.warning(f'Failed to get last schedule time: {err}')
            return False

        if not last_schedule_time:
            LOGGER.debug(f'No record of {self.hd_cron_job.FULL_NAME} being scheduled.')
            return False

        if last_schedule_time >= self.start_time:
            return True
        else:
            return False


class HMSDiscoverySuspendedWaiter(Waiter):
    """Waiter for HMS discovery cronjob to be suspended and not running.

    Specifically, the waiter checks if the the cron job is suspended, and if
    there are any k8s jobs running that were launched by the cron job.
    """

    def __init__(self, timeout, poll_interval=1, retries=0):
        self.hd_cron_job = HMSDiscoveryCronJob()
        super().__init__(timeout, poll_interval=poll_interval, retries=retries)

    def condition_name(self):
        return "HMS Discovery Suspended"

    def has_completed(self):
        return self.hd_cron_job.get_suspend_status() and not self.hd_cron_job.is_active()
