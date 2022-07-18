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
Support for interacting with the Fox API.
"""

import inflect
import logging
import time

from sat.apiclient import APIError
from sat.session import SATSession
from sat.apiclient import FoxClient

inf = inflect.engine()

LOGGER = logging.getLogger(__name__)


class DiagStatus:
    """Handles information for a running diagnostic, and keep track of its
    progress.

    Attributes of this class are set dynamically according to the data
    returned from queries to the host's Redfish API. Attribute names
    and values are set verbatim from JSON data from the host.

    Attributes:
        xname: the xname of the host on which the diagnostic is running.
        taskstate: The state of this diag. Set dynamically by update_content()
    """

    def __init__(self, xname):
        self.xname = xname
        self.taskstate = None

    def update_content(self, status):
        """Update the fields of this object.

        If json_blob is a valid JSON dictionary, the attributes of
        this object will be set according to the key/value pairs in
        the dictionary. Otherwise, this object will not be updated.

        Args:
            status: a dict containing key/value pairs which
                define the status of this diagnostic. This is
                returned indirectly from the Redfish API.

        Returns: None.
        """
        if 'error' in status:
            LOGGER.error(
                'Error on %s: %s', self.xname, status['error'].get('message', 'Unknown error')
            )
            self.taskstate = 'Exception'
            return

        for key, val in status.items():
            if key.startswith("@odata"):
                setattr(self, key[1:].replace('.', '_'), val)
            else:
                setattr(self, key.lower(), val)

    @property
    def complete(self):
        """bool: True if this diagnostic has finished running, regardless of
        whether it succeeded or not, or False otherwise."""
        return self.taskstate in ("Completed", "Interrupted", "Killed",
                                  "Cancelled", "Exception", "Timed Out")

    @property
    def launched(self):
        """bool: True if this diagnostic has been launched."""
        return self.taskstate is not None


class RunningDiagPool:
    """A bundle of running diagnostics that are to be tracked."""

    def __init__(self, xnames, diag_command, diag_args, poll_interval, timeout):
        """Constructor for a RunningDiagPool.

        The RunningDiagPool constructor initiates diagnostics by making a
        request to the Fox API.

        Args:
            xnames (list): xnames on which the diagnostics should be run.
            diag_command (str): the command to run on the target.
            diag_args (list): a list of strings with arguments to pass to the
                diag command.
            poll_interval (int): minimum interval, in seconds, to allow between
                HTTP requests.
            timeout (int): maximum time, in seconds, to wait for a diag to
                complete or to wait for a diag to launch.

        Raises:
            APIError: if launching the diagnostic fails.
        """
        self.interval = poll_interval
        self.timeout = timeout
        self._completed_diags = []
        self.starttime = time.time()
        self._last_poll = self.starttime
        self.diag_command = diag_command
        self.fox_client = FoxClient(SATSession())

        self.job_id = self.fox_client.initiate_diag(xnames, diag_command, diag_args)
        self._diags = [DiagStatus(xname) for xname in xnames]

    def __iter__(self):
        return iter(self._diags)

    def poll_until_launched(self):
        """Continually poll until all diagnostics have launched.

        This function also filters out diagnostics which did not launch.

        Returns: None
        """
        while not self.all_launched:
            self.poll_diag_launch_statuses()
            time.sleep(0.1)
        # discard diagnostics that did not launch
        self._diags = [diag for diag in self._diags if diag.taskstate == 'New']

    def poll_until_complete(self):
        """Continually poll until all diagnostics have completed.

        Returns: None
        """
        while not self.complete:
            self.poll_diag_statuses()
            time.sleep(0.1)

    def poll_diag_launch_statuses(self):
        """Check the launch status of the diags. If the last call to this
        function was more recent than self.interval seconds ago, this method
        is a noop.

        Returns: None.
        """
        currtime = time.time()
        if currtime - self._last_poll > self.interval:
            for diag in self._diags:
                if diag.taskstate is not None:
                    continue
                try:
                    diag.update_content(self.fox_client.get_job_launch_status(self.job_id, diag.xname))
                except APIError as err:
                    LOGGER.error(err)
                    diag.taskstate = 'Exception'
                    continue
                if currtime - self.starttime > self.timeout:
                    LOGGER.error("%s on %s exceeded launch timeout (%d %s).",
                                 self.diag_command, diag.xname,
                                 self.timeout, inf.plural("second", self.timeout))
                    diag.taskstate = 'Timed Out'
            self._last_poll = currtime

    def poll_diag_statuses(self):
        """Update the status of all diags that have been launched. If the last
        call to this function was more recent than self.interval seconds ago,
        this method is a noop.

        Returns: None.
        """
        currtime = time.time()
        if currtime - self._last_poll > self.interval:
            for diag in self._diags:
                if diag.complete:
                    continue
                try:
                    diag.update_content(self.fox_client.get_job_status_for_xname(self.job_id, diag.xname))
                except APIError as err:
                    LOGGER.error(err)
                    diag.taskstate = 'Exception'
                    continue
                if currtime - self.starttime > self.timeout:
                    LOGGER.error("%s on %s exceeded timeout (%d %s).",
                                 self.diag_command, diag.xname,
                                 self.timeout, inf.plural("second", self.timeout))
                    diag.taskstate = 'Timed Out'

            self._last_poll = currtime

    def cleanup(self):
        """Delete the Fox Job."""
        try:
            self.fox_client.delete_job(self.job_id)
        except APIError as err:
            LOGGER.error('Failed to delete %s: %s', self.job_id, err)

    @property
    def complete(self):
        """bool: True if all diagnostics in this pool have completed."""
        return all(diag.complete for diag in self._diags)

    @property
    def all_launched(self):
        """bool: True if all diagnostics in this pool have been launched."""
        return all(diag.launched for diag in self._diags)

    @property
    def completed(self):
        yield from (diag for diag in self._diags if diag.complete)

    @property
    def not_completed(self):
        yield from (diag for diag in self._diags if not diag.complete)
