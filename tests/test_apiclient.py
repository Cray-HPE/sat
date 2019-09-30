"""
Unit tests for sat.config

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from unittest import mock
import unittest

from sat.apiclient import APIGatewayClient, HSMClient


def get_http_url_prefix(hostname):
    """Construct http URL prefix to help with assertions on requests.get calls."""
    return 'https://{}/apis/'.format(hostname)


class TestAPIGatewayClient(unittest.TestCase):
    """Tests for the APIGatewayClient class."""

    def test_create_without_host(self):
        """Test creation of APIGatewayClient w/o host."""
        default_host = 'default-api-gw'
        with mock.patch('sat.apiclient.get_config_value', return_value=default_host):
            client = APIGatewayClient()

        self.assertEqual(client.host, default_host)

    def test_create_with_host(self):
        """Test creation of APIGatewayClient w/ host."""
        api_gw_host = 'my-api-gw'
        client = APIGatewayClient(api_gw_host)
        self.assertEqual(client.host, api_gw_host)

    @mock.patch('requests.get')
    def test_get_no_params(self, mock_requests_get):
        """Test get method with no additional params."""
        api_gw_host = 'my-api-gw'
        client = APIGatewayClient(api_gw_host)
        path_components = ['foo', 'bar', 'baz']
        response = client.get(*path_components)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            params=None
        )
        self.assertEqual(response, mock_requests_get.return_value)

    @mock.patch('requests.get')
    def test_get_with_params(self, mock_requests_get):
        """Test get method with additional params."""
        api_gw_host = 'my-api-gw'
        client = APIGatewayClient(api_gw_host)
        path_components = ['People']
        params = {'name': 'ryan'}
        response = client.get(*path_components, params=params)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) + '/'.join(path_components),
            params=params
        )
        self.assertEqual(response, mock_requests_get.return_value)


class TestHSMClient(unittest.TestCase):
    """Tests for the APIGatewayClient class."""

    @mock.patch('requests.get')
    def test_get_inventory(self, mock_requests_get):
        """Test get method with an inventory path"""
        api_gw_host = 'my-api-gw'
        client = HSMClient('my-api-gw')
        path_components = ['Inventory', 'Hardware']
        response = client.get(*path_components)

        mock_requests_get.assert_called_once_with(
            get_http_url_prefix(api_gw_host) +
            HSMClient.base_resource_path +
            '/'.join(path_components),
            params=None
        )
        self.assertEqual(response, mock_requests_get.return_value)


if __name__ == '__main__':
    unittest.main()
