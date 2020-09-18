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
            params=None, verify=True
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
            params=params, verify=True
        )
        self.assertEqual(response, mock_requests_get.return_value)

    @mock.patch('requests.get', side_effect=requests.exceptions.RequestException)
    def test_get_exception(self, mock_requests_get):
        """Test get method with exception during GET."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        with self.assertRaises(sat.apiclient.APIError):
            response = client.get(*path_components, params=None)

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
            data=payload, verify=True, json=None
        )
        self.assertEqual(response, mock_requests_post.return_value)

    @mock.patch('requests.post', side_effect=requests.exceptions.RequestException)
    def test_post_exception(self, mock_requests_post):
        """Test post method with exception during POST."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        payload = {}
        with self.assertRaises(sat.apiclient.APIError):
            response = client.post(*path_components, payload=payload)

    @mock.patch('requests.put')
    def test_put(self, mock_requests_put):
        """Test put method."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        payload = {}
        response = client.put(*path_components, payload=payload)

        mock_requests_put.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            data=payload, verify=True
        )

    @mock.patch('requests.put', side_effect=requests.exceptions.RequestException)
    def test_put_exception(self, mock_requests_put):
        """Test put method with exception during PUT."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        payload = {}
        with self.assertRaises(sat.apiclient.APIError):
            response = client.put(*path_components, payload=payload)

    @mock.patch('requests.delete')
    def test_delete(self, mock_requests_delete):
        """Test delete method."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        response = client.delete(*path_components)

        mock_requests_delete.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            verify=True
        )
        self.assertEqual(response, mock_requests_delete.return_value)

    @mock.patch('requests.delete', side_effect=requests.exceptions.RequestException)
    def test_delete_exception(self, mock_requests_delete):
        """Test delete method with exception during DELETE."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        with self.assertRaises(sat.apiclient.APIError):
            response = client.delete(*path_components)


class TestHSMClient(unittest.TestCase):
    """Tests for the APIGatewayClient class: HSM client."""

    def setUp(self):
        self.stored_config = sat.config.CONFIG
        sat.config.CONFIG = sat.config.SATConfig('')

    def tearDown(self):
        sat.config.CONFIG = self.stored_config

    @mock.patch('requests.get')
    def test_get_inventory(self, mock_requests_get):
        """Test call of get method through HSM client."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.HSMClient(host='my-api-gw')
        path_components = ['Inventory', 'Hardware']
        response = client.get(*path_components)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) +
            sat.apiclient.HSMClient.base_resource_path +
            '/'.join(path_components),
            params=None, verify=True
        )
        self.assertEqual(response, mock_requests_get.return_value)


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


if __name__ == '__main__':
    unittest.main()
