"""
Unit tests for sat.config

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

from unittest import mock
import unittest

from sat.apiclient import APIGatewayClient, HSMClient
import sat.config


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
            client = APIGatewayClient()

        self.assertEqual(client.host, default_host)

    def test_create_with_host(self):
        """Test creation of APIGatewayClient w/ host."""
        api_gw_host = 'my-api-gw'
        client = APIGatewayClient(None, api_gw_host)
        self.assertEqual(client.host, api_gw_host)

    @mock.patch('requests.get')
    def test_get_no_params(self, mock_requests_get):
        """Test get method with no additional params."""
        api_gw_host = 'my-api-gw'
        client = APIGatewayClient(None, api_gw_host)
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
        client = APIGatewayClient(None, api_gw_host)
        path_components = ['People']
        params = {'name': 'ryan'}
        response = client.get(*path_components, params=params)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            params=params, verify=True
        )
        self.assertEqual(response, mock_requests_get.return_value)


class TestHSMClient(unittest.TestCase):
    """Tests for the APIGatewayClient class."""

    def setUp(self):
        self.stored_config = sat.config.CONFIG
        sat.config.CONFIG = sat.config.SATConfig('')

    def tearDown(self):
        sat.config.CONFIG = self.stored_config

    @mock.patch('requests.get')
    def test_get_inventory(self, mock_requests_get):
        """Test get method with an inventory path"""
        api_gw_host = 'my-api-gw'
        client = HSMClient(None, 'my-api-gw')
        path_components = ['Inventory', 'Hardware']
        response = client.get(*path_components)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) +
            HSMClient.base_resource_path +
            '/'.join(path_components),
            params=None, verify=True
        )
        self.assertEqual(response, mock_requests_get.return_value)


if __name__ == '__main__':
    unittest.main()
