"""
OAuth2 authentication support.

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
import os.path
import os

from oauthlib.oauth2 import (UnauthorizedClientError, MissingTokenError,
                             InvalidGrantError, LegacyApplicationClient)
from requests_oauthlib import OAuth2Session

from sat.cached_property import cached_property
from sat.config import get_config_value
from sat.util import get_resource_filename


LOGGER = logging.getLogger(__name__)


class SATSession:
    """Manage API sessions, authentication, and token storage/retrieval."""

    TOKEN_URI = '/keycloak/realms/{}/protocol/openid-connect/token'
    tenant = 'shasta'
    client_id = 'shasta'

    def __init__(self, no_unauth_warn=False):
        """Initialize a Session. Wraps an OAuth2Session.

        Parameter management. Initialization of the OAuth2Session passes to
        self.get_session().

        Args:
            no_unauth_warn (bool): Suppress session-is-not-authorized warning.
                used when fetching a new token with "sat auth".
        """

        self.host = get_config_value('api_gateway.host')
        self.cert_verify = get_config_value('api_gateway.cert_verify')
        self.username = get_config_value('api_gateway.username')

        opts = self.session_opts
        token = self.token

        client = LegacyApplicationClient(client_id=self.client_id, token=token)
        if token:
            client.parse_request_body_response(json.dumps(token))
        else:
            if not no_unauth_warn:
                LOGGER.warning('Session is not authenticated. ' +
                               'Username is "{}". '.format(self.username) +
                               'Obtain a token with "auth" ' +
                               'subcommand, or use --token-file on the command line.')

        self.session = OAuth2Session(client=client, token=token, **opts)

    @property
    def token_filename(self):
        """str: Filename of authentication token
        """

        token_filename = get_config_value('api_gateway.token_file')
        if token_filename == '':
            host_as_filename = self.host.replace('-', '_').replace('.', '_')
            token_filename = get_resource_filename(
                '{}.{}.json'.format(host_as_filename, self.username), 'tokens')

        return token_filename

    @cached_property
    def token(self):
        """dict: Deserialized authentication token.
        """

        if not os.path.exists(self.token_filename):
            return None

        try:
            with open(self.token_filename, 'r') as f:
                token = json.load(f)
                LOGGER.info('Loaded auth token from %s.', self.token_filename)

        except json.JSONDecodeError as err:
            LOGGER.error('Unable to parse token: %s.', err)
            return None

        except OSError as err:
            LOGGER.error("Unable to create token file '%s': %s", self.token_filename, err)
            return None

        return token

    def save(self):
        """Serializes an authentication token.

        Tokens are stored with read permissions revoked for anyone
        other than the user or administrator.
        """

        token = self.token

        if 'client_id' not in token:
            token['client_id'] = self.client_id

        with open(self.token_filename, 'w') as f:
            # revoke read permissions from group/other
            os.fchmod(f.fileno(), 0o600)
            json.dump(token, f)

        LOGGER.info('Saved auth token to: %s', self.token_filename)

    @property
    def token_url(self):
        return 'https://{}{}'.format(self.host, self.TOKEN_URI.format(self.tenant))

    def fetch_token(self, password):
        """Fetch a new authentication token.

        Args:
            password (str): password

        Returns:
            token (dict): Authentication token
        """

        username = self.username

        opts = dict(client_id=self.client_id, verify=self.cert_verify)
        opts.update(self.session_opts)

        try:
            self._token = self.session.fetch_token(token_url=self.token_url,
                                                   username=username, password=password, **opts)
        except (MissingTokenError, UnauthorizedClientError, InvalidGrantError) as err:
            LOGGER.error("Authorization of user '%s' failed: %s.", username, err)
            self._token = None
        else:
            LOGGER.info("Acquired new auth token for user '%s'.", username)

    @cached_property
    def session_opts(self):
        return dict(auto_refresh_url=self.token_url, token_updater=self.save,
                    auto_refresh_kwargs=dict(client_id=self.client_id))
