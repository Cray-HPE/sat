#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
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
OAuth2 authentication support.
"""

import logging

from csm_api_client.session import UserSession

from sat.config import get_config_value
from sat.util import get_resource_filename


LOGGER = logging.getLogger(__name__)


class SATSession(UserSession):
    """Subclass of the csm-api-client UserSession which follows the config file"""

    def __init__(self, no_unauth_warn=False):
        """Initialize a SATSession.

        Args:
            no_unauth_warn (bool): Suppress session-is-not-authorized warning.
                used when fetching a new token with "sat auth".
        """

        host = get_config_value('api_gateway.host')
        cert_verify = get_config_value('api_gateway.cert_verify')
        username = get_config_value('api_gateway.username')

        token_filename = get_config_value('api_gateway.token_file')
        if token_filename == '':
            host_as_filename = host.replace('-', '_').replace('.', '_')
            token_filename = get_resource_filename(
                '{}.{}.json'.format(host_as_filename, username), 'tokens')

        super().__init__(host, cert_verify, username, token_filename)

        if not (self.token or no_unauth_warn):
            LOGGER.warning('Session is not authenticated. ' +
                           'Username is "{}". '.format(username) +
                           'Obtain a token with "auth" ' +
                           'subcommand, or use --token-file on the command line.')
