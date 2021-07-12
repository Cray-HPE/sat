"""
Code for handling setting BMC credentials via the SCSD API.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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
import re
import secrets

from sat.apiclient import APIError, SCSDClient
from sat.cli.bmccreds.constants import (
    BMC_USERNAME,
    RANDOM_PASSWORD_LENGTH,
    VALID_BMC_PASSWORD_CHARACTERS
)
from sat.report import Report
from sat.xname import XName


LOGGER = logging.getLogger(__name__)


class BMCCredsException(Exception):
    """An exception when setting BMC credentials fails."""


class BMCCredsManager:
    """A class that can set credentials for a set of BMCs.

    Attributes:
        password (str or NoneType): The password to use. If None, generate
            a random password.
        xnames ([str]): A list of xnames.
        domain (str): The 'reach' of random passwords, e.g. if
            domain is 'chassis', BMCs in the same chassis will
            get the same random password. If None, all BMCs across
            the system will get the same random password.
        force (bool): The value of the 'force' parameter to the SCSD
            API request. If True, SCSD will not query HSM to check
            BMC state.
        report_format (str): The format to print the report. Expected to
            be 'pretty', 'yaml', or 'json'.
    """
    NODE_BMC_XNAME_REGEX = re.compile(r'x\d+c\d+s\d+b\d+$')
    CHASSIS_BMC_XNAME_REGEX = re.compile(r'x\d+c\d+b\d+$')
    ROUTER_BMC_XNAME_REGEX = re.compile(r'x\d+c\d+r\d+b\d+$')

    def __init__(self, password, xnames, domain, force, report_format):
        self.password = password
        self.xnames = [XName(xname) for xname in xnames]
        self.domain = domain
        self.force = force
        self.report_format = report_format

    @staticmethod
    def _get_bmc_type(bmc):
        """Get the type of a given BMC using regular expressions.

        Args:
            bmc (str): The xname of the BMC.

        Returns:
            str: The type of the BMC.
        """
        if BMCCredsManager.NODE_BMC_XNAME_REGEX.match(bmc):
            return 'NodeBMC'
        if BMCCredsManager.CHASSIS_BMC_XNAME_REGEX.match(bmc):
            return 'ChassisBMC'
        if BMCCredsManager.ROUTER_BMC_XNAME_REGEX.match(bmc):
            return 'RouterBMC'
        return 'Unknown'

    @staticmethod
    def _generate_random_password_string():
        """Get a random string of letters and numbers that is RANDOM_PASSWORD_LENGTH characters long."""
        return ''.join(
            secrets.choice(VALID_BMC_PASSWORD_CHARACTERS) for _ in range(RANDOM_PASSWORD_LENGTH)
        )

    def _create_globalcreds_request_body(self):
        """Generate a request payload for the SCSD 'globalcreds' endpoint.

        Returns:
            dict: The dictionary data that should be passed in the request
            body of a POST to /bmc/globalcreds.
        """
        return {
            'Username': BMC_USERNAME,
            'Password': self.password or self._generate_random_password_string(),
            'Targets': [str(xname) for xname in self.xnames],
            'Force': self.force
        }

    def _create_discreetcreds_request_body(self):
        """Generate a request payload for the SCSD 'discreetcreds' endpoint.

        Returns:
            dict: The dictionary data that should be passed in the request
            body of a POST to /bmc/discreetcreds.
        """
        passwords_by_xname = self._group_xname_passwords_by_domain()

        return {
            'Targets': [
                {
                    'Xname': str(xname),
                    'Creds': {
                        'Username': BMC_USERNAME,
                        'Password': password
                    },
                } for xname, password in passwords_by_xname.items()
            ],
            'Force': self.force
        }

    def _group_xname_passwords_by_domain(self):
        """Create a map of xnames to their randomly-generated passwords.

        Returns:
            dict: A dictionary of xnames to passwords.

        Raises:
            BMCCredsException: if unable to get chassis/cabinet name for
                a given xname.
        """
        if self.domain in ['cabinet', 'chassis']:
            domain_passwords = {}
            passwords_by_xname = {}
            for xname in self.xnames:
                ancestor_name = xname.get_cabinet() if self.domain == 'cabinet' else xname.get_chassis()
                if not ancestor_name.xname_str:
                    raise BMCCredsException(
                        f'Unable to determine {self.domain} xname for xname {xname}'
                    )
                if ancestor_name not in domain_passwords:
                    domain_passwords[ancestor_name] = self._generate_random_password_string()
                passwords_by_xname[xname] = domain_passwords[ancestor_name]
        else:
            passwords_by_xname = {
                xname: self._generate_random_password_string() for xname in self.xnames
            }

        return passwords_by_xname

    @staticmethod
    def print_report(response, password_type, password_domain, report_format):
        """Print a report from SCSD API response.

        Args:
            response (requests.models.Response): The response from the SCSD API.
            password_type (str): The type of password that was set, e.g.
                'User' or 'Random'
            password_domain (str): The domain of the password that was set, e.g.
                'chassis', 'cabinet', 'bmc' or 'system'.
            report_format (str): The format to print the report. Expected to
                be 'pretty', 'yaml', or 'json'.

        Returns:
            None
        """
        try:
            response_targets = response.json()['Targets']
        except ValueError as err:
            raise BMCCredsException(
                f'Unable to parse API response ("{response.text}") as JSON: {err}'
            )
        except KeyError as err:
            raise BMCCredsException(
                f'Missing expected key from API response: {err}'
            )

        report = Report(['xname', 'Type', 'Password Type', 'Status Code', 'Status Message'])
        for target in response_targets:
            try:
                report.add_row([
                    target['Xname'],
                    BMCCredsManager._get_bmc_type(target['Xname']),
                    f'{password_type}, domain: {password_domain}',
                    target['StatusCode'],
                    target['StatusMsg']
                ])
            except KeyError as err:
                LOGGER.error('Missing expected key from target (%s): %s', target, err)

        if report_format == 'yaml':
            print(report.get_yaml())
        elif report_format == 'json':
            print(report.get_json())
        else:
            print(report)

    def set_bmc_passwords(self, session):
        """Send a request to the SCSD API to set BMC passwords.

        Args:
            session (SATSession): The session with which to initialize
                SCSDClient.

        Returns:
            None

        Raises:
            BMCCredsException: if setting credentials fails.
            BMCCredsException: if printing the API response fails.
        """
        scsd_client = SCSDClient(session)
        api_type = (
            'globalcreds' if self.password or self.domain not in ['cabinet', 'chassis', 'bmc'] else 'discreetcreds'
        )
        if api_type == 'globalcreds':
            request_body = self._create_globalcreds_request_body()
        else:
            request_body = self._create_discreetcreds_request_body()
        try:
            response = scsd_client.post('bmc', api_type, json=request_body)
            self.print_report(
                response, 'User' if self.password else 'Random', self.domain or 'system', self.report_format
            )
        except APIError as err:
            raise BMCCredsException(
                f'Failed to update BMC credentials due to an error from the SCSD API: {err}'
            )
