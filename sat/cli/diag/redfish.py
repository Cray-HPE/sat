"""
Library support for the diag subcommand.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
import json
import logging
import time
from urllib.parse import urljoin, urlunparse

import inflect
import requests



inf = inflect.engine()
LOGGER = logging.getLogger(__name__)

# API entrypoint for Redfish diag queries.
REDFISH_BASE_PATH = '/redfish/v1/'
REDFISH_CRAY_PROCESS_SCHED_PATH = urljoin(REDFISH_BASE_PATH, 'Managers/BMC/Actions/Oem/CrayProcess.Schedule')


def _request_payload(command, args):
    """Gets a dictionary which can be passed to the Redfish API to
    schedule a diagnostic.

    Args:
        command: a string which is the name of a command available
            through the Redfish API on the switch or controller.
        args: a list of arguments passed to the command.

    Returns: a dict with 'Name' mapped to `command` and 'Options'
        mapped to `args`, appropriately formatted.

    """
    payload = {'Name': command}
    if args:
        payload['Options'] = ' '.join(args)
    return payload


class DiagStatus:
    """Handles information for a running diagnostic, and keep track of its
    progress.

    Attributes of this class are set dynamically according to the data
    returned from queries to the host's Redfish API. Attribute names
    and values are set verbatim from JSON data from the host.

    Attributes:
        xname: the xname of the host on which the diagnostic is running.
        session: the HTTP session used to connect to the host.

    """
    def __init__(self, xname, username, password):
        self.xname = xname
        self.session = requests.Session()
        self.session.auth = (username, password)

    def _update_content(self, json_blob):
        """Updates the fields of this object.

        If json_blob is a valid JSON dictionary, the attributes of
        this object will be set according to the key/value pairs in
        the dictionary. Otherwise, this object will not be updated.

        Args:
            json_blob: a string containing key/value pairs which
                define the status of this diagnostic. Typically, this is
                returned from a Redfish API.

        Returns: None.
        """
        try:
            status = json.loads(json_blob)
        except ValueError:
            LOGGER.error("Received malformed response: %s", json_blob)
            raise

        if 'error' in status:
            raise KeyError(status['error']['message'])

        for key, val in status.items():
            if key.startswith("@odata"):
                setattr(self, key[1:].replace('.', '_'), val)
            else:
                setattr(self, key.lower(), val)

    @staticmethod
    def initiate_diag(xname, username, password, diag_command, diag_args):
        """Runs a diagnostic command on a physical product.

        Args:
            xname: xname of the target device for diagnostics to run.
            diag_command: string containing command name to run.
            diag_args: arguments to pass to the command.

        Returns:
            If the host indicates the diagnostic started successfully,
            a DiagStatus object which can be used to check on the status of
            the diagnostic is returned. Otherwise, None is returned.
        """
        payload = _request_payload(diag_command, diag_args)

        # TODO: Once we have an abstract way of querying the APIs, it
        # should be much simpler to either get a URL or do a query
        # directly.
        sched_url = urlunparse(('https', xname, REDFISH_CRAY_PROCESS_SCHED_PATH, '', '', ''))

        try:
            LOGGER.info("Starting diagnostic %s on %s.", diag_command, xname)

            status = DiagStatus(xname, username, password)
            resp = status.session.post(sched_url, json=payload)

            LOGGER.debug("POST %s returned %s", xname, resp.text)
            status._update_content(resp.text)
            return status

        except requests.exceptions.RequestException as exc:
            LOGGER.error("Couldn't connect to %s to initiate diagnostics; %s", xname, exc)
        except ValueError:
            LOGGER.error("Target %s returned malformed response: %s", xname, resp.text)
        except KeyError as err:  # Undefined diagnostic
            LOGGER.error("%s (%s)", err, xname)

        # Return `None` in the error case.
        return None

    def poll(self):
        """Updates the status of a running diagnostic.

        If the target can't be reached, or if it returns a malformed
        response, taskstate is set to "Exception".

        Returns: Duration of this task's execution in seconds.
        """

        LOGGER.debug("Requesting status of task %s from %s.", self.id, self.xname)
        try:
            task_status_url = urlunparse(('https', self.xname, self.odata_id,
                                          '', '', ''))
            resp = self.session.get(task_status_url)
            LOGGER.debug("GET %s returned %s", self.xname, resp.text)

            self._update_content(resp.text)
            return

        except requests.exceptions.RequestException as exc:
            LOGGER.error("Couldn't connect to %s to update status, marking as Exception; %s", self.xname, exc)
        except ValueError:
            LOGGER.error("Target %s returned malformed response '%s'; marking as Exception.", self.xname, resp.text)

        # This condition should only be reached if there was an exception.
        self.taskstate = "Exception"

    def cancel(self):
        """Deletes a diagnostic and mark it as cancelled.

        Args: None.

        Returns: None.
        """
        self.taskstate = "Cancelled"
        self.cleanup()

    def delete(self):
        """Deletes this diagnostic.

        This will stop execution and remove all trace of this task
        from the target. If the task is not found on the target, this
        method is a noop. If there is a problem connecting to the
        target, taskstate is set to "Exception."

        Returns: None.
        """
        LOGGER.debug("Attempting to delete diag %s on target %s...", self.name, self.xname)
        try:
            if hasattr(self, 'odata_id'):
                task_status_url = urlunparse(('https', self.xname, self.odata_id,
                                              '', '', ''))
                resp = self.session.delete(task_status_url)
                LOGGER.debug("DELETE %s returned %s", self.xname, resp.text)
            else:
                LOGGER.info("Tried to delete diag on %s, but it doesn't seem to exist.", self.xname)
        except requests.exceptions.RequestException as exc:
            LOGGER.error("Couldn't connect to %s to cancel/delete diagnostics, "
                         "marking as Exception. %s", self.xname, exc)
            self.taskstate = "Exception"

    @property
    def complete(self):
        """Checks if this diagnostic is complete.

        Returns: True if this diagnostic has finished running, regardless of
            whether it succeeded or not, or False otherwise.
        """
        return self.taskstate in ("Completed", "Interruped", "Killed",
                                  "Cancelled", "Exception")

    def cleanup(self):
        """Cleans up the HTTP session and removes the job from the target.

        This calls `DiagStatus.delete()` to achieve this.

        Returns: None.
        """
        self.delete()
        self.session.close()


class RunningDiagPool:
    """A bundle of running diagnostics that are to be tracked."""

    def __init__(self, xnames, diag_command, diag_args, poll_interval, timeout,
                 username, password):
        """Constructor for a RunningDiagPool.

        Args:
            xnames: a list of xnames on which the diagnostics should be run.
            diag_command: a string containing the command to run on the target.
            diag_args: a list of strings with arguments to pass to the diag
                command.
            poll_interval: an int representing minimum interval, in seconds, to
                allow between HTTP requests.
        """
        self.interval = int(poll_interval)
        self.timeout = int(timeout)
        self._diags = []
        self.starttime = time.time()
        self._last_poll = self.starttime

        for xname in xnames:
            new_diag = DiagStatus.initiate_diag(xname, username, password,
                                                diag_command, diag_args)
            if new_diag is not None:
                self._diags.append(new_diag)

    def __iter__(self):
        return iter(self._diags)

    def poll_diag_statuses(self):
        """Update the status of all diags that have been launched. If the last
        call to this function was more recent than self.interval
        seconds ago, this method is a noop.

        Returns: None.
        """
        currtime = time.time()
        if currtime - self._last_poll > self.interval:
            for diag in self._diags:
                diag.poll()

                if not diag.complete and currtime - self.starttime > self.timeout:
                    LOGGER.error("%s on %s exceeded timeout (%d %s). Cancelling.",
                                 diag.name, diag.xname,
                                 self.timeout, inf.plural("second", self.timeout))
                    diag.cancel()
            self._last_poll = currtime

    @property
    def complete(self):
        """Check if all diagnostics have completed their execution.

        Returns: True if all diagnostics in this pool have completed.
        """
        return all(diag.complete for diag in self._diags)

    @property
    def completed(self):
        yield from (diag for diag in self._diags if diag.complete)

    @property
    def not_completed(self):
        yield from (diag for diag in self._diags if not diag.complete)

    def cleanup(self):
        """Delete and cancel all running and completed tasks, and close all
        corresponding HTTP sessions.

        Returns: None.
        """
        for diag in self._diags:
            diag.cleanup()
