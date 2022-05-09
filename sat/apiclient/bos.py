"""
Client for querying the Boot Orchestration Service (BOS) API

(C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP.

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
import logging

from sat.apiclient.gateway import APIError, APIGatewayClient
from sat.config import get_config_value

LOGGER = logging.getLogger(__name__)


class BOSClientCommon(APIGatewayClient):
    """Base class for BOS functionality common between v1 and v2.

    This class should not be instantiated directly; instead, the
    `BOSClientCommon.get_bos_client()` static method should be used to
    dynamically create a client object for the correct BOS version.
    """

    base_resource_path = 'bos/'

    def create_session(self, session_template, operation, limit=None):
        """Create a BOS session from a session template with an operation.

        Args:
            session_template (str): the name of the session template from which
                to create the session.
            operation (str): the operation to create the session with. Can be
                one of boot, configure, reboot, shutdown.
            limit (str): a limit string to pass through to BOS as the `limit`
                parameter in the POST payload when creating the BOS session

        Returns:
            The response from the POST to 'session'.

        Raises:
            APIError: if the POST request to create the session fails.
        """
        request_body = {
            'templateUuid': session_template,
            'operation': operation
        }

        if limit:
            request_body['limit'] = limit

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

    def get_session_template(self, session_template_name):
        """Get a specific BOS session template.

        Args:
            session_template_name (str): name of the session template to
                retrieve

        Returns:
            dict: the session template

        Raises:
            APIError: if the GET request to retrieve the session template fails
                or the response JSON cannot be parsed
        """
        try:
            return self.get('sessiontemplate', session_template_name).json()
        except APIError as err:
            raise APIError(f'Failed to get BOS session template: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from BOS when '
                           f'getting session template: {err}')

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

    @staticmethod
    def get_bos_client(session, **kwargs):
        """Instantiate a BOSVxClient for the given API version.

        Args:
            session (SATSession): session object to pass through to the client

        Additional kwargs are passed through to the underlying BOSVxClient
        constructor.

        Returns:
            An instance of a subclass of `BOSClientCommon`.

        Raises:
            ValueError: if the given version string is not valid
        """
        version = get_config_value('bos.api_version')

        bos_client_cls = {
            'v1': BOSV1Client,
            'v2': BOSV2Client,
        }.get(version)

        if bos_client_cls is None:
            raise ValueError(f'Invalid BOS API version "{version}"')

        return bos_client_cls(session, **kwargs)


class BOSV1Client(BOSClientCommon):
    base_resource_path = 'bos/v1/'


class BOSV2Client(BOSClientCommon):
    base_resource_path = f'bos/v2/'
