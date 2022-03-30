"""
Unit tests for sat.apiclient.hsm

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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
import unittest
from unittest import mock

from sat.apiclient import APIError, APIGatewayClient, HSMClient
from tests.common import ExtendedTestCase


class TestHSMClient(unittest.TestCase):
    """Tests for the APIGatewayClient class: HSM client."""

    def setUp(self):
        self.xnames = ['x1000c0s0b0n0', 'x1000c0s0b0n1', 'x1000c0s1b0n0', 'x1000c0s1b0n1']
        self.states = ['On', 'Ready', 'Empty', 'Empty']

        self.components = [
            # There will be more fields than this, but we only care about these
            {'ID': xname, 'State': state} for xname, state in zip(self.xnames, self.states)
        ]
        self.mock_get = mock.patch.object(APIGatewayClient, 'get').start()
        self.mock_get.return_value.json.return_value = {
            'Components': self.components
        }

        self.hsm_client = HSMClient()

    def tearDown(self):
        mock.patch.stopall()

    def test_get_component_xnames_success(self):
        """Test get_component_xnames in the successful case."""
        params = {'type': 'Node', 'role': 'Compute'}
        result = self.hsm_client.get_component_xnames(params)
        self.mock_get.assert_called_once_with('State', 'Components',
                                              params=params)
        self.assertEqual(self.xnames[0:2], result)

    def test_get_components_xnames_with_empty(self):
        """Test get_component_xnames with omit_empty=False"""
        params = {'type': 'Node', 'role': 'Compute'}
        result = self.hsm_client.get_component_xnames(params, omit_empty=False)
        self.mock_get.assert_called_once_with('State', 'Components',
                                              params=params)
        self.assertEqual(self.xnames, result)

    def test_get_node_components_success(self):
        """Test get_node_components in the successful case."""
        params = {'type': 'Node'}
        result = self.hsm_client.get_node_components()
        self.mock_get.assert_called_once_with('State', 'Components',
                                              params=params)
        self.assertEqual(result, [{'ID': xname, 'State': state}
                                  for xname, state in zip(self.xnames, self.states)])

    def test_get_node_components_api_error(self):
        """Test an API error is handled by get_node_components"""
        params = {'type': 'Node'}
        self.mock_get.side_effect = APIError('HSM failed')
        with self.assertRaisesRegex(APIError, 'Failed to get Node components: HSM failed'):
            self.hsm_client.get_node_components()
        self.mock_get.assert_called_once_with('State', 'Components',
                                              params=params)

    def test_get_node_components_missing_key(self):
        """Test a missing JSON key is handled by get_node_components"""
        params = {'type': 'Node'}
        self.mock_get.return_value.json.return_value = {'Not Components': []}
        err_regex = 'Failed to get Node components due to missing \'Components\' key in response'
        with self.assertRaisesRegex(APIError, err_regex):
            self.hsm_client.get_node_components()
        self.mock_get.assert_called_once_with('State', 'Components',
                                              params=params)

    def test_get_node_components_bad_data(self):
        """Test bad JSON is handled by get_node_components"""
        params = {'type': 'Node'}
        self.mock_get.return_value.json.side_effect = ValueError('Bad JSON')
        err_regex = 'Failed to get Node components due to bad JSON in response: Bad JSON'
        with self.assertRaisesRegex(APIError, err_regex):
            self.hsm_client.get_node_components()
        self.mock_get.assert_called_once_with('State', 'Components',
                                              params=params)

    def test_get_node_components_limit_by_ancestor(self):
        """Test getting node components with a common ancestor"""
        ancestor_xname = 'x1000c0s1'
        self.mock_get.return_value.json.return_value = {
            'Components': [
                component_dict for component_dict in self.components
                if component_dict['ID'].startswith(ancestor_xname)
            ]
        }
        result = self.hsm_client.get_node_components(ancestor=ancestor_xname)
        self.assertEqual({r['ID'] for r in result}, {'x1000c0s1b0n0', 'x1000c0s1b0n1'})

    def test_get_node_components_bad_ancestor(self):
        """Test getting node components with an invalid ancestor xname"""
        with self.assertRaises(APIError):
            self.hsm_client.get_node_components(ancestor='some-invalid-xname')


class TestHSMClientRedfishEndpoints(ExtendedTestCase):
    """Tests for HSMClient functions that interact with the Inventory/RedfishEndpoints API."""

    def setUp(self):
        """Set up tests."""
        # There will be more fields than this, but we only care about these
        self.mock_get = mock.patch.object(APIGatewayClient, 'get').start()
        self.mock_get.return_value.json.return_value = {
            'RedfishEndpoints': [
                {
                    'ID': 'x1000c0s1b0',
                    'Enabled': True,
                    'DiscoveryInfo': {'LastDiscoveryStatus': 'DiscoverOK'}
                },
                {
                    'ID': 'x1000c0s2b0',
                    'Enabled': True,
                    'DiscoveryInfo': {'LastDiscoveryStatus': 'DiscoverOK'}
                },
                {
                    'ID': 'x1000c0r1b0',
                    'Enabled': True,
                    'DiscoveryInfo': {'LastDiscoveryStatus': 'DiscoverOK'}
                },
                {
                    'ID': 'x1000c0b0',
                    'Enabled': True,
                    'DiscoveryInfo': {'LastDiscoveryStatus': 'DiscoverOK'}
                }
            ]
        }
        mock.patch('sat.apiclient.gateway.get_config_value').start()
        self.hsm_client = HSMClient()

    def tearDown(self):
        """Stop patches."""
        mock.patch.stopall()

    def test_get_all_bmc_xnames(self):
        """Test getting all BMC xnames."""
        expected_xnames = {bmc['ID'] for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints']}
        actual_xnames = self.hsm_client.get_and_filter_bmcs()
        self.mock_get.assert_called_once_with('Inventory', 'RedfishEndpoints', params={})
        self.assertEqual(expected_xnames, actual_xnames)

    def test_get_all_bmc_xnames_with_types(self):
        """Test getting all BMC xnames when types are explicitly specified."""
        expected_xnames = {bmc['ID'] for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints']}
        actual_xnames = self.hsm_client.get_and_filter_bmcs(bmc_types=('ChassisBMC', 'NodeBMC', 'RouterBMC'))
        self.mock_get.assert_called_once_with('Inventory', 'RedfishEndpoints', params={})
        self.assertEqual(expected_xnames, actual_xnames)

    def test_get_all_bmc_xnames_with_two_types(self):
        """Test getting BMCs with two types queries HSM once per type."""
        # Force the fake BMCs returned to exclude RouterBMC xnames. Here the type filtering
        # is actually done by the HSM API and mocking the behavior doesn't affect the test,
        # which is asserting that we called HSM correctly and returned what HSM gave us.
        chassis_response = mock.Mock()
        chassis_response.json.return_value = {
            'RedfishEndpoints': [
                {
                    'ID': 'x1000c0b0',
                    'Enabled': True,
                    'DiscoveryInfo': {'LastDiscoveryStatus': 'DiscoverOK'}
                }
            ]
        }
        router_response = mock.Mock()
        router_response.json.return_value = {
            'RedfishEndpoints': [
                {
                    'ID': 'x1000c0r1b0',
                    'Enabled': True,
                    'DiscoveryInfo': {'LastDiscoveryStatus': 'DiscoverOK'}
                }
            ]
        }

        def _fake_get(*args, params):
            if params.get('type') == 'ChassisBMC':
                return chassis_response
            return router_response
        self.mock_get.side_effect = _fake_get

        expected_xnames = {'x1000c0b0', 'x1000c0r1b0'}
        actual_xnames = self.hsm_client.get_and_filter_bmcs(bmc_types=('ChassisBMC', 'RouterBMC'))
        self.assertEqual(
            self.mock_get.call_args_list,
            [
                mock.call('Inventory', 'RedfishEndpoints', params={'type': 'ChassisBMC'}),
                mock.call('Inventory', 'RedfishEndpoints', params={'type': 'RouterBMC'})
            ]
        )
        self.assertEqual(expected_xnames, actual_xnames)

    def test_missing_xname(self):
        """Test getting BMC data using an xname that is missing from HSM."""
        bmcs = [
            bmc for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints']
            if bmc['ID'] != 'x1000c0r1b0'
        ]
        self.mock_get.return_value.json.return_value['RedfishEndpoints'] = bmcs
        expected_xnames = []
        with self.assertLogs(level=logging.WARNING) as logs:
            actual_xnames = self.hsm_client.get_and_filter_bmcs(xnames=['x1000c0r1b0'])
        self.mock_get.assert_called_once_with('Inventory', 'RedfishEndpoints', params={})
        self.assertCountEqual(expected_xnames, actual_xnames)
        self.assert_in_element(
            'The following xnames will be excluded as they are not type(s) NodeBMC, RouterBMC, ChassisBMC: x1000c0r1b0',
            logs.output
        )

    def test_wrong_type_xname(self):
        """Test getting BMC data using an xname that is not the right type."""
        # This is not much different than test_missing_xname because the filtering is done by the HSM API.
        bmcs = [
            bmc for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints']
            if bmc['ID'] == 'x1000c0b0'
        ]
        self.mock_get.return_value.json.return_value['RedfishEndpoints'] = bmcs
        expected_xnames = []
        with self.assertLogs(level=logging.WARNING) as logs:
            actual_xnames = self.hsm_client.get_and_filter_bmcs(xnames=['x1000c0r1b0'], bmc_types=('ChassisBMC',))
        self.mock_get.assert_called_once_with('Inventory', 'RedfishEndpoints', params={'type': 'ChassisBMC'})
        self.assertCountEqual(expected_xnames, actual_xnames)
        self.assert_in_element(
            'The following xnames will be excluded as they are not type(s) ChassisBMC: x1000c0r1b0',
            logs.output
        )

    def test_get_bmc_xnames_excluding_disabled(self):
        """Test getting BMC data and excluding disabled BMCs."""
        self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['Enabled'] = False
        disabled_bmc_xname = self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['ID']
        expected_xnames = [bmc['ID'] for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints'][1:]]
        with self.assertLogs(level=logging.WARNING) as logs:
            actual_xnames = self.hsm_client.get_and_filter_bmcs()
        self.assertCountEqual(expected_xnames, actual_xnames)
        self.assert_in_element(f'Excluding the following xnames which are disabled: {disabled_bmc_xname}', logs.output)

    def test_get_bmc_xnames_including_disabled(self):
        """Test getting BMC data and including disabled BMCs."""
        self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['Enabled'] = False
        expected_xnames = [bmc['ID'] for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints']]
        actual_xnames = self.hsm_client.get_and_filter_bmcs(include_disabled=True)
        self.assertCountEqual(expected_xnames, actual_xnames)

    def test_get_bmc_xnames_excluding_failed_discovery(self):
        """Test getting BMC data and excluding BMCs for which discovery failed."""
        return_value = self.mock_get.return_value.json.return_value
        return_value['RedfishEndpoints'][0]['DiscoveryInfo']['LastDiscoveryStatus'] = 'HTTPSGetFailed'
        failed_bmc_xname = self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['ID']
        expected_xnames = [bmc['ID'] for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints'][1:]]
        with self.assertLogs(level=logging.WARNING) as logs:
            actual_xnames = self.hsm_client.get_and_filter_bmcs()
        self.assertCountEqual(expected_xnames, actual_xnames)
        self.assert_in_element(
            f'Excluding the following xnames which have a LastDiscoveryStatus '
            f'other than "DiscoverOK": {failed_bmc_xname}', logs.output
        )

    def test_get_bmc_xnames_including_failed_discovery(self):
        """Test getting BMC data and including BMCs for which discovery failed."""
        return_value = self.mock_get.return_value.json.return_value
        return_value['RedfishEndpoints'][0]['DiscoveryInfo']['LastDiscoveryStatus'] = 'HTTPSGetFailed'
        expected_xnames = [bmc['ID'] for bmc in self.mock_get.return_value.json.return_value['RedfishEndpoints']]
        actual_xnames = self.hsm_client.get_and_filter_bmcs(include_failed_discovery=True)
        self.assertCountEqual(expected_xnames, actual_xnames)

    def test_get_bmc_xnames_with_xnames(self):
        """Test getting BMC data when giving two xnames to filter."""
        xnames_to_query = ['x1000c0s1b0', 'x1000c0s2b0']
        actual_xnames = self.hsm_client.get_and_filter_bmcs(
            bmc_types=('NodeBMC', 'ChassisBMC', 'RouterBMC'), xnames=xnames_to_query
        )
        self.assertCountEqual(xnames_to_query, actual_xnames)

    def test_get_bmc_xnames_missing_endpoints_key(self):
        """Test getting BMC data when the API response is missing a RedfishEndpoints key."""
        del self.mock_get.return_value.json.return_value['RedfishEndpoints']
        with self.assertRaisesRegex(APIError, 'API response missing expected key: \'RedfishEndpoints\''):
            self.hsm_client.get_and_filter_bmcs()

    def test_get_bmc_xnames_invalid_json(self):
        """Test getting BMC data when the API response is not valid JSON."""
        self.mock_get.return_value.json.side_effect = ValueError('Invalid JSON')
        with self.assertRaisesRegex(APIError, 'API response could not be parsed as JSON: Invalid JSON'):
            self.hsm_client.get_and_filter_bmcs()

    def test_get_bmc_xnames_missing_key(self):
        """Test getting BMC data when one of the BMCs is missing the 'Enabled' key."""
        del self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['Enabled']
        incomplete_xname = self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['ID']
        with self.assertLogs(level=logging.WARNING) as logs:
            self.hsm_client.get_and_filter_bmcs()
        self.assert_in_element(
            f'The following xnames were excluded due to incomplete information from HSM: {incomplete_xname}',
            logs.output
        )

    def test_get_bmc_xnames_missing_subkey(self):
        """Test getting BMC data when one of the BMCs is missing the 'LastDiscoveryStatus' key."""
        del self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['DiscoveryInfo']['LastDiscoveryStatus']
        incomplete_xname = self.mock_get.return_value.json.return_value['RedfishEndpoints'][0]['ID']
        with self.assertLogs(level=logging.WARNING) as logs:
            self.hsm_client.get_and_filter_bmcs()
        self.assert_in_element(
            f'The following xnames were excluded due to incomplete information from HSM: {incomplete_xname}',
            logs.output
        )


if __name__ == '__main__':
    unittest.main()
