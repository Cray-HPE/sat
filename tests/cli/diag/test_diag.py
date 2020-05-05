from json.decoder import JSONDecodeError
import unittest
from unittest import mock

import requests

from sat.cli import diag

# These sample Redfish API responses are taken from
# https://connect.us.cray.com/confluence/display/ASICD/Shasta+Controller+Diagnostics+Usage
MOCK_XNAME = 'x0c0r0b0'
MOCK_DIAG_COMMAND = 'runMemtester'
MOCK_DIAG_ARGS = ['-h']

MOCK_POST_RESPONSE = r"""
{
    "@odata.context": "/redfish/v1/$metadata#Task.Task(Description,TaskState,Name,Id)",
    "@odata.id": "/redfish/v1/TaskService/Tasks/1",
    "@odata.type": "#Task.v1_1_0.Task",
    "Description": "Task for runMemTester",
    "Id": "1",
    "Name": "runMemTester",
    "TaskState": "New"
}
"""

MOCK_GET_RESPONSE = r"""
{
    "@odata.context": "/redfish/v1/$metadata#Task.Task(StartTime,TaskState,Id,EndTime,Messages,Name,Description)",
    "@odata.etag": "W/\"1568405585\"",
    "@odata.id": "/redfish/v1/TaskService/Tasks/1",
    "@odata.type": "#Task.v1_1_0.Task",
    "Description": "Task for runMemTester",
    "EndTime": "2019-09-13T20:13:05+00:00",
    "Id": "1",
    "Messages": [
        {
            "@odata.type": "#Message.v1_0_5.Message",
            "Message": "[Redacted for simplicity.]",
            "MessageId": "CrayDiagnostics.1.0.DiagnosticStdout",
            "Resolution": "None",
            "Severity": "OK"
        }
    ],
    "Name": "runMemTester",
    "StartTime": "2019-09-13T20:13:05+00:00",
    "TaskState": "Completed"
}
"""


class DiagStatusTestCase(unittest.TestCase):
    def setUp(self):
        self.rq_post_mock = mock.MagicMock()
        self.rq_post_mock.return_value.text = MOCK_POST_RESPONSE
        mock.patch('sat.cli.diag.redfish.requests.Session.post', self.rq_post_mock).start()

        self.rq_get_mock = mock.MagicMock()
        self.rq_get_mock.return_value.text = MOCK_GET_RESPONSE
        mock.patch('sat.cli.diag.redfish.requests.Session.get', self.rq_get_mock).start()

        self.rq_del_mock = mock.MagicMock()
        mock.patch('sat.cli.diag.redfish.requests.Session.delete', self.rq_del_mock).start()

        self.initial_status = diag.redfish.DiagStatus.initiate_diag(MOCK_XNAME, 'user', 'pass',
                                                                    MOCK_DIAG_COMMAND, MOCK_DIAG_ARGS)

    def tearDown(self):
        mock.patch.stopall()


class TestDiagStatusClass(DiagStatusTestCase):
    """Tests for the DiagStatus class."""
    def test_diag_status_has_correct_attrs(self):
        """Test that the object's attributes are set correctly after updating."""
        self.assertTrue(all(hasattr(self.initial_status, attr) for attr in
                            ['odata_context', 'odata_id', 'odata_type',
                             'description', 'xname', 'id', 'name', 'taskstate']))

    def test_diag_status_malformed_json(self):
        """Test that malformed JSON will return status None."""
        self.rq_post_mock.return_value.text = '{"No closing quote or brace'
        self.assertEqual(diag.redfish.DiagStatus.initiate_diag(MOCK_XNAME, 'user', 'pass',
                                                               MOCK_DIAG_COMMAND, MOCK_DIAG_ARGS), None)

    def test_diag_status_update_content(self):
        """Test if status of the diagnostic can be updated."""
        self.initial_status._update_content(MOCK_GET_RESPONSE)
        self.assertEqual(self.initial_status.taskstate, "Completed")

    def test_diag_status_update_malformed_json(self):
        """Test if bad JSON input doesn't change diag status."""
        with self.assertRaises(JSONDecodeError):
            self.initial_status._update_content('{"TaskState": "No closing quote or brace')

        self.assertEqual(self.initial_status.taskstate, 'New')


class TestRedfishQueries(DiagStatusTestCase):
    """Tests for functions which query Redfish APIs"""

    def test_request_payload(self):
        """Test if diag scheduling payloads are created correctly."""
        payload = diag.redfish._request_payload('foo', ['bar', '--baz'])
        self.assertEqual(payload.get('Name'), 'foo')
        self.assertEqual(payload.get('Options'), 'bar --baz')

    def test_running_diag_on_target(self):
        """Test if diag run requests are posted successfully."""
        self.rq_post_mock.assert_called_once_with(
            'https://x0c0r0b0/redfish/v1/Managers/BMC/Actions/Oem/CrayProcess.Schedule',
            json={'Name': 'runMemtester', 'Options': '-h'})

        for k, v in [('id', '1'), ('name', 'runMemTester'), ('taskstate', 'New')]:
            self.assertEqual(getattr(self.initial_status, k), v)

    def test_run_diag_returns_none_on_error(self):
        """Test if None is returned if xname can't be accessed."""
        self.rq_post_mock.return_value = None
        self.rq_post_mock.side_effect = requests.exceptions.RequestException()

        self.assertEqual(diag.redfish.DiagStatus.initiate_diag(MOCK_XNAME, 'user', 'pass',
                                                               'foo', ['bar', '--baz']), None)

    def test_update_diag_status(self):
        """Test if updating the diag status works properly."""
        self.initial_status.poll()
        for k, v in [('id', '1'), ('name', 'runMemTester'), ('taskstate', 'Completed'),
                     ('starttime', '2019-09-13T20:13:05+00:00'),
                     ('endtime', '2019-09-13T20:13:05+00:00')]:
            self.assertEqual(getattr(self.initial_status, k),  v)

    def test_update_diag_status_do_nothing_on_error(self):
        """Test if a malformed repsonse doesn't update anything."""
        self.rq_get_mock.return_value = None
        self.rq_get_mock.side_effect = requests.exceptions.RequestException()

        self.initial_status.poll()
        self.assertEqual(self.initial_status.name, 'runMemTester')

    def test_can_cancel_task(self):
        """Test if we can cancel a task."""
        self.initial_status.delete()
        self.rq_del_mock.assert_called_once_with('https://x0c0r0b0/redfish/v1/TaskService/Tasks/1')


if __name__ == '__main__':
    unittest.main()
