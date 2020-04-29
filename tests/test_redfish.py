"""
Unit tests for sat.redfish

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

import os
import unittest
from collections import defaultdict
from unittest import mock

import sat.redfish
import sat.config


class InputDict(dict):
    """For help with mocking getpass.

    When tests in this file mock input, they do it by replacing it with a
    lambda that points to a global instance of InputDict, which finds a field
    that is a substring of the prompt to input.
    """
    def __getitem__(self, super_):
        """Find first value whose key is in super_.

        Args:
            super_: A string that should contain one of the keys as a
                substring.

        Returns:
            Value if its key is a substring of super_.
            Returns empty string if no match.
        """

        for key, val in self.items():
            if key in super_:
                return val

        return ''


# For mocking sat.config.get_config_value
full = defaultdict(lambda: '')
full['redfish.username'] = 'user'
full['redfish.password'] = 'pass'

withuser = defaultdict(lambda: '')
withuser['redfish.username'] = 'user'

withpass = defaultdict(lambda: '')
withpass['redfish.password'] = 'pass'

empty = defaultdict(lambda: '')


class TestRedfishAuth(unittest.TestCase):
    """Tests for redfish.get_username_and_pass function.
    """

    @mock.patch('sat.redfish.get_config_value', lambda x: full[x])
    def test_empty_suggestion(self):
        """It should use the values in the config if no suggestion.
        """
        u, p = sat.redfish.get_username_and_pass()
        self.assertEqual('user', u)
        self.assertEqual('pass', p)

    @mock.patch('sat.redfish.get_config_value', lambda x: full[x])
    @mock.patch('sat.redfish.getpass.getpass', return_value='topsecret')
    def test_suggestion_usage(self, _):
        """It should use the suggested username and prompt for a password.
        """
        u, p = sat.redfish.get_username_and_pass('suggestion')
        self.assertEqual('suggestion', u)
        self.assertEqual('topsecret', p)

    @mock.patch('sat.redfish.get_config_value', lambda x: empty[x])
    @mock.patch('sat.redfish.getpass.getpass', return_value='topsecret')
    @mock.patch('builtins.input', return_value='yogibear')
    def test_empty_config(self, _a, _b):
        """It should prompt for both username and password if config empty.
        """
        u, p = sat.redfish.get_username_and_pass()
        self.assertEqual('yogibear', u)
        self.assertEqual('topsecret', p)

    @mock.patch('sat.redfish.get_config_value', lambda x: withuser[x])
    @mock.patch('sat.redfish.getpass.getpass', return_value='topsecret')
    def test_config_has_username(self, _):
        """It should only prompt for password if config has username.
        """
        u, p = sat.redfish.get_username_and_pass()
        self.assertEqual('user', u)
        self.assertEqual('topsecret', p)

    @mock.patch('sat.redfish.get_config_value', lambda x: withpass[x])
    @mock.patch('sat.redfish.getpass.getpass', return_value='topsecret')
    @mock.patch('builtins.input', return_value='yogibear')
    def test_config_has_password(self, _a, _b):
        """It should prompt for both if config is missing username.
        """
        u, p = sat.redfish.get_username_and_pass()
        self.assertEqual('yogibear', u)
        self.assertEqual('topsecret', p)

    @mock.patch('sat.redfish.get_config_value', lambda x: withpass[x])
    @mock.patch('sat.redfish.getpass.getpass', return_value='topsecret')
    def test_config_has_password_with_suggestion(self, _):
        """It should just prompt for password if it has been given a suggestion.

        This should hold even if the config is missing a username.
        """
        u, p = sat.redfish.get_username_and_pass('suggestion')
        self.assertEqual('suggestion', u)
        self.assertEqual('topsecret', p)


if __name__ == '__main__':
    unittest.main()
