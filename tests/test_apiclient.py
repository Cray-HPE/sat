"""
Unit tests for sat.apiclient

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
import logging
from unittest import mock
import unittest

import requests

import sat.apiclient
import sat.config
from tests.common import ExtendedTestCase


def get_http_url_prefix(hostname):
    """Construct http URL prefix to help with assertions on requests.get calls."""
    return 'https://{}/apis/'.format(hostname)


class TestAPIGatewayClient(unittest.TestCase):
    """Tests for the APIGatewayClient class."""

    def setUp(self):
        self.stored_config = sat.config.CONFIG
        sat.config.CONFIG = sat.config.SATConfig('')

    def tearDown(self):
        sat.config.CONFIG = self.stored_config

    def test_create_without_host(self):
        """Test creation of APIGatewayClient w/o host."""
        default_host = 'default-api-gw'
        with mock.patch('sat.apiclient.get_config_value', return_value=default_host):
            client = sat.apiclient.APIGatewayClient()

        self.assertEqual(client.host, default_host)

    def test_create_with_host(self):
        """Test creation of APIGatewayClient w/ host."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        self.assertEqual(client.host, api_gw_host)

    @mock.patch('requests.get')
    def test_get_no_params(self, mock_requests_get):
        """Test get method with no additional params."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        response = client.get(*path_components)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            params=None, verify=True, timeout=60
        )
        self.assertEqual(response, mock_requests_get.return_value)

    @mock.patch('requests.get')
    def test_get_with_params(self, mock_requests_get):
        """Test get method with additional params."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['People']
        params = {'name': 'ryan'}
        response = client.get(*path_components, params=params)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            params=params, verify=True, timeout=60
        )
        self.assertEqual(response, mock_requests_get.return_value)

    @mock.patch('requests.get', side_effect=requests.exceptions.RequestException)
    def test_get_exception(self, _):
        """Test get method with exception during GET."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        with self.assertRaises(sat.apiclient.APIError):
            client.get(*path_components)

    @mock.patch('requests.post')
    def test_post(self, mock_requests_post):
        """Test post method."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        payload = {}
        response = client.post(*path_components, payload=payload)

        mock_requests_post.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            data=payload, verify=True, json=None, timeout=60
        )
        self.assertEqual(response, mock_requests_post.return_value)

    @mock.patch('requests.post', side_effect=requests.exceptions.RequestException)
    def test_post_exception(self, _):
        """Test post method with exception during POST."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        payload = {}
        with self.assertRaises(sat.apiclient.APIError):
            client.post(*path_components, payload=payload)

    @mock.patch('requests.put')
    def test_put(self, mock_requests_put):
        """Test put method."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        payload = {}
        client.put(*path_components, payload=payload)

        mock_requests_put.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            data=payload, verify=True, timeout=60
        )

    @mock.patch('requests.put', side_effect=requests.exceptions.RequestException)
    def test_put_exception(self, _):
        """Test put method with exception during PUT."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        payload = {}
        with self.assertRaises(sat.apiclient.APIError):
            client.put(*path_components, payload=payload)

    @mock.patch('requests.delete')
    def test_delete(self, mock_requests_delete):
        """Test delete method."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        response = client.delete(*path_components)

        mock_requests_delete.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            verify=True, timeout=60
        )
        self.assertEqual(response, mock_requests_delete.return_value)

    @mock.patch('requests.delete', side_effect=requests.exceptions.RequestException)
    def test_delete_exception(self, _):
        """Test delete method with exception during DELETE."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        with self.assertRaises(sat.apiclient.APIError):
            client.delete(*path_components)


class TestHSMClient(unittest.TestCase):
    """Tests for the APIGatewayClient class: HSM client."""

    def setUp(self):
        self.xnames = ['x1000c0s0b0n0', 'x1000c0s1b0n0', 'x1000c0s1b1n0', 'x1000c0s1b1n0']
        self.states = ['On', 'Ready', 'Empty', 'Empty']

        self.mock_get = mock.patch('sat.apiclient.APIGatewayClient.get').start()
        self.mock_get.return_value.json.return_value = {
            'Components': [
                # There will be more fields than this, but we only care about these
                {'ID': xname, 'State': state} for xname, state in zip(self.xnames, self.states)
            ]
        }

        self.hsm_client = sat.apiclient.HSMClient()

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

    def test_get_components_success(self):
        """Test get_node_components in the successful case."""
        params = {'type': 'Node'}
        result = self.hsm_client.get_node_components()
        self.mock_get.assert_called_once_with('State', 'Components',
                                              params=params)


class TestFabricControllerClient(ExtendedTestCase):
    """Tests for the APIGatewayClient class: Fabric Controller client."""

    def setUp(self):
        mock.patch('sat.apiclient.get_config_value').start()

        self.mock_port_sets = {
            'fabric-ports': {'ports': ['x3000c0r24j4p0', 'x3000c0r24j4p1']},
            'edge-ports': {'ports': ['x3000c0r24j8p0', 'x3000c0r24j8p1']}
        }
        self.mock_port_set_status = {
            'fabric-ports': {
                'ports': [
                    {'xname': 'x3000c0r24j4p0', 'status': {'enable': True}},
                    {'xname': 'x3000c0r24j4p1', 'status': {'enable': False}}
                ]
            },
            'edge-ports': {
                'ports': [
                    {'xname': 'x3000c0r24j8p0', 'status': {'enable': True}},
                    {'xname': 'x3000c0r24j8p1', 'status': {'enable': False}}
                ]
            }
        }

        self.json_value_err = False
        self.get_api_err = False

        def mock_fc_get(_, *args):
            mock_response = mock.Mock()
            if self.get_api_err:
                raise sat.apiclient.APIError("simulated failure")
            elif self.json_value_err:
                mock_response.json.side_effect = ValueError('simulated json parse error')
            elif len(args) == 2 and args[0] == 'port-sets':
                # This should give a description of the port set
                mock_response.json.return_value = self.mock_port_sets[args[1]]
            elif len(args) == 3 and args[0] == 'port-sets' and args[-1] == 'status':
                # This should give the status of the port set
                mock_response.json.return_value = self.mock_port_set_status[args[1]]
            else:
                raise AssertionError(f'Unexpected args received by get method: {args}')
            return mock_response

        self.mock_fc_get = mock.patch('sat.apiclient.APIGatewayClient.get', mock_fc_get).start()

        self.fabric_client = sat.apiclient.FabricControllerClient()

        self.fabric_status_fail_msg = 'Failed to get port status for port set fabric-ports'
        self.edge_status_fail_msg = 'Failed to get port status for port set edge-ports'

    def tearDown(self):
        mock.patch.stopall()

    def test_get_fabric_edge_ports(self):
        """Test getting all fabric and edge ports."""
        expected = {
            'fabric-ports': ['x3000c0r24j4p0', 'x3000c0r24j4p1'],
            'edge-ports': ['x3000c0r24j8p0', 'x3000c0r24j8p1']
        }
        actual = self.fabric_client.get_fabric_edge_ports()
        self.assertEqual(expected, actual)

    def test_get_fabric_edge_ports_api_error(self):
        """Test getting all fabric and edge ports when there is an APIError."""
        self.get_api_err = True
        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element('Failed to get ports for port set', cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_bad_json(self):
        """Test getting all fabric and edge ports when the response JSON cannot be parsed."""
        self.json_value_err = True
        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element('Failed to parse response', cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_missing_key(self):
        """Test getting all fabric and edge ports when there is a missing 'ports' key."""
        del self.mock_port_sets['fabric-ports']['ports']
        expected = {
            'edge-ports': ['x3000c0r24j8p0', 'x3000c0r24j8p1']
        }

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports()
        self.assertEqual(1, len(cm.output))
        self.assert_in_element("Response from fabric controller API was missing "
                               "the 'ports' key", cm.output)
        self.assertEqual(expected, actual)

    def test_get_fabric_edge_ports_status(self):
        """Test getting enabled status of fabric and edge ports."""
        expected = {
            'fabric-ports': {'x3000c0r24j4p0': True, 'x3000c0r24j4p1': False},
            'edge-ports': {'x3000c0r24j8p0': True, 'x3000c0r24j8p1': False}
        }
        actual = self.fabric_client.get_fabric_edge_ports_enabled_status()
        self.assertEqual(expected, actual)

    def test_get_fabric_edge_ports_status_api_error(self):
        """Test getting enabled status of fabric and edge ports w/ APIError."""
        self.get_api_err = True

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports_enabled_status()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element(self.fabric_status_fail_msg, cm.output)
        self.assert_in_element(self.edge_status_fail_msg, cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_status_bad_json(self):
        """Test getting enabled status of fabric and edge ports w/ JSON parse error."""
        self.json_value_err = True

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports_enabled_status()

        self.assertEqual(2, len(cm.output))
        self.assert_in_element(self.fabric_status_fail_msg, cm.output)
        self.assert_in_element(self.edge_status_fail_msg, cm.output)
        self.assertEqual({}, actual)

    def test_get_fabric_edge_ports_status_missing_key(self):
        """Test getting enabled status of fabric and edge ports w/ missing 'ports' key."""
        del self.mock_port_set_status['fabric-ports']['ports']
        expected = {
            'edge-ports': {'x3000c0r24j8p0': True, 'x3000c0r24j8p1': False}
        }

        with self.assertLogs(level=logging.WARNING) as cm:
            actual = self.fabric_client.get_fabric_edge_ports_enabled_status()

        self.assertEqual(1, len(cm.output))
        self.assert_in_element(self.fabric_status_fail_msg, cm.output)
        self.assertEqual(expected, actual)


class TestCAPMCError(unittest.TestCase):
    """Tests for the CAPMCError custom Exception class."""
    def setUp(self):
        self.err_msg = 'Some CAPMC error'

    def test_with_no_xnames(self):
        """Test CAPMCError with no xnames argument."""
        err = sat.apiclient.CAPMCError(self.err_msg)
        self.assertEqual(self.err_msg, str(err))

    def test_with_empty_xnames(self):
        """Test CAPMCError with empty list of xnames."""
        err = sat.apiclient.CAPMCError(self.err_msg)
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
        err = sat.apiclient.CAPMCError(self.err_msg, xname_errs=xnames)
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
        err = sat.apiclient.CAPMCError(base_err_msg, xname_errs=xnames)
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

        self.mock_post = mock.patch('sat.apiclient.APIGatewayClient.post').start()
        self.mock_post.return_value.json.return_value = {'e': 0, 'err_msg': '', 'xnames': []}

        self.capmc_client = sat.apiclient.CAPMCClient()

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
        self.mock_post.side_effect = sat.apiclient.APIError('failure')
        power_state = 'on'
        expected_err = rf'Failed to power {power_state} xname\(s\): {", ".join(self.xnames)}'
        with self.assertRaisesRegex(sat.apiclient.CAPMCError, expected_err):
            self.capmc_client.set_xnames_power_state(self.xnames, power_state)

    def test_set_xnames_power_state_value_err(self):
        """Test set_xnames_power_state with ValueError when trying to parse JSON response."""
        self.mock_post.return_value.json.side_effect = ValueError("bad JSON")
        power_state = 'on'
        expected_err = (rf'Failed to parse JSON in response from CAPMC API when powering '
                        rf'{power_state} xname\(s\): {", ".join(self.xnames)}')
        with self.assertRaisesRegex(sat.apiclient.CAPMCError, expected_err):
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
        with self.assertRaisesRegex(sat.apiclient.CAPMCError, expected_err):
            self.capmc_client.set_xnames_power_state(self.xnames, power_state)


class TestCAPMCClientGetState(ExtendedTestCase):
    """Test the CAPMClient methods to get power state."""

    def setUp(self):
        self.xnames = ['x1000c0s0b0n0', 'x1000c0s1b0n0']
        self.post_params = {'xnames': self.xnames}

        self.mock_post = mock.patch('sat.apiclient.APIGatewayClient.post').start()
        self.mock_post.return_value.json.return_value = {
            'e': 0,
            'err_msg': '',
            'on': self.xnames[:1],
            'off': self.xnames[1:]
        }

        self.capmc_client = sat.apiclient.CAPMCClient()

    def tearDown(self):
        mock.patch.stopall()

    def test_get_xnames_power_state_success(self):
        """Test get_xnames_power_state in successful case."""
        nodes_by_state = self.capmc_client.get_xnames_power_state(self.xnames)
        expected = {'on': self.xnames[:1], 'off': self.xnames[1:]}
        self.assertEqual(expected, nodes_by_state)

    def test_get_xnames_power_state_api_err(self):
        """Test get_xnames_power_state with APIError."""
        self.mock_post.side_effect = sat.apiclient.APIError('failure')
        expected_err = rf'Failed to get power state of xname\(s\): {", ".join(self.xnames)}'
        with self.assertRaisesRegex(sat.apiclient.CAPMCError, expected_err):
            self.capmc_client.get_xnames_power_state(self.xnames)

    def test_get_xnames_power_state_value_err(self):
        """Test get_xnames_power_state with a ValueError when parsing JSON."""
        self.mock_post.side_effect = ValueError('bad JSON')
        expected_err = (rf'Failed to parse JSON in response from CAPMC API when '
                        rf'getting power state of xname\(s\): {", ".join(self.xnames)}')
        with self.assertRaisesRegex(sat.apiclient.CAPMCError, expected_err):
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
        capmc_client = sat.apiclient.CAPMCClient(suppress_warnings=True)
        with self.assertLogs(level=logging.DEBUG) as cm:
            capmc_client.get_xnames_power_state(self.xnames)

        self.assertEqual(logging.getLevelName(logging.DEBUG), cm.records[0].levelname)
        self.assertEqual(cm.records[0].message, expected_msg)

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
        with self.assertRaisesRegex(sat.apiclient.CAPMCError, expected_err):
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
        with self.assertRaisesRegex(sat.apiclient.CAPMCError, expected_err):
            self.capmc_client.get_xname_power_state(xname)


if __name__ == '__main__':
    unittest.main()
