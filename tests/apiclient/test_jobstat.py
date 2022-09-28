#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.apiclient.jobstat
"""

from copy import deepcopy
import unittest
from unittest.mock import Mock, patch
from uuid import uuid4

from sat.apiclient import APIError, APIGatewayClient
from sat.apiclient.jobstat import JobstatClient


MOCK_JOBS = [
    {
        'apid': str(uuid4()),
        'jobid': 'pbs-host',
        'user': '100',
        'command': '/bin/echo',
        'state': 'completed',
        'num_nodes': 2,
        'node_list': 'nid001,nid002'
    },
    {
        'apid': str(uuid4()),
        'jobid': 'pbs-host2',
        'user': '100',
        'command': '/bin/echo',
        'state': 'completed',
        'num_nodes': 2,
        'node_list': 'nid001,nid002'
    }
]

MOCK_JOBSTAT_RESPONSE = {
    'jobstat': MOCK_JOBS,
    'errorcode': 0,
    'errormessage': 'success',
    'timereported': '2022-09-21T18:02:29'
}


class TestJobstatClient(unittest.TestCase):
    """Test the Jobstat client."""
    def setUp(self):
        """Set up mocks."""
        mock_session = Mock(host='mock_host')
        self.jobstat_client = JobstatClient(mock_session, timeout=0)
        self.mock_get = patch.object(APIGatewayClient, 'get').start()
        self.mock_response = deepcopy(
            MOCK_JOBSTAT_RESPONSE
        )
        self.mock_get.return_value.json.return_value = self.mock_response

    def tearDown(self):
        """Stop patches."""
        patch.stopall()

    def test_successful(self):
        """Test a successful call to the jobstat service."""
        expected = MOCK_JOBSTAT_RESPONSE['jobstat']
        actual = self.jobstat_client.get_all()
        self.assertEqual(expected, actual)

    def test_successful_without_errors(self):
        """If the error fields no longer exist, still return the jobstat data."""
        del self.mock_response['errorcode']
        del self.mock_response['errormessage']
        expected = MOCK_JOBSTAT_RESPONSE['jobstat']
        actual = self.jobstat_client.get_all()
        self.assertEqual(expected, actual)

    def test_successful_null_errors(self):
        """If errorcode and errormessage are null, return the jobstat data."""
        self.mock_response['errorcode'] = None
        self.mock_response['errormessage'] = None
        expected = MOCK_JOBSTAT_RESPONSE['jobstat']
        actual = self.jobstat_client.get_all()
        self.assertEqual(expected, actual)

    def test_no_data(self):
        """Test the case when the API unexpectedly returns no data."""
        self.mock_get.return_value.json.return_value = {}
        with self.assertRaisesRegex(APIError, r'Failed to get State Checker data '
                                              r'due to missing \'jobstat\' key in response'):
            self.jobstat_client.get_all()

    def test_http_error(self):
        """Test the case when the API returns an error."""
        self.mock_get.side_effect = APIError
        with self.assertRaises(APIError):
            self.jobstat_client.get_all()

    def test_invalid_json(self):
        self.mock_get.return_value.json.side_effect = ValueError
        with self.assertRaises(APIError):
            self.jobstat_client.get_all()
