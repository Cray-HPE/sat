#
# MIT License
#
# (C) Copyright 2021-2023 Hewlett Packard Enterprise Development LP
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
"""
Tests for the PCSClient class.
"""

import unittest
from unittest.mock import MagicMock

from csm_api_client.service.gateway import APIError

from sat.apiclient.pcs import PCSClient, PCSError
from sat.session import SATSession


class TestPCSClient(unittest.TestCase):
    """Tests for the PCSClient class"""

    def setUp(self):
        self.power_status_retval = {
            'status': [
                {
                    'xname': 'x3000c0s0b0n0',
                    'powerState': 'on',
                    'managementState': 'available',
                    'error': None,
                    'supportedPowerTransitions': [
                        'off',
                        'soft-restart',
                        'hard-restart',
                        'force-off',
                        'soft-off',
                    ],
                    'lastUpdated': '2022-08-24T16:45:53.953811137Z',
                },
                {
                    'xname': 'x3000c0s0b0n1',
                    'powerState': 'off',
                    'managementState': 'available',
                    'error': None,
                    'supportedPowerTransitions': [
                        'off',
                        'soft-restart',
                        'hard-restart',
                        'force-off',
                        'soft-off',
                    ],
                    'lastUpdated': '2022-08-24T16:45:53.953811137Z',
                },
            ],
        }
        self.mock_session = MagicMock(autospec=SATSession)
        self.mock_session.session.get.return_value.json.return_value = self.power_status_retval
        self.mock_session.host = 'api-service-gw-nmn.local'
        self.pcs_client = PCSClient(self.mock_session)
        self.xnames = [f'x3000c0s0b0n{n}' for n in [0, 1]]

    def test_get_xname_power_state(self):
        """Test getting power state for an xname"""
        status = self.pcs_client.get_xname_power_state('x3000c0s0b0n0')
        self.assertEqual(status, 'on')

    def test_get_xname_power_state_fails(self):
        """Test error handling when PCS can't be queried"""
        self.mock_session.session.get.side_effect = APIError
        with self.assertRaises(PCSError):
            self.pcs_client.get_xname_power_state('x3000c0s0b0n0')

    def test_get_xnames_power_state(self):
        """Test getting power state for multiple xnames"""
        status = self.pcs_client.get_xnames_power_state(self.xnames)
        self.assertEqual(['x3000c0s0b0n0'], status['on'])
        self.assertEqual(['x3000c0s0b0n1'], status['off'])

    def test_get_xnames_power_state_fails(self):
        """Test error handling when getting power state for multiple xnames"""
        self.mock_session.session.get.side_effect = APIError
        with self.assertRaises(PCSError):
            self.pcs_client.get_xnames_power_state(self.xnames)
