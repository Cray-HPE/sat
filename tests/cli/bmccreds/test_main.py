"""
Unit tests for the sat.cli.bmccreds.main module.

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

from argparse import ArgumentParser
import logging
from textwrap import dedent
import unittest
from unittest.mock import patch

from sat.apiclient import APIError
from sat.constants import BMC_TYPES
from sat.cli.bmccreds import parser as bmccreds_parser
from sat.cli.bmccreds.main import do_bmccreds
from sat.cli.bmccreds.constants import BMC_USERNAME, USER_PASSWORD_MAX_LENGTH
from sat.cli.bmccreds.creds_manager import BMCCredsException
from tests.common import ExtendedTestCase


class TestBMCCredsMain(ExtendedTestCase):
    """Tests for the main portion of bmccreds, including argument validation."""
    def setUp(self):
        """Set up tests."""
        self.parser = ArgumentParser()
        bmccreds_parser.add_bmccreds_subparser(self.parser.add_subparsers())
        self.cli_args = None

        self.mock_session = patch('sat.cli.bmccreds.main.SATSession').start().return_value
        self.mock_hsm_client_cls = patch('sat.cli.bmccreds.main.HSMClient').start()
        self.mock_hsm_client = self.mock_hsm_client_cls.return_value

        self.credentials = ('myuser', 'sWoRdp45')
        self.mock_get_username_and_password = patch(
            'sat.cli.bmccreds.main.get_username_and_password_interactively', return_value=self.credentials
        ).start()

        self.bmccreds_cls = patch('sat.cli.bmccreds.main.BMCCredsManager').start()
        self.bmccreds = self.bmccreds_cls.return_value

        self.mock_pester = patch('sat.cli.bmccreds.main.pester', return_value=True).start()
        patch('builtins.print', side_effect=self.mock_print).start()
        self.mock_print_output = []

        patch('sat.config.get_config_value').start()

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    def mock_print(self, line=''):
        """Capture printed output."""
        self.mock_print_output.append(line)

    def assert_exits_with_error(self, function, args, expected_error_text, expected_exit_code=1):
        """Helper to assert a function exits and logs an error."""
        with self.assertRaises(SystemExit) as err_cm:
            with self.assertLogs(level=logging.ERROR) as logs:
                function(args)
        self.assert_in_element(expected_error_text, logs.output)
        self.assertEqual(err_cm.exception.code, expected_exit_code)

    def parse_args(self):
        """Parse an array of CLI arguments"""
        return self.parser.parse_args(self.cli_args)

    def test_unknown_option(self):
        """Test an unknown option results in an error."""
        self.cli_args = ['bmccreds', '--unknown-option']
        expected_exit_code = 2
        with patch('sys.stderr.write'):
            with self.assertRaises(SystemExit) as err_cm:
                self.parse_args()
        self.assertEqual(err_cm.exception.code, expected_exit_code)

    def test_pw_domain_without_random_password(self):
        """Giving --pw-domain without --random-password results in an error."""
        self.cli_args = ['bmccreds', '--pw-domain=system', '--password=foo']
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            '--pw-domain is only valid with --random-password.'
        )

    def test_pw_domain_without_random_password_or_password(self):
        """Giving --pw-domain without --random-password results in an error."""
        self.cli_args = ['bmccreds', '--pw-domain=system']
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            '--pw-domain is only valid with --random-password.'
        )

    def test_no_hsm_check_without_xnames(self):
        """Giving --no-hsm-check without xnames results in an error."""
        self.cli_args = ['bmccreds', '--no-hsm-check']
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            '--no-hsm-check requires xnames to be specified.'
        )

    def test_with_no_arguments(self):
        """Supplying no arguments will prompt for password and query hsm."""
        self.cli_args = ['bmccreds']
        do_bmccreds(self.parse_args())
        self.mock_hsm_client.get_and_filter_bmcs.assert_called_once_with(
            BMC_TYPES, False, False, None
        )
        self.mock_get_username_and_password.assert_called_once_with(
            BMC_USERNAME, password_prompt='BMC password', confirm_password=True
        )
        self.bmccreds_cls.assert_called_once_with(
            password=self.credentials[1],
            xnames=self.mock_hsm_client.get_and_filter_bmcs.return_value,
            domain=None,
            force=False,
            report_format='pretty'
        )

    def test_random_password(self):
        """Supplying --random-password will not prompt or initialize BMCCredsManager with a password."""
        self.cli_args = ['bmccreds', '--random-password']
        do_bmccreds(self.parse_args())
        self.mock_get_username_and_password.assert_not_called()
        self.bmccreds_cls.assert_called_once_with(
            password=None,
            xnames=self.mock_hsm_client.get_and_filter_bmcs.return_value,
            domain=None,
            force=False,
            report_format='pretty'
        )

    def test_random_password_with_domain(self):
        """Supplying --random-password with a domain specifies a domain"""
        self.cli_args = ['bmccreds', '--random-password', '--pw-domain', 'bmc']
        do_bmccreds(self.parse_args())
        self.mock_get_username_and_password.assert_not_called()
        self.bmccreds_cls.assert_called_once_with(
            password=None,
            xnames=self.mock_hsm_client.get_and_filter_bmcs.return_value,
            domain='bmc',
            force=False,
            report_format='pretty'
        )

    def test_with_type(self):
        """Supplying no arguments will prompt for password and query hsm."""
        self.cli_args = ['bmccreds', '--bmc-types', 'NodeBMC']
        do_bmccreds(self.parse_args())
        self.mock_hsm_client.get_and_filter_bmcs.assert_called_once_with(
            ['NodeBMC'], False, False, None
        )

    def test_with_include_disabled(self):
        """Including disabled components calls get_and_filter_bmcs with disabled components."""
        self.cli_args = ['bmccreds', '--include-disabled']
        do_bmccreds(self.parse_args())
        self.mock_hsm_client.get_and_filter_bmcs.assert_called_once_with(
            BMC_TYPES, True, False, None
        )

    def test_with_include_discovery_failed(self):
        """Including failed-to-discover components calls get_and_filter_bmcs with ."""
        self.cli_args = ['bmccreds', '--include-failed-discovery']
        do_bmccreds(self.parse_args())
        self.mock_hsm_client.get_and_filter_bmcs.assert_called_once_with(
            BMC_TYPES, False, True, None
        )

    def test_no_hsm_check_with_xnames(self):
        """Giving --no-hsm-check skips querying HSM and uses 'force'."""
        self.cli_args = ['bmccreds', '--no-hsm-check', '--xnames', 'x1000c0s0b0']
        do_bmccreds(self.parse_args())
        self.mock_hsm_client_cls.assert_not_called()
        self.mock_hsm_client.get_and_filter_bmcs.assert_not_called()
        self.bmccreds_cls.assert_called_once_with(
            password=self.credentials[1],
            xnames={'x1000c0s0b0'},
            domain=None,
            force=True,
            report_format='pretty'
        )
        self.bmccreds.set_bmc_passwords.assert_called_once_with(
            self.mock_session
        )

    def test_no_xnames_error(self):
        """If filtering xnames from HSM returns no xnames, exit with an error."""
        self.cli_args = ['bmccreds']
        self.mock_hsm_client.get_and_filter_bmcs.return_value = []
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            'No valid xnames for which to set credentials.'
        )

    def test_hsm_api_error(self):
        self.cli_args = ['bmccreds']
        self.mock_hsm_client.get_and_filter_bmcs.side_effect = APIError('API failed')
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            'Failed to contact HSM to check BMC eligibility: API failed'
        )

    def test_retry(self):
        """Test that setting credentials will retry if it fails the first time."""
        self.cli_args = ['bmccreds']
        self.bmccreds.set_bmc_passwords.side_effect = (BMCCredsException, None)
        do_bmccreds(self.parse_args())
        self.assertEqual(
            len(self.bmccreds.set_bmc_passwords.mock_calls), 2
        )

    def test_retry_failed(self):
        """Test that the command fails when the default number of retries is exceeded."""
        self.cli_args = ['bmccreds']
        self.bmccreds.set_bmc_passwords.side_effect = BMCCredsException
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            'Failed to update BMC credentials after 3 retries'
        )
        self.assertEqual(
            len(self.bmccreds.set_bmc_passwords.mock_calls), 3
        )

    def test_custom_retry(self):
        """Test that the command will be limited to the specified number of retries."""
        self.cli_args = ['bmccreds', '--retries', '5']
        self.bmccreds.set_bmc_passwords.side_effect = BMCCredsException
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            'Failed to update BMC credentials after 5 retries'
        )
        self.assertEqual(
            len(self.bmccreds.set_bmc_passwords.mock_calls), 5
        )

    def test_weak_password(self):
        """Test that a weak password will be flagged by the strength check."""
        self.cli_args = ['bmccreds', '--password', 'password']
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            'Please supply a stronger password.'
        )
        self.assertEqual(
            '\n'.join(self.mock_print_output),
            dedent("""\
                Bad password. Possible improvements:
                 - Use a good mix of numbers and letters
                 - Use a good mix of UPPER case and lower case letters
                 - Avoid using one of the ten thousand most common passwords
                 - Passphrases (e.g. an obfuscated sentence) are better than passwords""")
        )

    def test_abort_at_prompt(self):
        """Test that we don't set passwords when the user does not confirm."""
        self.cli_args = ['bmccreds']
        self.mock_pester.return_value = False
        with self.assertRaises(SystemExit):
            do_bmccreds(self.parse_args())
        self.mock_pester.assert_called_once()

    def test_disruptive(self):
        """Test that using --disruptive does not prompt."""
        self.cli_args = ['bmccreds', '--disruptive']
        do_bmccreds(self.parse_args())
        self.mock_pester.assert_not_called()

    def test_no_pw_strength_check(self):
        """Test that a weak password can be set by overriding the strength check."""
        self.cli_args = ['bmccreds', '--password', 'password', '--no-pw-strength-check']
        do_bmccreds(self.parse_args())

    def test_too_long_password(self):
        """Test that a password that is too long can never be set."""
        self.cli_args = ['bmccreds', '--password', 'passwordpassword', '--no-pw-strength-check']
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            f'Password must be less than or equal to {USER_PASSWORD_MAX_LENGTH} characters.'
        )

    def test_with_illegal_characters(self):
        """Test that a password with disallowed characters can never be set."""
        self.cli_args = ['bmccreds', '--password', 'pas$word', '--no-pw-strength-check']
        self.assert_exits_with_error(
            do_bmccreds, self.parse_args(),
            'Password may only contain letters, numbers and underscores.'
        )


if __name__ == '__main__':
    unittest.main()
