#
# MIT License
#
# (C) Copyright 2021, 2024 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.bmccreds.creds_manager module.
"""

import logging
import unittest
from unittest.mock import call, Mock, patch

from sat.apiclient import APIError
from sat.cli.bmccreds.constants import BMC_USERNAME, RANDOM_PASSWORD_LENGTH, VALID_CHAR_SETS_STRING
from sat.cli.bmccreds.creds_manager import BMCCredsException, BMCCredsManager
from tests.common import ExtendedTestCase


class TestBMCCredsManager(unittest.TestCase):
    """Tests for BMCCredsManager"""

    def setUp(self):
        """Set up tests."""
        self.mock_scsd_client_cls = patch('sat.cli.bmccreds.creds_manager.SCSDClient').start()
        self.mock_scsd_client = self.mock_scsd_client_cls.return_value
        self.mock_print_report = patch.object(BMCCredsManager, 'print_report').start()

        self.user_password = 'sWoRdp45'
        self.xnames = [
            'x3000c0s1b0', 'x3000c0s2b0', 'x3000c0r1b0', 'x3000c1s1b0', 'x9000c0s1b0'
        ]
        self.domain = None
        self.force = False
        self.report_format = 'pretty'
        self.length = RANDOM_PASSWORD_LENGTH
        self.allowed_chars = VALID_CHAR_SETS_STRING

        self.random_passwords = [
            BMCCredsManager._generate_random_password_string(self)
            for _ in range(len(self.xnames))
        ]
        self.generate_random_password_string = patch.object(
            BMCCredsManager, '_generate_random_password_string', side_effect=self.random_passwords
        ).start()

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    def get_creds_manager(self):
        """Create a BMCCredsManager."""
        return BMCCredsManager(
            password=self.user_password,
            xnames=self.xnames,
            domain=self.domain,
            force=self.force,
            report_format=self.report_format,
            length=self.length,
            allowed_chars=self.allowed_chars
        )

    def test_set_xnames_with_password(self):
        """Test setting xnames with a user-supplied password."""
        creds_manager = self.get_creds_manager()
        creds_manager.set_bmc_passwords(session=Mock())
        expected_json = {
            'Username': BMC_USERNAME,
            'Password': self.user_password,
            'Targets': self.xnames,
            'Force': self.force
        }
        self.mock_scsd_client.post.assert_called_once_with(
            'bmc', 'globalcreds', json=expected_json
        )
        self.mock_print_report.assert_called_once_with(
            self.mock_scsd_client.post.return_value,
            'User',
            'system',
            'pretty'
        )

    def test_set_xnames_with_report_format(self):
        """Test setting xnames with a user-supplied password and yaml format."""
        self.report_format = 'yaml'
        creds_manager = self.get_creds_manager()
        creds_manager.set_bmc_passwords(session=Mock())
        expected_json = {
            'Username': BMC_USERNAME,
            'Password': self.user_password,
            'Targets': self.xnames,
            'Force': self.force
        }
        self.mock_scsd_client.post.assert_called_once_with(
            'bmc', 'globalcreds', json=expected_json
        )
        self.mock_print_report.assert_called_once_with(
            self.mock_scsd_client.post.return_value,
            'User',
            'system',
            'yaml'
        )

    def test_set_xnames_with_random_password(self):
        """Test setting xnames with a random password."""
        self.user_password = None
        creds_manager = self.get_creds_manager()
        creds_manager.set_bmc_passwords(session=Mock())
        expected_json = {
            'Username': BMC_USERNAME,
            'Password': self.random_passwords[0],
            'Targets': self.xnames,
            'Force': self.force
        }
        self.mock_scsd_client.post.assert_called_once_with(
            'bmc', 'globalcreds', json=expected_json
        )
        self.mock_print_report.assert_called_once_with(
            self.mock_scsd_client.post.return_value,
            'Random',
            'system',
            'pretty'
        )

    def test_set_xnames_with_random_password_and_system_domain(self):
        """Test setting xnames with a random password."""
        self.user_password = None
        self.domain = 'system'
        expected_json = {
            'Username': BMC_USERNAME,
            'Password': self.random_passwords[0],
            'Targets': self.xnames,
            'Force': self.force
        }
        creds_manager = self.get_creds_manager()
        creds_manager.set_bmc_passwords(session=Mock())
        self.mock_scsd_client.post.assert_called_once_with(
            'bmc', 'globalcreds', json=expected_json
        )
        self.mock_print_report.assert_called_once_with(
            self.mock_scsd_client.post.return_value,
            'Random',
            'system',
            'pretty'
        )

    def test_set_xnames_with_random_password_and_bmc_domain(self):
        """Test setting xnames with a different random password for each bmc."""
        self.user_password = None
        self.domain = 'bmc'
        expected_json = {
            'Targets': [{
                'Xname': xname,
                'Creds': {
                    'Username': BMC_USERNAME,
                    'Password': self.random_passwords[i]}
            } for i, xname in enumerate(self.xnames)],
            'Force': False
        }
        creds_manager = self.get_creds_manager()
        creds_manager.set_bmc_passwords(session=Mock())
        self.mock_scsd_client.post.assert_called_once_with(
            'bmc', 'discreetcreds', json=expected_json
        )
        self.mock_print_report.assert_called_once_with(
            self.mock_scsd_client.post.return_value,
            'Random',
            'bmc',
            'pretty'
        )

    def test_set_xnames_with_random_password_and_cabinet_domain(self):
        """Test setting xnames with a random password that is shared within a cabinet."""
        self.user_password = None
        self.domain = 'cabinet'

        # Expect all x3000 xnames to have one password, all others to have another.
        def expected_password_for_xname(xname):
            if xname.startswith('x3000'):
                return self.random_passwords[0]
            return self.random_passwords[1]

        expected_json = {
            'Targets': [{
                'Xname': xname,
                'Creds': {
                    'Username': BMC_USERNAME,
                    'Password': expected_password_for_xname(xname)}
            } for xname in self.xnames],
            'Force': False
        }
        creds_manager = self.get_creds_manager()
        creds_manager.set_bmc_passwords(session=Mock())
        self.mock_scsd_client.post.assert_called_once_with(
            'bmc', 'discreetcreds', json=expected_json
        )
        self.mock_print_report.assert_called_once_with(
            self.mock_scsd_client.post.return_value,
            'Random',
            'cabinet',
            'pretty'
        )

    def test_set_xnames_with_random_password_and_chassis(self):
        """Test setting xnames with a random password."""
        self.user_password = None
        self.domain = 'chassis'

        # Expect all x3000 xnames to have one password, all others to have another.
        def expected_password_for_xname(xname):
            if xname.startswith('x3000c0'):
                return self.random_passwords[0]
            elif xname.startswith('x3000c1'):
                return self.random_passwords[1]
            elif xname.startswith('x9000'):
                return self.random_passwords[2]

        expected_json = {
            'Targets': [{
                'Xname': xname,
                'Creds': {
                    'Username': BMC_USERNAME,
                    'Password': expected_password_for_xname(xname)}
            } for xname in self.xnames],
            'Force': False
        }
        creds_manager = self.get_creds_manager()
        creds_manager.set_bmc_passwords(session=Mock())
        self.mock_scsd_client.post.assert_called_once_with(
            'bmc', 'discreetcreds', json=expected_json
        )
        self.mock_print_report.assert_called_once_with(
            self.mock_scsd_client.post.return_value,
            'Random',
            'chassis',
            'pretty'
        )

    def test_set_random_bmc_password_invalid_xname(self):
        """Test attempting to set passwords on invalid xnames cannot group by domain."""
        self.xnames = ['x']
        self.user_password = None
        self.domain = 'chassis'
        expected_error = 'Unable to determine chassis xname for xname x'
        creds_manager = self.get_creds_manager()
        with self.assertRaisesRegex(BMCCredsException, expected_error):
            creds_manager.set_bmc_passwords(session=Mock())

    def test_set_bmc_passwords_api_error(self):
        """Test an APIError from the SCSD client is handled."""
        self.mock_scsd_client.post.side_effect = APIError('API failed')
        expected_error = 'Failed to update BMC credentials due to an error from the SCSD API: API failed'
        creds_manager = self.get_creds_manager()
        with self.assertRaisesRegex(BMCCredsException, expected_error):
            creds_manager.set_bmc_passwords(session=Mock())


class TestBMCCredsManagerPrintReport(ExtendedTestCase):
    """Tests for BmCCredsManager.print_report"""
    def setUp(self):
        """Set up tests."""
        self.mock_print = patch('builtins.print').start()
        self.mock_report_cls = patch('sat.cli.bmccreds.creds_manager.Report').start()
        self.mock_report = self.mock_report_cls.return_value
        self.mock_print = patch('builtins.print').start()
        self.mock_response_json = {
            'Targets': [
                {
                    'Xname': 'x3000c0s1b0',
                    'StatusCode': 200,
                    'StatusMsg': 'OK'
                },
                {
                    'Xname': 'x3000c0s2b0',
                    'StatusCode': 200,
                    'StatusMsg': 'OK',
                },
                {
                    'Xname': 'x3000c0r1b0',
                    'StatusCode': 204,
                    'StatusMsg': 'No Content',
                },
            ]
        }
        self.mock_response = Mock()
        self.mock_response.json.return_value = self.mock_response_json

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    def assert_report(self, rows, report_format):
        """Assert that a Report was created and printed with the right content and format."""
        self.mock_report_cls.assert_called_once_with(
            ['xname', 'Type', 'Password Type', 'Status Code', 'Status Message'],
            print_format=report_format
        )
        self.assertEqual(
            [call(row) for row in rows],
            self.mock_report.add_row.mock_calls
        )
        self.mock_print.assert_called_once_with(self.mock_report)

    def test_print_default_report(self):
        """Test printing a default report."""
        BMCCredsManager.print_report(self.mock_response, 'User', 'system', 'pretty')
        self.assert_report(
            rows=[
                ['x3000c0s1b0', 'NodeBMC', 'User, domain: system', 200, 'OK'],
                ['x3000c0s2b0', 'NodeBMC', 'User, domain: system', 200, 'OK'],
                ['x3000c0r1b0', 'RouterBMC', 'User, domain: system', 204, 'No Content']
            ],
            report_format='pretty'
        )

    def test_print_report_missing_keys(self):
        """Test printing a report when one of the rows is missing some data."""
        del self.mock_response_json['Targets'][2]['Xname']
        with self.assertLogs(level=logging.ERROR) as logs:
            BMCCredsManager.print_report(self.mock_response, 'User', 'system', 'pretty')
        self.assert_report(
            rows=[
                ['x3000c0s1b0', 'NodeBMC', 'User, domain: system', 200, 'OK'],
                ['x3000c0s2b0', 'NodeBMC', 'User, domain: system', 200, 'OK'],
            ],
            report_format='pretty'
        )
        self.assert_in_element(
            'Missing expected key from target ({\'StatusCode\': 204, \'StatusMsg\': \'No Content\'}): \'Xname\'',
            logs.output
        )

    def test_print_report_with_yaml_format(self):
        """Test printing a report in YAML format."""
        BMCCredsManager.print_report(self.mock_response, 'User', 'system', 'yaml')
        self.assert_report(
            rows=[
                ['x3000c0s1b0', 'NodeBMC', 'User, domain: system', 200, 'OK'],
                ['x3000c0s2b0', 'NodeBMC', 'User, domain: system', 200, 'OK'],
                ['x3000c0r1b0', 'RouterBMC', 'User, domain: system', 204, 'No Content']
            ],
            report_format='yaml'
        )

    def test_print_report_invalid_json_response(self):
        """Test invalid JSON is handled by print_report"""
        self.mock_response.json.side_effect = ValueError('invalid JSON')
        self.mock_response.text = '{'
        expected_error = r'Unable to parse API response \("\{"\) as JSON: invalid JSON'
        with self.assertRaisesRegex(BMCCredsException, expected_error):
            BMCCredsManager.print_report(self.mock_response, 'User', 'system', 'pretty')

    def test_set_bmc_passwords_missing_report_fields(self):
        """Test a missing top-level key is handled by print_report"""
        self.mock_response.json.return_value = {}
        expected_error = 'Missing expected key from API response: \'Targets\''
        with self.assertRaisesRegex(BMCCredsException, expected_error):
            BMCCredsManager.print_report(self.mock_response, 'User', 'system', 'pretty')


if __name__ == '__main__':
    unittest.main()
