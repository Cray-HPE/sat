#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Client for querying the Boot Orchestration Service (BOS) API
"""
import logging

from sat.apiclient.gateway import APIError, APIGatewayClient

LOGGER = logging.getLogger(__name__)


class BOSClient(APIGatewayClient):
    base_resource_path = 'bos/v1/'

    def create_session(self, session_template, operation):
        """Create a BOS session from a session template with an operation.

        Args:
            session_template (str): the name of the session template from which
                to create the session.
            operation (str): the operation to create the session with. Can be
                one of boot, configure, reboot, shutdown.

        Returns:
            The response from the POST to 'session'.

        Raises:
            APIError: if the POST request to create the session fails.
        """
        request_body = {
            'templateUuid': session_template,
            'operation': operation
        }
        return self.post('session', json=request_body)

    def get_session_templates(self):
        """Get the BOS session templates.

        Returns:
            list of dict: the list of BOS session templates

        Raises:
            APIError: if the GET request to get session templates fails or the
                response cannot be parsed as JSON
        """
        try:
            return self.get('sessiontemplate').json()
        except APIError as err:
            raise APIError(f'Failed to get BOS session templates: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from BOS when '
                           f'getting session templates: {err}')

    def create_session_template(self, session_template_data):
        """Create a session template.

        Args:
            session_template_data (dict): the BOS session template data

        Returns:
            None

        Raises:
            APIError: if the POST request to create the session template fails
        """
        self.post('sessiontemplate', json=session_template_data)
