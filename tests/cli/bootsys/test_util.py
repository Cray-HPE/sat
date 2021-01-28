"""
Tests for common bootsys code.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
from textwrap import dedent
import unittest
from unittest.mock import call, mock_open, patch

from sat.cli.bootsys.util import get_mgmt_ncn_hostnames, RunningService


class TestGetNcns(unittest.TestCase):

    def setUp(self):
        """Set up a mock open function for the hosts file."""
        self.hosts_file_contents = dedent("""\
            10.252.2.14     ncn-s003 ncn-s003.local ncn-s003.nmn
            10.252.2.13     ncn-s002 ncn-s002.local ncn-s002.nmn
            10.252.2.12     ncn-s001 ncn-s001.local ncn-s001.nmn
            10.252.2.18     ncn-w003 ncn-w003.local ncn-w003.nmn
            10.252.2.9      ncn-w002 ncn-w002.local ncn-w002.nmn
            10.252.2.8      ncn-w001 ncn-w001.local ncn-w001.nmn
            10.252.2.15     ncn-m003 ncn-m003.local ncn-m003.nmn
            10.252.2.16     ncn-m002 ncn-m002.local ncn-m002.nmn
            #10.252.2.19     ncn-m001 ncn-m001.local ncn-m001.nmn
            10.252.2.20     uan01 uan01.nmn  # Repurposed ncn-w004
            10.252.2.100    rgw-vip rgw-vip.local rgw rgw.local
        """)
        patch('builtins.open', mock_open(read_data=self.hosts_file_contents)).start()

    def tearDown(self):
        """Stop the patches."""
        patch.stopall()

    def test_get_managers(self):
        """Test getting hostnames of all managers."""
        # Note that ncn-m001 is commented out
        expected = {'ncn-m002', 'ncn-m003'}
        actual = get_mgmt_ncn_hostnames(['managers'])
        self.assertEqual(expected, actual)

    def test_get_workers(self):
        """Test getting hostnames of all workers."""
        expected = {'ncn-w001', 'ncn-w002', 'ncn-w003'}
        actual = get_mgmt_ncn_hostnames(['workers'])
        self.assertEqual(expected, actual)

    def test_get_storage(self):
        """Test getting hostnames of all storage nodes."""
        expected = {'ncn-s001', 'ncn-s002', 'ncn-s003'}
        actual = get_mgmt_ncn_hostnames(['storage'])
        self.assertEqual(expected, actual)

    def test_get_all_ncns(self):
        """Test getting hostnames of all managers, workers, and storage nodes."""
        # Note that ncn-m001 is commented out
        expected = {'ncn-m002', 'ncn-m003',
                    'ncn-w001', 'ncn-w002', 'ncn-w003',
                    'ncn-s001', 'ncn-s002', 'ncn-s003'}
        actual = get_mgmt_ncn_hostnames(['managers', 'workers', 'storage'])
        self.assertEqual(expected, actual)

    def test_get_invalid_subrole(self):
        """Test getting hostnames with an invalid subrole included."""
        subroles = ['managers', 'impostors', 'workers']
        with self.assertRaisesRegex(ValueError, r'Invalid subroles given: impostors'):
            get_mgmt_ncn_hostnames(subroles)

    def test_get_invalid_subroles(self):
        """Test getting hostnames with multiple invalid subroles included."""
        subroles = ['managers', 'impostors', 'workers', 'crewmates']
        with self.assertRaisesRegex(ValueError, r'Invalid subroles given: impostors, crewmates'):
            get_mgmt_ncn_hostnames(subroles)

    def test_get_workers_substring(self):
        """Test getting worker NCN hostnames with tricky hostnames in the hosts file."""
        hosts_file_contents = dedent("""\
            10.252.2.7      not-ncn-w002 not-ncn-w002.local not-ncn-w002.nmn
            10.252.2.8      ncn-w001 ncn-w001.local ncn-w001.nmn
            10.252.3.8      ncn-w002.someothernet
        """)
        expected = {'ncn-w001'}
        with patch('builtins.open', mock_open(read_data=hosts_file_contents)):
            actual = get_mgmt_ncn_hostnames(['workers'])
        self.assertEqual(expected, actual)

    def test_get_workers_no_newline(self):
        """Test getting worker NCN hostname from last line without trailing whitespace."""
        hosts_file_contents = dedent("""\
            10.252.2.7      ncn-w001
            10.252.2.8      ncn-w002
            10.252.2.9      ncn-w003""")
        expected = {'ncn-w001', 'ncn-w002', 'ncn-w003'}
        with patch('builtins.open', mock_open(read_data=hosts_file_contents)):
            actual = get_mgmt_ncn_hostnames(['workers'])
        self.assertEqual(expected, actual)

    @patch('builtins.open', side_effect=FileNotFoundError('dne'))
    def test_get_ncns_hosts_file_error(self, _):
        """Test getting NCNs when hosts file cannot be opened."""
        with self.assertLogs(level=logging.ERROR) as cm:
            actual = get_mgmt_ncn_hostnames(['managers'])
        self.assertEqual(cm.records[0].message, 'Unable to read /etc/hosts to obtain '
                                                'management NCN hostnames: dne')
        self.assertEqual(set(), actual)


class TestRunningService(unittest.TestCase):
    """Tests for the RunningService class."""
    def setUp(self):
        self.svc_name = 'foo'

    @patch('sat.cli.bootsys.util.subprocess.check_call')
    def test_systemctl_start(self, mock_check_call):
        """Test starting systemd services."""
        svc = RunningService(self.svc_name)
        svc._systemctl_start_stop(True)
        mock_check_call.assert_called_once_with(['systemctl', 'start', self.svc_name])

    @patch('sat.cli.bootsys.util.subprocess.check_call')
    def test_systemctl_stop(self, mock_check_call):
        """Test stopping systemd services."""
        svc = RunningService(self.svc_name)
        svc._systemctl_start_stop(False)
        mock_check_call.assert_called_once_with(['systemctl', 'stop', self.svc_name])

    @patch('time.sleep')
    @patch('sat.cli.bootsys.util.RunningService._systemctl_start_stop')
    def test_running_service_context_manager(self, mock_start_stop, mock_sleep):
        """Test that the RunningService manager starts, then stops the service"""
        with RunningService(self.svc_name):
            pass

        mock_start_stop.assert_has_calls([call(True), call(False)])
        mock_sleep.assert_not_called()

    @patch('time.sleep')
    @patch('sat.cli.bootsys.util.RunningService._systemctl_start_stop')
    def test_running_service_context_manager_sleep(self, mock_start_stop, mock_sleep):
        """Test that the RunningService manager starts, sleeps, then stops the service"""
        sleep_time = 5
        with RunningService(self.svc_name, sleep_after_start=sleep_time):
            pass

        mock_start_stop.assert_has_calls([call(True), call(False)])
        mock_sleep.assert_called_once_with(sleep_time)
