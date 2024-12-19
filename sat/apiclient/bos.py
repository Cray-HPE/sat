#
# MIT License
#
# (C) Copyright 2019-2024 Hewlett Packard Enterprise Development LP
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

from csm_api_client.service.gateway import APIError, APIGatewayClient

from sat.config import get_config_value

LOGGER = logging.getLogger(__name__)


class BOSClientCommon(APIGatewayClient):
    """Base class for BOS functionality common between v1 and v2.

    This class should not be instantiated directly; instead, the
    `BOSClientCommon.get_bos_client()` static method should be used to
    dynamically create a client object for the correct BOS version.

    All BOSClientCommon subclasses should have a `session_template_path` class
    attribute, in addition to the standard `base_resource_path` class
    attribute. `session_template_path` should point to the API endpoint for
    querying session templates.
    """

    def get_session_templates(self):
        """Get the BOS session templates.

        Returns:
            list of dict: the list of BOS session templates

        Raises:
            APIError: if the GET request to get session templates fails or the
                response cannot be parsed as JSON
        """
        try:
            return self.get(self.session_template_path).json()
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
            return self.get(self.session_template_path, session_template_name).json()
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
            APIError: if the request to create the session template fails,
                or if session_template_data is invalid
        """
        self.post(self.session_template_path, json=session_template_data)

    @staticmethod
    def get_bos_client(session, version=None, **kwargs):
        """Instantiate a BOSVxClient for the given API version.

        Args:
            session (SATSession): session object to pass through to the client
            version (Optional[str]): 'v1' or 'v2', or None. If None, the config
                file and command line are consulted to determine the BOS version in
                use.

        Additional kwargs are passed through to the underlying BOSVxClient
        constructor.

        Returns:
            An instance of a subclass of `BOSClientCommon`.

        Raises:
            ValueError: if the given version string is not valid
        """
        version = version or get_config_value('bos.api_version')

        bos_client_cls = {
            'v1': BOSV1Client,
            'v2': BOSV2Client,
        }.get(version)

        if bos_client_cls is None:
            raise ValueError(f'Invalid BOS API version "{version}"')

        return bos_client_cls(session, **kwargs)

    def get_session(self, session_id):
        """Get information about a given session.

        Args:
            session_id (str): the ID of the session

        Returns:
            dict: session information for the given session from BOS

        Raises:
            APIError: if there is a problem retrieving the session from BOS, or
                if the returned JSON is invalid.
        """

        try:
            return self.get(self.session_path, session_id).json()
        except APIError as err:
            raise APIError(f'Failed to get BOS session {session_id}: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from BOS when '
                           f'getting session {session_id}: {err}')

    def get_sessions(self):
        """Get a list of all sessions.

        Returns:
            list of dict: session information for all sessions in BOS

        Raises:
            APIError: if there is a problem retrieving sessions from BOS, or if
                the returned JSON is invalid.
        """
        try:
            return self.get(self.session_path).json()
        except APIError as err:
            raise APIError(f'Failed to get BOS sessions: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from BOS when '
                           f'getting sessions: {err}')


class BOSV1Client(BOSClientCommon):
    base_resource_path = 'bos/v1/'
    session_template_path = 'sessiontemplate'
    session_path = 'session'

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

        return self.post(self.session_path, json=request_body)


class BOSV2Client(BOSClientCommon):
    base_resource_path = 'bos/v2/'
    session_template_path = 'sessiontemplates'
    session_path = 'sessions'

    def create_session(self, session_template, operation, limit=None, stage=False):
        """Create a BOS session from a session template with an operation.

        Args:
            session_template (str): the name of the session template from which
                to create the session.
            operation (str): the operation to create the session with. Can be
                one of boot, configure, reboot, shutdown.
            limit (str): a limit string to pass through to BOS as the `limit`
                parameter in the POST payload when creating the BOS session
            stage (bool): if True, create a 'staged' BOS session, which updates
                components' staged state rather than their desired state.

        Returns:
            The response from the POST to 'sessions'.

        Raises:
            APIError: if the POST request to create the session fails.
        """
        request_body = {
            'template_name': session_template,
            'operation': operation,
            'stage': stage
        }

        if limit:
            request_body['limit'] = limit

        return self.post(self.session_path, json=request_body)

    def create_session_template(self, session_template_data):
        name = session_template_data.get('name')
        if not name:
            raise APIError('"name" key missing from session template data')
        del session_template_data['name']

        self.put(self.session_template_path, name, json=session_template_data)

    def get_components(self):
        """Get the full collection of components from BOS v2.

        Returns:
            list of dict: components managed by BOS v2

        Raises:
            APIError: if an error occurs while retrieving components from BOS
                v2
        """
        try:
            return self.get('components').json()
        except APIError as err:
            raise APIError(f'Failed to get BOS components: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON in response from BOS when '
                           f'getting components: {err}')
