"""
Mock objects for unit tests for sat.cli.diag and sat.foxclient

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

from datetime import datetime
from uuid import uuid4
import json

# MHJTD POST response when a job is launched
MOCK_HMJTD_NEW_RESPONSE = r"""
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

# HMJTD POST response when a job is invalid
MOCK_HMJTD_ERROR_RESPONSE = r"""
{
  "error": {
    "@Message.ExtendedInfo": [
      {
        "@odata.type": "#Message.v1_0_5.Message",
        "Message": "[Redacted for simplicity.]",
        "MessageArgs": [
          "runDiagPowerz",
          "/redfish/v1/Managers/BMC/Actions/Oem/CrayProcess.Schedule"
        ],
        "MessageId": "Base.1.0.ActionParameterNotSupported",
        "RelatedProperties": [
          "runDiagPowerz"
        ],
        "Resolution": "Remove the parameter supplied and resubmit the request if the operation failed.",
        "Severity": "Warning"
      }
    ],
    "code": "Base.1.0.ActionParameterNotSupported",
    "message": "[Redacted for simplicity.]"
  }
}
"""

# HMJTD GET response when a job is in progress
MOCK_HMJTD_RUNNING_RESPONSE = r"""
{
    "@odata.context": "/redfish/v1/$metadata#Task.Task(Description,TaskState,Name,Id)",
    "@odata.id": "/redfish/v1/TaskService/Tasks/1",
    "@odata.type": "#Task.v1_1_0.Task",
    "Description": "Task for runMemTester",
    "Id": "1",
    "Name": "runMemTester",
    "TaskState": "Running"
}
"""

# HMJTD GET response when a job has completed
MOCK_HMJTD_COMPLETE_RESPONSE = r"""
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

# HMJTD GET response when a job has exited with an error
MOCK_HMJTD_EXCEPTION_RESPONSE = r"""
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
            "Severity": "Warning"
        }
    ],
    "Name": "runMemTester",
    "StartTime": "2019-09-13T20:13:05+00:00",
    "TaskState": "Exception"
}
"""

# Mock responses from Fox API
MOCK_FOX_JOB_ID = f'{uuid4()}'
MOCK_JOB_NAME = 'runMemTester'
MOCK_JOB_OPTIONS = '-h'
MOCK_XNAMES = ['x1000c0r1b0', 'x1000c0r2b0']
MOCK_FOX_POST_RESPONSE = {
    'jobID': MOCK_FOX_JOB_ID
}

MOCK_FOX_GET_RESPONSE = {
    'jobID': MOCK_FOX_JOB_ID,
    'jobName': MOCK_JOB_NAME,
    'options': MOCK_JOB_OPTIONS,
    'createTime': f'{datetime.now()}',
    'tasks': [
        {
            'xname': MOCK_XNAMES[0],
            'launchMessage': MOCK_HMJTD_NEW_RESPONSE
        },
        {
            'xname': MOCK_XNAMES[1],
            'launchMessage': MOCK_HMJTD_NEW_RESPONSE
        }
    ]
}

MOCK_FOX_GET_XNAME_RESPONSE = {
    'xname': 'x1000c0r1b0',
    'jobID': MOCK_FOX_JOB_ID,
    'statusCode': 200,
    'message': MOCK_HMJTD_RUNNING_RESPONSE
}


def positive_ints_generator():
    """Yield the next positive integer, used to mock time.time()"""
    ret = 0
    while True:
        yield ret
        ret += 1


def job_that_completes():
    """A generator that yields a 'running' response followed by a 'completed' response."""
    yield json.loads(MOCK_HMJTD_RUNNING_RESPONSE)
    yield json.loads(MOCK_HMJTD_COMPLETE_RESPONSE)


def job_that_runs_forever():
    """A generator that always yields a 'running' response"""
    while True:
        yield json.loads(MOCK_HMJTD_RUNNING_RESPONSE)


def job_with_exception():
    """A generator that yields an 'exception' response"""
    yield json.loads(MOCK_HMJTD_RUNNING_RESPONSE)
    yield json.loads(MOCK_HMJTD_EXCEPTION_RESPONSE)


def delayed_launch():
    """A generator that yields an empty response, followed by a successful launch."""
    yield {}
    yield json.loads(MOCK_HMJTD_NEW_RESPONSE)


def failed_launch():
    """A generator that yields a failed POST response from HMJTD"""
    yield json.loads(MOCK_HMJTD_ERROR_RESPONSE)
