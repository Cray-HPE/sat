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
Unit tests for sat.apiclient.capmc
"""

import logging
import unittest
from unittest import mock

from sat.apiclient import APIError, APIGatewayClient, CAPMCClient, CAPMCError
from tests.common import ExtendedTestCase


class TestCAPMCError(unittest.TestCase):
    """Tests for the CAPMCError custom Exception class."""
    def setUp(self):
        self.err_msg = 'Some CAPMC error'

    def test_with_no_xnames(self):
        """Test CAPMCError with no xnames argument."""
        err = CAPMCError(self.err_msg)
        self.assertEqual(self.err_msg, str(err))

    def test_with_empty_xnames(self):
        """Test CAPMCError with empty list of xnames."""
        err = CAPMCError(self.err_msg)
        self.assertEqual(self.err_msg, str(err))

    def test_with_xnames_same_errs(self):
        """Test CAPMCError with some xnames having the same error."""
        common_err_msg = 'failed to power off node'
        xnames = [
            {
                'e': 1,
                'err_msg': common_err_msg,
                'xname': 'x3000c0s0b0n0'
            },
            {
                'e': 1,
                'err_msg': common_err_msg,
                'xname': 'x5000c0s7b1n1'
            }
        ]
        err = CAPMCError(self.err_msg, xname_errs=xnames)
        expected_str = (
            f'{self.err_msg}\n'
            f'xname(s) (x3000c0s0b0n0, x5000c0s7b1n1) failed with e=1 '
            f'and err_msg="{common_err_msg}"'
        )
        self.assertEqual(expected_str, str(err))

    def test_with_xnames_diff_errs(self):
        """Test CAPMCError with some xnames having different errors."""
        base_err_msg = 'Some CAPMC error'
        first_err_msg = 'failed to power off node'
        second_err_msg = 'unable to reach node'
        xnames = [
            {
                'e': 1,
                'err_msg': first_err_msg,
                'xname': 'x3000c0s0b0n0'
            },
            {
                'e': 1,
                'err_msg': second_err_msg,
                'xname': 'x5000c0s7b1n1'
            }
        ]
        err = CAPMCError(base_err_msg, xname_errs=xnames)
        expected_str = (
            f'{base_err_msg}\n'
            f'xname(s) (x3000c0s0b0n0) failed with e=1 and err_msg="{first_err_msg}"\n'
            f'xname(s) (x5000c0s7b1n1) failed with e=1 and err_msg="{second_err_msg}"'
        )
        self.assertEqual(expected_str, str(err))


class TestCAPMCClientSetState(ExtendedTestCase):
    """Test the CAPMClient method to set power state."""
    def setUp(self):
        self.xnames = ['x1000c0s0b0n0', 'x1000c0s1b0n0']
        self.post_params = {'xnames': self.xnames, 'force': False,
                            'recursive': False, 'prereq': False}

        self.mock_session = mock.MagicMock(host='api-gw-client.local')
        self.mock_post = mock.patch.object(APIGatewayClient, 'post').start()
        self.mock_post.return_value.json.return_value = {'e': 0, 'err_msg': '', 'xnames': []}

        self.capmc_client = CAPMCClient(self.mock_session)

    def tearDown(self):
        mock.patch.stopall()

    def test_set_xnames_power_state_on_success(self):
        """Test set_xnames_power_state with on state in successful case."""
        self.capmc_client.set_xnames_power_state(self.xnames, 'on')
        self.mock_post.assert_called_once_with('xname_on', json=self.post_params)

    def test_set_xnames_power_state_off_success(self):
        """Test set_xnames_power_state with off state in successful case."""
        self.capmc_client.set_xnames_power_state(self.xnames, 'off')
        self.mock_post.assert_called_once_with('xname_off', json=self.post_params)

    def test_set_xnames_force_recursive(self):
        """Test set_xnames_power_state with force and recursive options."""
        self.capmc_client.set_xnames_power_state(self.xnames, 'on', force=True, recursive=True)
        expected_params = {'xnames': self.xnames, 'force': True,
                           'recursive': True, 'prereq': False}
        self.mock_post.assert_called_once_with('xname_on', json=expected_params)

    def test_set_xnames_force_prereq(self):
        """Test set_xnames_power_state with force and prereq options."""
        self.capmc_client.set_xnames_power_state(self.xnames, 'on', force=True, prereq=True)
        expected_params = {'xnames': self.xnames, 'force': True,
                           'recursive': False, 'prereq': True}
        self.mock_post.assert_called_once_with('xname_on', json=expected_params)

    def test_set_xnames_power_state_api_err(self):
        """Test set_xnames_power_state with APIError."""
        self.mock_post.side_effect = APIError('failure')
        power_state = 'on'
        expected_err = rf'Failed to power {power_state} xname\(s\): {", ".join(self.xnames)}'
        with self.assertRaisesRegex(CAPMCError, expected_err):
            self.capmc_client.set_xnames_power_state(self.xnames, power_state)

    def test_set_xnames_power_state_value_err(self):
        """Test set_xnames_power_state with ValueError when trying to parse JSON response."""
        self.mock_post.return_value.json.side_effect = ValueError("bad JSON")
        power_state = 'on'
        expected_err = (rf'Failed to parse JSON in response from CAPMC API when powering '
                        rf'{power_state} xname\(s\): {", ".join(self.xnames)}')
        with self.assertRaisesRegex(CAPMCError, expected_err):
            self.capmc_client.set_xnames_power_state(self.xnames, power_state)

    def test_set_xnames_power_state_bad_state(self):
        """Test set_xnames_power_state with invalid power state."""
        bad_state = 'sleeping'
        expected_err = f'Invalid power state {bad_state} given. Must be "on" or "off"'
        with self.assertRaisesRegex(ValueError, expected_err):
            self.capmc_client.set_xnames_power_state(self.xnames, bad_state)

    def test_set_xnames_power_state_err_response(self):
        """Test set_xnames_power_state with an error reported in response from CAPMC."""
        self.mock_post.return_value.json.return_value = {
            'e': -1,
            'err_msg': 'some failure',
            'xnames': [{'e': -1, 'err_msg': 'failure', 'xname': 'x1000c0s0b0n0'}]
        }
        power_state = 'on'
        expected_err = rf'Power {power_state} operation failed for xname\(s\).'
        with self.assertRaisesRegex(CAPMCError, expected_err):
            self.capmc_client.set_xnames_power_state(self.xnames, power_state)


class TestCAPMCClientGetState(ExtendedTestCase):
    """Test the CAPMClient methods to get power state."""

    def setUp(self):
        self.xnames = ['x1000c0s0b0n0', 'x1000c0s1b0n0']
        self.post_params = {'xnames': self.xnames}

        self.mock_session = mock.MagicMock(host='api-gw-host.local')
        self.mock_post = mock.patch.object(APIGatewayClient, 'post').start()
        self.mock_post.return_value.json.return_value = {
            'e': 0,
            'err_msg': '',
            'on': self.xnames[:1],
            'off': self.xnames[1:]
        }

        self.capmc_client = CAPMCClient(self.mock_session)

    def tearDown(self):
        mock.patch.stopall()

    def test_get_xnames_power_state_success(self):
        """Test get_xnames_power_state in successful case."""
        nodes_by_state = self.capmc_client.get_xnames_power_state(self.xnames)
        expected = {'on': self.xnames[:1], 'off': self.xnames[1:]}
        self.assertEqual(expected, nodes_by_state)

    def test_get_xnames_power_state_api_err(self):
        """Test get_xnames_power_state with APIError."""
        self.mock_post.side_effect = APIError('failure')
        expected_err = rf'Failed to get power state of xname\(s\): {", ".join(self.xnames)}'
        with self.assertRaisesRegex(CAPMCError, expected_err):
            self.capmc_client.get_xnames_power_state(self.xnames)

    def test_get_xnames_power_state_value_err(self):
        """Test get_xnames_power_state with a ValueError when parsing JSON."""
        self.mock_post.side_effect = ValueError('bad JSON')
        expected_err = (rf'Failed to parse JSON in response from CAPMC API when '
                        rf'getting power state of xname\(s\): {", ".join(self.xnames)}')
        with self.assertRaisesRegex(CAPMCError, expected_err):
            self.capmc_client.get_xnames_power_state(self.xnames)

    def test_get_xnames_power_state_capmc_err(self):
        """Test get_xnames_power_state with an error reported by CAPMC."""
        self.mock_post.return_value.json.return_value['e'] = -1
        err_msg = 'capmc failure'
        self.mock_post.return_value.json.return_value = {
            'e': -1,
            'err_msg': err_msg,
            'undefined': self.xnames
        }
        expected_warning = (f'Failed to get power state of one or more xnames, e=-1, '
                            f'err_msg="{err_msg}". xnames with undefined power state: '
                            f'{", ".join(self.xnames)}')

        with self.assertLogs(level=logging.WARNING) as cm:
            self.capmc_client.get_xnames_power_state(self.xnames)
        self.assert_in_element(expected_warning, cm.output)

    def test_get_xnames_power_state_capmc_err_suppress(self):
        """Test get_xnames_power_state with an error reported by CAPMC."""
        self.mock_post.return_value.json.return_value['e'] = -1
        err_msg = 'capmc failure'
        self.mock_post.return_value.json.return_value = {
            'e': -1,
            'err_msg': err_msg,
            'undefined': self.xnames
        }
        expected_msg = (f'Failed to get power state of one or more xnames, e=-1, '
                        f'err_msg="{err_msg}". xnames with undefined power state: '
                        f'{", ".join(self.xnames)}')
        capmc_client = CAPMCClient(self.mock_session, suppress_warnings=True)
        with self.assertLogs(level=logging.DEBUG) as cm:
            capmc_client.get_xnames_power_state(self.xnames)

        self.assertEqual(logging.getLevelName(logging.DEBUG), cm.records[0].levelname)
        self.assertEqual(cm.records[-1].message, expected_msg)

    def test_get_xname_power_state_success(self):
        """Test get_xname_power_state when there is a single matching state."""
        self.assertEqual('on', self.capmc_client.get_xname_power_state(self.xnames[0]))
        self.assertEqual('off', self.capmc_client.get_xname_power_state(self.xnames[1]))

    def test_get_xname_power_state_multiple_matches(self):
        """Test get_xname_power_state when there are multiple matching states for a node."""
        self.mock_post.return_value.json.return_value = {
            'e': 0,
            'err_msg': '',
            'on': self.xnames,
            'off': self.xnames
        }
        xname = self.xnames[0]
        expected_err = (f'Unable to determine power state of {xname}. CAPMC '
                        f'reported multiple power states: on, off')
        with self.assertRaisesRegex(CAPMCError, expected_err):
            self.capmc_client.get_xname_power_state(xname)

    def test_get_xname_power_state_no_matches(self):
        """Test get_xname_power_state when there are no matches for the xname."""
        self.mock_post.return_value.json.return_value = {
            'e': 0,
            'err_msg': '',
            'on': self.xnames[1:]
        }
        xname = self.xnames[0]
        expected_err = (f'Unable to determine power state of {xname}. Not '
                        f'present in response from CAPMC')
        with self.assertRaisesRegex(CAPMCError, expected_err):
            self.capmc_client.get_xname_power_state(xname)


if __name__ == '__main__':
    unittest.main()
