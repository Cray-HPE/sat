"""
Unit tests for sat.apiclient.gateway

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
from unittest import mock
import unittest

import requests

import sat.apiclient
import sat.config
from sat.apiclient import APIError


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
        with mock.patch('sat.apiclient.gateway.get_config_value', return_value=default_host):
            client = sat.apiclient.APIGatewayClient()

        self.assertEqual(client.host, default_host)

    def test_create_with_host(self):
        """Test creation of APIGatewayClient w/ host."""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        self.assertEqual(client.host, api_gw_host)

    def test_configured_timeout(self):
        """Make sure the API client timeout is configurable by the config file."""
        with mock.patch('sat.apiclient.gateway.get_config_value') as mock_config:
            for configured_timeout in range(10, 60, 10):
                mock_config.return_value = configured_timeout
                client = sat.apiclient.APIGatewayClient()
                self.assertEqual(client.timeout, configured_timeout)

    def test_setting_timeout_with_constructor(self):
        """Test setting the API client timeout with the constructor argument."""
        with mock.patch('sat.apiclient.gateway.get_config_value', return_value=120):
            client = sat.apiclient.APIGatewayClient(timeout=60)
            self.assertEqual(client.timeout, 60)

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

    def test_request_failed_with_problem_description(self):
        """Test get, post, put, patch, and delete with fail HTTP codes and additional problem details"""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path = 'fail'
        expected_url = f'{get_http_url_prefix(api_gw_host)}{path}'
        status_code = 400
        reason = 'Bad Request'
        problem_title = 'Title of problem'
        problem_detail = 'Details of problem and how to fix it'

        verbs_to_test = ['get', 'post', 'put', 'patch', 'delete']
        for verb in verbs_to_test:
            with self.subTest(verb=verb):
                with mock.patch(f'requests.{verb}') as mock_request_func:
                    mock_response = mock.Mock(ok=False, status_code=status_code, reason=reason)
                    mock_response.json.return_value = {
                        'title': problem_title,
                        'detail': problem_detail
                    }
                    mock_request_func.return_value = mock_response

                    err_regex = (f"{verb.upper()} request to URL '{expected_url}' failed with status "
                                 f"code {status_code}: {reason}. {problem_title} Detail: {problem_detail}")

                    with self.assertRaisesRegex(APIError, err_regex):
                        kwargs = {}
                        if verb in ('put', 'patch'):
                            # put and patch methods require a payload keyword-only argument
                            kwargs['payload'] = {}
                        getattr(client, verb)(path, **kwargs)

    def test_request_failed_no_problem_description(self):
        """Test get, post, put, patch, and delete with fail HTTP codes and no problem details"""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path = 'fail'
        expected_url = f'{get_http_url_prefix(api_gw_host)}{path}'
        status_code = 400
        reason = 'Bad Request'

        verbs_to_test = ['get', 'post', 'put', 'patch', 'delete']
        for verb in verbs_to_test:
            with self.subTest(verb=verb):
                with mock.patch(f'requests.{verb}') as mock_request_func:
                    mock_response = mock.Mock(ok=False, status_code=status_code, reason=reason)
                    mock_response.json.return_value = {}
                    mock_request_func.return_value = mock_response

                    err_regex = (f"{verb.upper()} request to URL '{expected_url}' failed with "
                                 f"status code {status_code}: {reason}")

                    with self.assertRaisesRegex(APIError, err_regex):
                        kwargs = {}
                        if verb in ('put', 'patch'):
                            # put and patch methods require a payload keyword-only argument
                            kwargs['payload'] = {}
                        getattr(client, verb)(path, **kwargs)

    def test_request_failed_invalid_json_response(self):
        """Test get, post, put, patch, and delete with fail HTTP codes and response not valid JSON"""
        api_gw_host = 'my-api-gw'
        client = sat.apiclient.APIGatewayClient(host=api_gw_host)
        path = 'fail'
        expected_url = f'{get_http_url_prefix(api_gw_host)}{path}'
        status_code = 400
        reason = 'Bad Request'

        verbs_to_test = ['get', 'post', 'put', 'patch', 'delete']
        for verb in verbs_to_test:
            with self.subTest(verb=verb):
                with mock.patch(f'requests.{verb}') as mock_request_func:
                    mock_response = mock.Mock(ok=False, status_code=status_code, reason=reason)
                    mock_response.json.side_effect = ValueError
                    mock_request_func.return_value = mock_response

                    err_regex = (f"{verb.upper()} request to URL '{expected_url}' failed with "
                                 f"status code {status_code}: {reason}")

                    with self.assertRaisesRegex(APIError, err_regex):
                        kwargs = {}
                        if verb in ('put', 'patch'):
                            # put and patch methods require a payload keyword-only argument
                            kwargs['payload'] = {}
                        getattr(client, verb)(path, **kwargs)


if __name__ == '__main__':
    unittest.main()
