"""
Unit tests for sat.apiclient.fox

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

from copy import deepcopy
import json
import unittest
from unittest.mock import Mock, patch

from tests.common import ExtendedTestCase
from tests.cli.diag.fakes import (
    MOCK_FOX_GET_RESPONSE,
    MOCK_FOX_GET_XNAME_RESPONSE,
    MOCK_FOX_JOB_ID,
    MOCK_FOX_POST_RESPONSE,
    MOCK_HMJTD_NEW_RESPONSE,
    MOCK_HMJTD_RUNNING_RESPONSE,
    MOCK_XNAMES
)

from sat.apiclient import APIGatewayClient, APIError
from sat.apiclient import FoxClient


class TestFoxClient(ExtendedTestCase):
    def setUp(self):
        """Set up mocks."""
        self.mock_get = patch.object(APIGatewayClient, 'get').start()
        self.mock_post = patch.object(APIGatewayClient, 'post').start()
        self.mock_delete = patch.object(APIGatewayClient, 'delete')
        self.mock_get.return_value.text = json.dumps(MOCK_FOX_GET_RESPONSE)
        self.mock_post.return_value.text = json.dumps(MOCK_FOX_POST_RESPONSE)
        self.fox_client = FoxClient(Mock())
        self.job_name = 'runMemTester'
        self.job_args = ['-h']

    def tearDown(self):
        """Stop mocks."""
        patch.stopall()

    def test_initiate_diag(self):
        """Test creating a diag with FoxClient calls the post method with the expected data."""
        expected_payload = {
            'xnames': MOCK_XNAMES,
            'jobName': self.job_name,
            'options': ' '.join(self.job_args)
        }
        job_id = self.fox_client.initiate_diag(MOCK_XNAMES, self.job_name, self.job_args)
        self.mock_post.assert_called_once_with('jobpool', json=expected_payload)
        self.assertEqual(job_id, MOCK_FOX_JOB_ID)

    def test_initiate_diag_api_error(self):
        """Test an API error when creating a diag raises the error."""
        self.mock_post.side_effect = APIError
        with self.assertRaisesRegex(APIError, r'Unable to initiate diagnostics for xname\(s\)'):
            self.fox_client.initiate_diag(MOCK_XNAMES, self.job_name, self.job_args)

    def test_initiate_diag_malformed_response(self):
        """Test we raise an APIError when the response from the Fox API can't be parsed as JSON."""
        self.mock_post.return_value.text = r'{badJson'
        with self.assertRaisesRegex(APIError, 'Response from Fox contained malformed data'):
            self.fox_client.initiate_diag(MOCK_XNAMES, self.job_name, self.job_args)

    def test_initiate_diag_missing_response_key(self):
        """Test we raise an APIError when the response from the Fox API is missing an expected key."""
        mock_response = deepcopy(MOCK_FOX_POST_RESPONSE)
        del mock_response['jobID']
        self.mock_post.return_value.text = json.dumps(mock_response)
        with self.assertRaisesRegex(APIError, 'Response from Fox missing expected key'):
            self.fox_client.initiate_diag(MOCK_XNAMES, self.job_name, self.job_args)

    def test_get_job_launch_status(self):
        """Test getting the job launch status from FoxClient."""
        job_launch_status = self.fox_client.get_job_launch_status(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])
        self.assertEqual(job_launch_status, json.loads(MOCK_HMJTD_NEW_RESPONSE))
        self.mock_get.assert_called_once_with(f'jobpool/{MOCK_FOX_JOB_ID}')

    def test_get_job_launch_status_api_error(self):
        """Test an API error when getting a diag launch status raises the error"""
        self.mock_get.side_effect = APIError
        with self.assertRaisesRegex(APIError, 'Unable to determine launch status for'):
            self.fox_client.get_job_launch_status(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_launch_status_malformed_response(self):
        """Test we raise an APIError when the response from the Fox API can't be parsed as JSON."""
        self.mock_get.return_value.text = r'{badJson'
        with self.assertRaisesRegex(APIError, 'Response from Fox contained malformed data'):
            self.fox_client.get_job_launch_status(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_launch_status_missing_key(self):
        """Test we raise an APIError when the response from the Fox API is missing an expected key."""
        mock_response = deepcopy(MOCK_FOX_GET_RESPONSE)
        del mock_response['tasks']
        self.mock_get.return_value.text = json.dumps(mock_response)
        with self.assertRaisesRegex(APIError, 'Response from Fox missing expected key'):
            self.fox_client.get_job_launch_status(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_launch_status_missing_launch_message(self):
        """Test we return an empty dictionary when the launchMessage field is missing."""
        mock_response = deepcopy(MOCK_FOX_GET_RESPONSE)
        del mock_response['tasks'][0]['launchMessage']
        self.mock_get.return_value.text = json.dumps(mock_response)
        launch_status = self.fox_client.get_job_launch_status(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])
        self.assertEqual(launch_status, {})

    def test_get_job_launch_status_hmjtd_malformed_response(self):
        """Test we raise an APIError when the string-ified JSON from HMJTD can't be parsed."""
        mock_response = deepcopy(MOCK_FOX_GET_RESPONSE)
        mock_response['tasks'][0]['launchMessage'] = r'{badJson'
        self.mock_get.return_value.text = json.dumps(mock_response)
        with self.assertRaisesRegex(APIError, 'Fox response contained malformed data from HMJTD'):
            self.fox_client.get_job_launch_status(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_launch_status_hmjtd_wrong_type(self):
        """Test we raise an APIError when the string-ified JSON from HMJTD is not the right type."""
        mock_response = deepcopy(MOCK_FOX_GET_RESPONSE)
        mock_response['tasks'][0]['launchMessage'] = 1234
        self.mock_get.return_value.text = json.dumps(mock_response)
        with self.assertRaisesRegex(APIError, 'Fox response contained malformed data from HMJTD'):
            self.fox_client.get_job_launch_status(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_status_for_xname(self):
        """Test getting the job status for an xname."""
        self.mock_get.return_value.text = json.dumps(MOCK_FOX_GET_XNAME_RESPONSE)
        job_status = self.fox_client.get_job_status_for_xname(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])
        self.assertEqual(job_status, json.loads(MOCK_HMJTD_RUNNING_RESPONSE))

    def test_get_job_status_for_xname_api_error(self):
        """Test we raise an APIError when the response from the Fox API can't be parsed as JSON."""
        self.mock_get.side_effect = APIError
        with self.assertRaisesRegex(APIError, 'Unable to get job status for'):
            self.fox_client.get_job_status_for_xname(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_status_for_xname_malformed_response(self):
        """Test we raise an APIError when the response from the Fox API can't be parsed as JSON."""
        self.mock_get.return_value.text = r'{badJson'
        with self.assertRaisesRegex(APIError, 'Response from Fox contained malformed data'):
            self.fox_client.get_job_status_for_xname(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_status_for_xname_missing_key(self):
        """Test we raise an APIError when the response from the Fox API is missing an expected key."""
        mock_response = deepcopy(MOCK_FOX_GET_XNAME_RESPONSE)
        del mock_response['message']
        self.mock_get.return_value.text = json.dumps(mock_response)
        with self.assertRaisesRegex(APIError, 'Response from Fox missing expected key'):
            self.fox_client.get_job_status_for_xname(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_status_for_xname_hmjtd_malformed_response(self):
        """Test we raise an APIError when the string-ified JSON from HMJTD can't be parsed."""
        mock_response = deepcopy(MOCK_FOX_GET_XNAME_RESPONSE)
        mock_response['message'] = r'{badJson'
        self.mock_get.return_value.text = json.dumps(mock_response)
        with self.assertRaisesRegex(APIError, 'Fox response contained malformed data from HMJTD'):
            self.fox_client.get_job_status_for_xname(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])

    def test_get_job_status_for_xname_hmjtd_wrong_type(self):
        """Test we raise an APIError when the string-ified JSON from HMJTD is not the right type."""
        mock_response = deepcopy(MOCK_FOX_GET_XNAME_RESPONSE)
        mock_response['message'] = 1234
        self.mock_get.return_value.text = json.dumps(mock_response)
        with self.assertRaisesRegex(APIError, 'Fox response contained malformed data from HMJTD'):
            self.fox_client.get_job_status_for_xname(MOCK_FOX_JOB_ID, MOCK_XNAMES[0])


if __name__ == '__main__':
    unittest.main()
