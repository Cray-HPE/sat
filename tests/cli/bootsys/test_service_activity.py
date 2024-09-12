#
# MIT License
#
# (C) Copyright 2020-2024 Hewlett Packard Enterprise Development LP
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
Unit tests for the service_activity module.
"""
from collections import OrderedDict
from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException
import logging
import socket
import unittest
from unittest.mock import call, MagicMock, Mock, patch

from paramiko.ssh_exception import BadHostKeyException, AuthenticationException, SSHException

from tests.common import ExtendedTestCase
from sat.apiclient import APIError
from sat.cli.bootsys.service_activity import (
    ServiceActivityChecker,
    ServiceCheckError,
    SDUActivityChecker,
    BOSV1ActivityChecker,
    BOSV2ActivityChecker,
    CFSActivityChecker,
    FirmwareActivityChecker,
    NMDActivityChecker,
    _report_active_sessions,
    do_service_activity_check
)
from sat.report import Report


class MockPodList:
    """A fake return value for list_namespaced_pods."""
    def __init__(self, items):
        self.items = items


class MockPod:
    """A fake pod for the items returned by list_namespaced_pods."""
    def __init__(self, label_value, phase):
        self.status = Mock()
        self.label_value = label_value
        self.status.phase = phase


class TestServiceActivityChecker(unittest.TestCase):
    """Test the properties defined in the ServiceActivityChecker."""

    def setUp(self):
        """Define a class that implements ServiceActivityChecker."""
        class CustomActivityChecker(ServiceActivityChecker):
            def __init__(self):
                super().__init__()
                self.service_name = 'SVC'
                self.session_name = 'session'
                self.cray_cli_args = 'svc session describe'
                self.id_field_name = 'session_id'

            def get_active_sessions(self):
                return []

        self.custom_class = CustomActivityChecker

    def test_service_activity_checker_properties(self):
        """Test the properties of the ServiceActivityChecker."""
        checker = self.custom_class()
        self.assertEqual('Active SVC Sessions', checker.report_title)
        self.assertEqual('cray svc session describe SESSION_ID',
                         checker.cray_cli_command)
        self.assertEqual('active SVC sessions', checker.active_sessions_desc)

    def test_service_activity_checker_get_err(self):
        """Test the get_err method of the ServiceActivityChecker."""
        checker = self.custom_class()
        err = checker.get_err('utter failure')
        self.assertEqual('Unable to get active SVC sessions: utter failure',
                         str(err))


class TestSDUActivityChecker(ExtendedTestCase):
    """Test the SDUActivityChecker class."""
    def setUp(self):
        self.mock_channel = MagicMock()
        self.mock_channel.recv_exit_status.side_effect = [1, 1, 1]

        self.mock_transport = MagicMock()
        self.mock_transport.open_session.return_value = self.mock_channel

        self.mock_ssh_client_instance = MagicMock()
        self.mock_ssh_client_instance.get_transport.return_value = self.mock_transport

        self.mock_ssh_client = patch('sat.cli.bootsys.service_activity.get_ssh_client').start()
        self.mock_ssh_client.return_value = self.mock_ssh_client_instance

        self.mock_get_mgmt_ncn_groups = patch('sat.cli.bootsys.service_activity.get_mgmt_ncn_groups').start()
        self.mock_get_mgmt_ncn_groups.return_value = ({'managers': ['ncn-m001', 'ncn-m002', 'ncn-m003']}, {})

    def tearDown(self):
        patch.stopall()

    def assert_ssh_client_set_up(self):
        self.mock_ssh_client_instance.connect.assert_called()
        self.mock_ssh_client_instance.close.assert_called()

    def test_getting_sdu_sessions_none_running(self):
        """Test no active SDU sessions returned when no dumps are occurring."""
        s = SDUActivityChecker()

        self.assertEqual(s.get_active_sessions(), [])
        self.assert_ssh_client_set_up()

    def test_getting_sdu_sessions_one_running(self):
        """Test active SDU sessions are returned when remote dumps are occurring."""
        s = SDUActivityChecker()
        self.mock_channel.recv_exit_status.side_effect = [1, 0, 1]

        self.assertEqual(s.get_active_sessions(), [OrderedDict([('ncn', 'ncn-m002')])])
        self.assert_ssh_client_set_up()

    def test_exception_thrown_on_ssh_error(self):
        """Test an exception is thrown when SSH error occurs when checking SDU sessions."""
        mock_bad_host_key_exception = BadHostKeyException('ncn-m002', MagicMock(), MagicMock())
        for err_type in [mock_bad_host_key_exception, AuthenticationException,
                         SSHException, socket.error]:
            s = SDUActivityChecker()
            self.mock_ssh_client_instance.connect.side_effect = err_type
            with self.assertRaises(ServiceCheckError):
                self.assertEqual(s.get_active_sessions(), [])
        self.assert_ssh_client_set_up()

    def test_exception_thrown_on_open_session_error(self):
        """Test an exception is thrown when there is a problem opening the SSH channel."""
        self.mock_transport.open_session.side_effect = SSHException
        with self.assertRaises(ServiceCheckError):
            SDUActivityChecker().get_active_sessions()
        self.assert_ssh_client_set_up()

    def test_exception_thrown_on_exec_command_error(self):
        """Test an exception is thrown when there is a problem executing remote commands."""
        self.mock_channel.exec_command.side_effect = SSHException
        with self.assertRaises(ServiceCheckError):
            SDUActivityChecker().get_active_sessions()
        self.assert_ssh_client_set_up()

    def test_exception_thrown_on_remote_pgrep_error(self):
        """Test that exceptions are thrown when error return codes are given from remote pgrep."""
        self.mock_channel.recv_exit_status.side_effect = None

        for returncode in [2, 3, 5]:
            self.mock_channel.recv_exit_status.return_value = returncode
            s = SDUActivityChecker()
            with self.assertRaises(ServiceCheckError):
                s.get_active_sessions()

    def test_exception_not_thrown_when_sdu_not_installed_or_configured(self):
        """Test that exceptions are not thrown when SDU cannot be accessed."""
        self.mock_channel.recv_exit_status.side_effect = None

        for returncode in [125, 127]:
            self.mock_channel.recv_exit_status.return_value = returncode
            s = SDUActivityChecker()
            try:
                s.get_active_sessions()
            except ServiceCheckError:
                self.fail(f"ServiceCheckError was thrown on SDU return code "
                          f"{returncode}")


class TestBOSV1ActivityChecker(ExtendedTestCase):
    """Test the BOSV1ActivityChecker class."""

    def setUp(self):
        """Set up mocks and sample BOS data."""
        self.mock_get_config_value = patch(
            'sat.cli.bootsys.service_activity.get_config_value',
            return_value='v1',
        ).start()

        self.session_template_id = 'cle-1.3.0'
        self.bos_session_details = {
            '1': {
                'bos_launch': 'bos_launch_1',
                'computes': 'boot_pcs_finished',
                'session_template_id': self.session_template_id,
                'operation': 'shutdown',
                'boa_launch': 'boa_launch_1',
                'stage': 'Done'
            },
            '2': {
                'bos_launch': 'bos_launch_2',
                'computes': 'boot_pcs_finished',
                'session_template_id': self.session_template_id,
                'operation': 'configure',
                'boa_launch': 'boa_launch_2',
                'stage': 'Done'
            },
            '3': {
                'bos_launch': 'bos_launch_3',
                'computes': 'boot_pcs_finished',
                'session_template_id': self.session_template_id,
                'operation': 'reboot',
                'boa_launch': 'boa_launch_3',
            }
        }
        self.bos_session_ids = list(self.bos_session_details.keys())

        self.missing_session_message = 'Could not find session.'

        def mock_bos_get(*args):
            def json():
                if not args or args[0] != 'session':
                    self.fail('Unexpected get to BOSV1Client with args: {}'.format(args))
                elif len(args) == 1:
                    return self.bos_session_ids
                else:
                    try:
                        return self.bos_session_details[args[1]]
                    except KeyError:
                        raise APIError(self.missing_session_message)
            return Mock(json=json)

        patch('sat.cli.bootsys.service_activity.SATSession').start()
        self.mock_bos_client = patch(
            'sat.cli.bootsys.service_activity.BOSClientCommon.get_bos_client').start()
        self.mock_bos_client.return_value.get = mock_bos_get

        # This can be overridden in test methods to test other scenarios.
        self.pods = [
            MockPod('boa-1', 'Failed'),
            MockPod('boa-2', 'Succeeded'),
            MockPod('boa-1', 'Succeeded'),
            MockPod('boa-3', 'Failed'),
            MockPod('boa-3', 'Failed'),
            MockPod('boa-3', 'Pending')
        ]

        def mock_list_pods(_, **kwargs):
            if 'label_selector' in kwargs:
                label_value = kwargs['label_selector'].split('=', 1)[1]
                return MockPodList([pod for pod in self.pods
                                    if pod.label_value == label_value])
            return MockPodList(self.pods)

        self.mock_kube_client = Mock()
        self.mock_kube_client.list_namespaced_pod = mock_list_pods
        self.mock_load_kube_api = patch(
            'sat.cli.bootsys.service_activity.load_kube_api',
            return_value=self.mock_kube_client).start()

        self.bos_checker = BOSV1ActivityChecker()

    def tearDown(self):
        """Stop mocks at the end of each unit test."""
        patch.stopall()

    def test_init(self):
        """Test creation of a BOSV1ActivityChecker."""
        self.assertEqual('BOS', self.bos_checker.service_name)
        self.assertEqual('session', self.bos_checker.session_name)
        self.assertEqual('bos v1 session describe', self.bos_checker.cray_cli_args)
        self.assertEqual('session_id', self.bos_checker.id_field_name)

    def test_get_active_sessions_one_active(self):
        """Test get_active_sessions with one active session."""
        active_sessions = self.bos_checker.get_active_sessions()
        expected_active_sessions = [
            OrderedDict([
                ('session_id', '3'),
                ('bos_launch', 'bos_launch_3'),
                ('operation', 'reboot'),
                ('stage', 'MISSING'),
                ('session_template_id', self.session_template_id)
            ])
        ]
        self.assertEqual(expected_active_sessions, active_sessions)

    def test_get_active_sessions_none_active(self):
        """Test get_active_sessions with no active sessions."""
        self.pods = [
            MockPod('boa-1', 'Failed'),
            MockPod('boa-2', 'Succeeded'),
            MockPod('boa-3', 'Unknown'),
        ]
        active_sessions = self.bos_checker.get_active_sessions()
        self.assertEqual([], active_sessions)

    def test_get_active_sessions_all_active(self):
        """Test get_active_sessions with all sessions active."""
        self.pods = [
            MockPod('boa-1', 'Failed'),
            MockPod('boa-1', 'Pending'),
            MockPod('boa-2', 'Running'),
            MockPod('boa-3', 'Pending')
        ]
        active_sessions = self.bos_checker.get_active_sessions()
        expected_active_sessions = [
            OrderedDict([
                ('session_id', '1'),
                ('bos_launch', 'bos_launch_1'),
                ('operation', 'shutdown'),
                ('stage', 'Done'),
                ('session_template_id', self.session_template_id)
            ]),
            OrderedDict([
                ('session_id', '2'),
                ('bos_launch', 'bos_launch_2'),
                ('operation', 'configure'),
                ('stage', 'Done'),
                ('session_template_id', self.session_template_id)
            ]),
            OrderedDict([
                ('session_id', '3'),
                ('bos_launch', 'bos_launch_3'),
                ('operation', 'reboot'),
                ('stage', 'MISSING'),
                ('session_template_id', self.session_template_id)
            ])
        ]
        self.assertEqual(expected_active_sessions, active_sessions)

    def test_get_active_sessions_missing_pods(self):
        """Test get_active_sessions with some pods missing for sessions."""
        self.pods = [
            MockPod('boa-1', 'Failed'),
            # No pod matching the session with id 2
            MockPod('boa-3', 'Succeeded')
        ]
        # No sessions have active pods, so we expect no active sessions
        active_sessions = self.bos_checker.get_active_sessions()
        self.assertEqual([], active_sessions)

    def test_get_active_sessions_bos_sessions_err(self):
        """Test get_active_sessions with BOS failing to get sessions."""
        api_err_msg = 'internal error'
        self.mock_bos_client.return_value.get = Mock(
            side_effect=APIError(api_err_msg))
        err_regex = r'^Unable to get active BOS sessions: {}'.format(api_err_msg)
        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            self.bos_checker.get_active_sessions()

    def test_get_active_sessions_bos_session_get_err(self):
        """Test get_active_sessions with BOS failing to GET a session id"""
        # Add an id that does not appear in self.bos_session_details
        self.bos_session_ids.append('4')

        with self.assertLogs(level=logging.WARNING) as cm:
            self.bos_checker.get_active_sessions()

        self.assert_in_element('Unable to get details about BOS session 4: '
                               '{}'.format(self.missing_session_message),
                               cm.output)

    def test_get_active_sessions_kube_config_err(self):
        """Test get_active_sessions with failure to load kube_config."""
        config_err_msg = 'invalid config'
        # Newer version of kubernetes raise this
        self.mock_load_kube_api.side_effect = ConfigException(config_err_msg)
        err_regex_template = ('^Unable to get active BOS sessions: Failed to '
                              'load kubernetes config to get BOA pod status: {}')
        err_regex = err_regex_template.format(config_err_msg)

        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            self.bos_checker.get_active_sessions()

    def test_get_active_sessions_list_pods_err(self):
        """Test get_active_sessions with a failure to list pods."""
        api_err_msg = 'list pods failed'
        err_regex = (r'^Unable to get active BOS sessions: Unable to get BOA '
                     r'pod status for BOS session 1: \({}\)'.format(api_err_msg))
        self.mock_kube_client.list_namespaced_pod = Mock(
            side_effect=ApiException(api_err_msg))

        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            self.bos_checker.get_active_sessions()


class TestBOSV2ActivityChecker(unittest.TestCase):
    """Test the BOSV2ActivityChecker class."""

    def setUp(self):
        self.mock_bos_client = MagicMock()
        patch('sat.cli.bootsys.service_activity.BOSClientCommon.get_bos_client',
              return_value=self.mock_bos_client).start()

    def test_finding_no_sessions(self):
        """Test that the BOSV2ServiceChecker returns no sessions when no sessions exist"""
        self.mock_bos_client.get_sessions.return_value = []
        self.assertEqual(len(BOSV2ActivityChecker().get_active_sessions()), 0)

    def test_finding_only_complete_sessions(self):
        """Test that the BOSV2ServiceChecker returns no sessions when all are complete"""
        self.mock_bos_client.get_sessions.return_value = [
            {
                'name': f'abcdef-0123456-789098-fdebcda-{n}',
                'operation': 'shutdown',
                'template_name': 'some-session-template',
                'status': {'status': 'complete'}
            }
            for n in range(10)
        ]
        self.assertEqual(len(BOSV2ActivityChecker().get_active_sessions()), 0)

    def test_finding_incomplete_sessions(self):
        """Test that the BOSV2ServiceChecker returns sessions which are not complete"""
        num_sessions = 10
        for status in ['running', 'pending']:
            with self.subTest(status=status):
                sessions = [
                    {
                        'name': f'abcdef-0123456-789098-fdebcda-{n}',
                        'operation': ['boot', 'reboot', 'shutdown'][n % 3],
                        'template_name': 'some-session-template',
                        'status': {'status': status}
                    }
                    for n in range(num_sessions)
                ]
                self.mock_bos_client.get_sessions.return_value = sessions

                active_sessions = BOSV2ActivityChecker().get_active_sessions()
                self.assertEqual(len(active_sessions), num_sessions)

                for active_session in active_sessions:
                    self.assertTrue(any(session['name'] == active_session['name']
                                        for session in sessions))

    def test_api_error_when_querying_sessions(self):
        """Test that a warning is logged and no sessions returned if APIError on session query"""
        self.mock_bos_client.get_sessions.side_effect = APIError
        with self.assertLogs(level='WARNING'), self.assertRaises(ServiceCheckError):
            BOSV2ActivityChecker().get_active_sessions()


class TestCFSActivityChecker(unittest.TestCase):
    """Test the CFSActivityChecker class."""

    def get_cfs_session(self, **kwargs):
        """Get a CFS session data structure.

        Args:
            **kwargs: Keyword arguments used as values in CFS session.
        """
        return {
            'name': kwargs.get('name', self.default_name),
            'status': {
                'session': {
                    'status': kwargs.get('status', self.default_status),
                    'startTime': kwargs.get('startTime', self.default_start_time),
                    'succeeded': kwargs.get('succeeded', self.default_succeeded),
                    'job': kwargs.get('job', self.default_job)
                }
            }
        }

    def setUp(self):
        """Set up mocks and sample CFS data."""
        self.cfs_checker = CFSActivityChecker()

        self.default_name = 'default-name'
        self.default_status = 'complete'
        self.default_start_time = '2020-05-20T18:20:27+00:00'
        self.default_succeeded = 'true'
        self.default_job = 'cfs-abcde12345'

        self.cfs_sessions = [
            self.get_cfs_session(name='cfs-session-{}'.format(num))
            for num in range(5)
        ]

        # If not None, causes CFSClient().get() to raise this
        self.cfs_err = None
        # If not None, causes CFSClient().get().json() to raise this
        self.json_err = None

        def mock_cfs_get(*args):
            if self.cfs_err:
                raise self.cfs_err

            def json():
                if len(args) != 1 or args[0] != 'sessions':
                    self.fail('Unexpected get to CFSClient with args: {}'.format(args))
                elif self.json_err:
                    raise self.json_err
                else:
                    return self.cfs_sessions
            return Mock(json=json)

        patch('sat.cli.bootsys.service_activity.SATSession').start()
        self.mock_cfs_client = patch(
            'sat.cli.bootsys.service_activity.CFSClientBase.get_cfs_client').start()
        self.mock_cfs_client.return_value.get = mock_cfs_get

    def tearDown(self):
        """Stop mocks at the end of each unit test."""
        patch.stopall()

    def test_init(self):
        """Test creation of a CFSActivityChecker."""
        self.assertEqual('CFS', self.cfs_checker.service_name)
        self.assertEqual('session', self.cfs_checker.session_name)
        self.assertEqual('cfs sessions describe', self.cfs_checker.cray_cli_args)
        self.assertEqual('name', self.cfs_checker.id_field_name)

    def test_get_active_sessions_two_active(self):
        """Test get_active_sessions with two active sessions."""
        self.cfs_sessions[0]['status']['session']['status'] = 'running'
        self.cfs_sessions[-1]['status']['session']['status'] = 'pending'

        active_sessions = self.cfs_checker.get_active_sessions()
        expected_active_sessions = [
            OrderedDict([
                ('name', self.cfs_sessions[0]['name']),
                ('status', 'running'),
                ('startTime', self.default_start_time),
                ('succeeded', self.default_succeeded),
                ('job', self.default_job)
            ]),
            OrderedDict([
                ('name', self.cfs_sessions[-1]['name']),
                ('status', 'pending'),
                ('startTime', self.default_start_time),
                ('succeeded', self.default_succeeded),
                ('job', self.default_job)
            ])
        ]
        self.assertEqual(expected_active_sessions, active_sessions)

    def test_get_active_sessions_api_err(self):
        """Test get_active_sessions with an API error."""
        api_err_msg = 'service unavailable'
        self.cfs_err = APIError(api_err_msg)
        err_regex = '^Unable to get active CFS sessions: {}'.format(api_err_msg)
        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            self.cfs_checker.get_active_sessions()

    def test_get_active_sessions_value_err(self):
        """Test get_active_sessions"""
        val_err_msg = 'invalid json'
        self.json_err = ValueError(val_err_msg)
        err_regex = '^Unable to get active CFS sessions: {}'.format(val_err_msg)
        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            self.cfs_checker.get_active_sessions()


class TestFirmwareActivityChecker(ExtendedTestCase):
    """Test the FirmwareActivityChecker class."""

    def get_fas_action(self, **kwargs):
        """Get a FAS action data structure.

        Args:
            **kwargs: Keyword arguments used as values in FAS session.
        """
        fas_action_fields = ['actionID', 'startTime', 'state',
                             'snapshotID', 'dryrun']
        return {
            field: kwargs.get(field, self.defaults.get(field))
            for field in fas_action_fields
        }

    def setUp(self):
        self.defaults = {
            'updateID': 'fus-update-id',
            'actionID': 'fas-action-id',
            'startTime': '2020-05-22 18:29:14 UTC',
            'dryrun': False,
            'snapshotID': 'fas-snapshot-id',
            'state': 'complete'
        }

        self.fas_actions = [
            self.get_fas_action(actionID='fas-action-{}'.format(num))
            for num in range(2)
        ]

        # If not None, causes FASClient to raise this
        self.fw_err = None

        def mock_get_active_updates():
            if self.fw_err:
                raise self.fw_err
            else:
                return self.fas_actions

        self.fw_client = patch('sat.cli.bootsys.service_activity.FASClient').start().return_value
        self.fw_client.get_active_actions.side_effect = mock_get_active_updates

    def tearDown(self):
        """Stop mocks at the end of each unit test."""
        patch.stopall()

    def test_init_fas(self):
        """Test creation of a FirmwareActivityChecker with FAS"""
        fw_checker = FirmwareActivityChecker()
        self.assertEqual('FAS', fw_checker.service_name)
        self.assertEqual('action', fw_checker.session_name)
        self.assertEqual('firmware actions describe', fw_checker.cray_cli_args)
        self.assertEqual('actionID', fw_checker.id_field_name)

    def test_get_active_sessions_two_active_fas(self):
        """Test get_active_sessions with two active FAS actions."""
        fw_checker = FirmwareActivityChecker()

        expected_active_sessions = []
        for action in self.fas_actions:
            expected_active_sessions.append(OrderedDict([
                ('actionID', action['actionID']),
                ('startTime', action['startTime']),
                ('state', action['state']),
                ('snapshotID', action['snapshotID']),
                ('dryrun', action['dryrun'])
            ]))

        active_sessions = fw_checker.get_active_sessions()
        self.assertEqual(expected_active_sessions, active_sessions)

    def test_get_active_sessions_api_err(self):
        """Test get_active_sessions with an API error."""
        api_err_msg = 'service unavailable'
        self.fw_err = APIError(api_err_msg)
        fw_checker = FirmwareActivityChecker()

        err_regex = '^Unable to get active FAS actions: {}'.format(api_err_msg)
        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            fw_checker.get_active_sessions()


class TestNMDActivityChecker(unittest.TestCase):
    """Test the NMDActivityChecker class."""

    def get_nmd_request(self, **kwargs):
        """Get an NMD session data structure.

        Args:
            **kwargs: Keyword arguments used as values in NMD session.
        """
        return {
            'requestID': kwargs.get('request_id', self.default_request_id),
            'info': {
                'state': kwargs.get('state', self.default_state),
                'xname': kwargs.get('xname', self.default_xname),
                'created': kwargs.get('created', self.default_created),
            }
        }

    def setUp(self):
        """Set up mocks and sample NMD data."""
        self.nmd_checker = NMDActivityChecker()

        self.default_request_id = 'nmd-request-id'
        self.default_state = 'done'
        self.default_xname = 'x1000c0s0b0n0'
        self.default_created = '2019-08-21T20:24:28.644088+00:00'

        self.nmd_requests = [
            self.get_nmd_request(request_id='nmd-request-{}'.format(num))
            for num in range(5)
        ]

        self.nmd_err = None
        self.json_err = None

        def mock_nmd_get(*args):
            if self.nmd_err:
                raise self.nmd_err

            def json():
                if len(args) != 1 or args[0] != 'dumps':
                    self.fail('Unexpected get to NMDClient with args: {}'.format(args))
                elif self.json_err:
                    raise self.json_err
                else:
                    return self.nmd_requests
            return Mock(json=json)

        patch('sat.cli.bootsys.service_activity.SATSession').start()
        self.mock_nmd_client = patch(
            'sat.cli.bootsys.service_activity.NMDClient').start()
        self.mock_nmd_client.return_value.get = mock_nmd_get

    def tearDown(self):
        """Stop mocks at the end of each unit test."""
        patch.stopall()

    def test_init(self):
        """Test creation of a NMDActivityChecker."""
        self.assertEqual('NMD', self.nmd_checker.service_name)
        self.assertEqual('dump', self.nmd_checker.session_name)
        self.assertEqual('nmd dumps describe', self.nmd_checker.cray_cli_args)
        self.assertEqual('requestID', self.nmd_checker.id_field_name)

    def test_get_active_sessions_two_active(self):
        """Test get_active_sessions with two active sessions."""
        active_session_indices = [0, -1]
        self.nmd_requests[0]['info']['state'] = 'waiting'
        self.nmd_requests[-1]['info']['state'] = 'dump'

        expected_active_sessions = []

        for idx in active_session_indices:
            expected_active_sessions.append(OrderedDict([
                ('requestID', self.nmd_requests[idx]['requestID']),
                ('state', self.nmd_requests[idx]['info']['state']),
                ('xname', self.nmd_requests[idx]['info']['xname']),
                ('created', self.nmd_requests[idx]['info']['created']),
            ]))

        active_sessions = self.nmd_checker.get_active_sessions()
        self.assertEqual(expected_active_sessions, active_sessions)

    def test_get_active_sessions_api_err(self):
        """Test get_active_sessions with an API error."""
        api_err_msg = 'service unavailable'
        self.nmd_err = APIError(api_err_msg)
        err_regex = '^Unable to get active NMD dumps: {}'.format(api_err_msg)
        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            self.nmd_checker.get_active_sessions()

    def test_get_active_sessions_value_err(self):
        """Test get_active_sessions"""
        val_err_msg = 'invalid json'
        self.json_err = ValueError(val_err_msg)
        err_regex = '^Unable to get active NMD dumps: {}'.format(val_err_msg)
        with self.assertRaisesRegex(ServiceCheckError, err_regex):
            self.nmd_checker.get_active_sessions()


class TestReportActiveSessions(ExtendedTestCase):
    """Test the _report_active_sessions function."""

    def setUp(self):
        """Set up mocks for use in tests."""
        # Default values to use when getting Mock ServiceActivityCheckers
        self.default_title = 'Active SVC Sessions'
        self.default_service_name = 'SVC'
        self.default_cray_cli_command = 'cray svc session describe SESSION_ID'
        self.default_active_desc = 'active SVC sessions'

        self.mock_print = patch('builtins.print').start()
        self.mock_report_objects = mock_report_objects = []

        def mock_report_init(*args, **kwargs):
            mock_report = Mock(spec=Report)
            mock_report_objects.append(mock_report)
            return mock_report

        self.mock_report_cls = patch('sat.cli.bootsys.service_activity.Report').start()
        self.mock_report_cls.side_effect = mock_report_init

    def tearDown(self):
        """Stop all mocks"""
        patch.stopall()

    def get_mock_service_checker(self, num_sessions=1, svc_check_err=None,
                                 **kwargs):
        """Get a mock ServiceActivityChecker to use in tests.

        Args:
            num_sessions (int): the number of sessions to return from the
                get_active_sessions method of the checker.
            svc_check_err (ServiceCheckError): if not None, raise this exception
                in the get_active_sessions method of the checker.
            **kwargs: additional attributes to set on the Mock object.
        """
        checker = Mock(
            report_title=self.default_title,
            service_name=self.default_service_name,
            cray_cli_command=self.default_cray_cli_command,
            active_sessions_desc=self.default_active_desc
        )

        if svc_check_err:
            checker.get_active_sessions.side_effect = svc_check_err
        else:
            checker.get_active_sessions.return_value = [
                OrderedDict([
                    ('session_id', 'session_{}'.format(idx)),
                    ('status', 'active')
                ])
                for idx in range(num_sessions)
            ]

        for key, val in kwargs.items():
            setattr(checker, key, val)

        return checker

    def test_report_active_sessions_active(self):
        """Test _report_active_sessions when sessions are active."""
        bos_err_msg = 'Unable to get BOS sessions.'
        checkers = [
            self.get_mock_service_checker(
                num_sessions=0, service_name='CFS',
                active_sessions_desc='active CFS sessions'
            ),
            self.get_mock_service_checker(
                num_sessions=2, service_name='FOO',
                active_sessions_desc='active FOO sessions',
                report_title='Active FOO Sessions',
                cray_cli_command='cray foo',
                more_details='For more details, execute \'cray foo\'.',
            ),
            self.get_mock_service_checker(
                svc_check_err=ServiceCheckError(bos_err_msg),
                service_name='BOS',
                active_sessions_desc='active BOS sessions'
            ),
            self.get_mock_service_checker(
                num_sessions=1, service_name='BAR',
                active_sessions_desc='active BAR sessions',
                report_title='Active BAR Sessions',
                cray_cli_command='cray bar',
                more_details='For more details, execute \'cray bar\'.',
            ),
        ]

        with self.assertLogs(level=logging.INFO) as cm:
            active, failed = _report_active_sessions(checkers)

        self.assert_in_element(bos_err_msg, cm.output)

        # There should be active services, and one failed service
        self.assertEqual(['FOO', 'BAR'], active)
        self.assertEqual(['BOS'], failed)

        # Two reports should have been created.
        self.assertEqual(len(self.mock_report_objects), 2)

        expected_logs = ['Checking for active CFS sessions.',
                         'Found no active CFS sessions.',
                         'Checking for active FOO sessions.',
                         "Found 2 active FOO sessions. Details shown below. For more "
                         "details, execute 'cray foo'.",
                         'Checking for active CFS sessions.',
                         'Checking for active BOS sessions.',
                         'Checking for active BAR sessions.',
                         "Found 1 active BAR session. Details shown below. For more "
                         "details, execute 'cray bar'."]
        for msg in expected_logs:
            self.assert_in_element(msg, cm.output)

        self.mock_print.assert_has_calls([
            call(self.mock_report_objects[0]),
            call(self.mock_report_objects[1])
        ])

        self.mock_report_cls.assert_has_calls([
            call(['session_id', 'status'], title='Active FOO Sessions'),
            call(['session_id', 'status'], title='Active BAR Sessions')
        ])
        self.mock_report_objects[0].add_rows.assert_called_once_with(
            checkers[1].get_active_sessions.return_value
        )
        self.mock_report_objects[1].add_rows.assert_called_once_with(
            checkers[3].get_active_sessions.return_value
        )

    def test_report_active_sessions_none_active(self):
        """Test _report_active_sessions when no sessions are active."""
        checkers = [
            self.get_mock_service_checker(
                num_sessions=0, service_name='CFS',
                active_sessions_desc='active CFS sessions',
            ),
            self.get_mock_service_checker(
                num_sessions=0, service_name='FOO',
                active_sessions_desc='active FOO sessions',
                more_details='For more details, execute \'cray foo\'',
            )
        ]

        with self.assertLogs(level=logging.INFO) as cm:
            active, failed = _report_active_sessions(checkers)

        # There should be neither active nor failed services
        self.assertFalse([], active)
        self.assertEqual([], failed)

        # No reports should have been created.
        self.assertEqual(len(self.mock_report_objects), 0)

        expected_logs = ['Checking for active CFS sessions.',
                         'Found no active CFS sessions.',
                         'Checking for active FOO sessions.',
                         'Found no active FOO sessions.']

        for msg in expected_logs:
            self.assert_in_element(msg, cm.output)

        self.mock_report_cls.assert_not_called()


class TestDoServiceActivityCheck(ExtendedTestCase):
    """Test the do_service_activity_check function."""
    # TODO: Fix these tests for changes to do_service_activity_check

    def setUp(self):
        """Set up some mocks."""
        checkers_to_patch = ['BOSV1', 'BOSV2', 'CFS', 'Firmware', 'NMD', 'SDU']
        self.checkers = []
        for checker in checkers_to_patch:
            path = 'sat.cli.bootsys.service_activity.{}ActivityChecker'.format(
                checker)
            self.checkers.append(patch(path).start())

        self.mock_report_active_sessions = patch(
            'sat.cli.bootsys.service_activity._report_active_sessions'
        ).start()

        self.mock_get_config_value = patch('sat.cli.bootsys.service_activity.get_config_value',
                                           return_value='v1').start()

        self.mock_args = Mock()

        self.mock_print = patch('builtins.print').start()

    def tearDown(self):
        """Stop all mock patches."""
        patch.stopall()

    def test_do_service_activity_check_active(self):
        """Test do_service_activity_check with active services."""
        self.mock_report_active_sessions.return_value = ['CFS', 'BOS'], []
        with self.assertRaises(SystemExit) as cm:
            do_service_activity_check(self.mock_args)

        self.assertEqual(1, cm.exception.code)
        self.mock_print.assert_called_once_with(
            'Active sessions exist for the following services: CFS, BOS. Allow '
            'the sessions to complete or cancel them before proceeding.'
        )

    def test_do_service_activity_check_inactive(self):
        """Test do_service_activity_check with no active services."""
        self.mock_report_active_sessions.return_value = [], []

        do_service_activity_check(self.mock_args)

        self.mock_print.assert_called_once_with(
            'No active sessions exist. It is safe to proceed with the '
            'shutdown procedure.'
        )

    def test_do_service_activity_check_active_and_failed(self):
        """Test do_service_activity_check with active services and failures."""
        self.mock_report_active_sessions.return_value = ['NMD'], ['BOS', 'CFS']

        with self.assertRaises(SystemExit) as raises_cm, \
                self.assertLogs(level=logging.ERROR) as logs_cm:
            do_service_activity_check(self.mock_args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assert_in_element('Failed to get active sessions for the '
                               'following services: BOS, CFS',
                               logs_cm.output)
        self.mock_print.assert_called_once_with(
            'Active sessions exist for the following service: NMD. Allow the '
            'sessions to complete or cancel them before proceeding.'
        )

    def test_do_service_activity_check_failed(self):
        """Test do_service_activity_check with failures."""
        self.mock_report_active_sessions.return_value = [], ['NMD', 'CFS']

        with self.assertRaises(SystemExit) as raises_cm, \
                self.assertLogs(level=logging.ERROR) as logs_cm:
            do_service_activity_check(self.mock_args)

        self.assertEqual(1, raises_cm.exception.code)
        self.assert_in_element('Failed to get active sessions for the '
                               'following services: NMD, CFS',
                               logs_cm.output)
        self.mock_print.assert_called_once_with(
            'No active sessions found in the services which could be successfully '
            'queried. Review the errors above before proceeding with the shutdown '
            'procedure.'
        )


if __name__ == '__main__':
    unittest.main()
