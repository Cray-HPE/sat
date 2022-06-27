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
API Client for the Fox service, which provides indirect access to HMJTD.
"""

import json
import logging

from sat.apiclient.gateway import APIError, APIGatewayClient


LOGGER = logging.getLogger(__name__)


class FoxClient(APIGatewayClient):
    base_resource_path = 'fox/v1/'

    def initiate_diag(self, xnames, diag_command, diag_args):
        """Initiate a job to run a diagnostic on a list of xnames.

        Args:
            xnames (list): list of xnames for which to run diagnostics
            diag_command (str): command name to run, e.g. runDiagPower
            diag_args (list): command-line arguments to pass to the command

        Returns:
            The ID of the job returned from Fox.

        Raises:
            APIError: if the Fox API returned an error
            APIError: if the Fox API returned an invalid response, for example
                missing a key or invalid JSON.
        """
        request_body = {
            'xnames': xnames,
            'jobName': diag_command,
            'options': ' '.join(diag_args)
        }

        try:
            resp_text = self.post('jobpool', json=request_body).text
        except APIError as err:
            raise APIError(f'Unable to initiate diagnostics for xname(s) {",".join(xnames)}: {err}')

        try:
            return json.loads(resp_text)['jobID']
        except ValueError as err:
            raise APIError(f'Response from Fox contained malformed data: {err}. Response: {resp_text}')
        except KeyError as err:
            raise APIError(f'Response from Fox missing expected key: {err}. Response: {resp_text}')

    def get_job_launch_status(self, job_id, xname):
        """Get the launch status of a job for one xname.

        Args:
            job_id (str): The ID of the job for which to get launch status.
            xname (str): The xname for which to get launch status.

        Returns:
            A dictionary of parsed data representing the POST response
            from HMJTD, or an empty dictionary if Fox has not yet
            received a response from HMJTD.

        Raises:
            APIError: If the Fox API returned an error
            APIError: If the fox API returned an invalid response, for example
                missing a key or invalid JSON.
            APIError: If the value of the 'launchMessage' key in the response
                from Fox could not be parsed as JSON.
        """
        try:
            resp_text = self.get(f'jobpool/{job_id}').text
        except APIError as err:
            raise APIError(f'Unable to determine launch status for {xname}: {err}')

        try:
            tasks = json.loads(resp_text)['tasks']
        except ValueError as err:
            raise APIError(f'Response from Fox contained malformed data: {err}. Response: {resp_text}')
        except KeyError as err:
            raise APIError(f'Response from Fox missing expected key: {err}. Response: {resp_text}')

        # Find the matching xname in the list of job tasks, and return the
        # value of the task's 'launchMessage', parsed as JSON. If the
        # task does not have a 'launchMessage' key, return an empty dict.
        for task in tasks:
            if task.get('xname') == xname:
                try:
                    if 'launchMessage' in task:
                        return json.loads(task['launchMessage'])
                    else:
                        return {}
                except (TypeError, ValueError) as err:
                    raise APIError(
                        f'Fox response contained malformed data from '
                        f'HMJTD: {err}. Data: {task.get("launchMessage")}'
                    )

    def get_job_status_for_xname(self, job_id, xname):
        """Get the job status for one xname.

        Args:
            job_id (str): The ID of the job
            xname (str): The xname for which to get status.

        Returns:
            A dictionary of parsed JSON data from HMJTD, the value of the
            'message' key in the response from the FOX API.
        Raises:
            APIError: if the Fox API returned an error
            APIError: if the Fox API returned an invalid response, for example
                missing a key or invalid JSON.
            APIError: If the value of the 'message' key in the response
                from Fox could not be parsed as JSON.
        """
        try:
            resp_text = self.get(f'jobpool/{job_id}/{xname}').text
        except APIError as err:
            raise APIError(f'Unable to get job status for job {job_id} xname {xname}: {err}')

        try:
            message = json.loads(resp_text)['message']
        except ValueError as err:
            raise APIError(f'Response from Fox contained malformed data: {err}. Response: {resp_text}')
        except KeyError as err:
            raise APIError(f'Response from Fox missing expected key: {err}. Response: {resp_text}')

        try:
            return json.loads(message)
        except (TypeError, ValueError) as err:
            raise APIError(f'Fox response contained malformed data from HMJTD: {err}. Data: {message}')

    def delete_job(self, job_id):
        self.delete(f'jobpool/{job_id}')
