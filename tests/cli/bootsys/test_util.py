"""
Tests for common bootsys code.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
import subprocess
import unittest
from unittest.mock import patch, call

from sat.cli.bootsys.util import get_ncns, RunningService, run_ansible_playbook


class TestGetNcns(unittest.TestCase):
    def test_get_groups_with_no_exclude(self):
        """Test getting NCNs without excludes"""
        all_ncns = {'foo', 'bar', 'baz'}
        with patch('sat.cli.bootsys.util.get_groups', side_effect=[all_ncns, set()]):
            self.assertEqual(all_ncns, get_ncns([]))

    def test_get_groups_with_exclude(self):
        """Test getting NCNs with exclusions"""
        all_ncns = {'foo', 'bar', 'baz'}
        exclusions = {'foo'}
        with patch('sat.cli.bootsys.util.get_groups', side_effect=[all_ncns, exclusions]):
            result = get_ncns([])
            self.assertEqual(result, {'bar', 'baz'})


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


class TestRunAnsiblePlaybok(unittest.TestCase):

    def setUp(self):
        self.mock_subprocess_run = patch('sat.cli.bootsys.util.subprocess.run').start()

    def tearDown(self):
        patch.stopall()

    def test_running_playbook(self):
        """Test running a successful Ansible playbook."""
        stdout = 'some output'
        self.mock_subprocess_run.return_value.stdout = stdout
        self.mock_subprocess_run.return_value.returncode = 0

        path = '/foo/bar/baz/quux.yml'
        returned_stdout = run_ansible_playbook(path)
        self.mock_subprocess_run.assert_called_once_with(['ansible-playbook', path],
                                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                         encoding='utf-8')
        self.assertEqual(stdout, returned_stdout)

    def test_running_playbook_with_opts(self):
        """Test running a playbook with some options."""
        stdout = 'some output'
        self.mock_subprocess_run.return_value.stdout = stdout
        self.mock_subprocess_run.return_value.returncode = 0

        path = 'playbook.yml'
        returned_stdout = run_ansible_playbook(path, opts='--skip-tags prompt')
        self.mock_subprocess_run.assert_called_once_with(['ansible-playbook', '--skip-tags', 'prompt', path],
                                                         stdout=subprocess.PIPE, stderr=subprocess.PIPE,
                                                         encoding='utf-8')
        self.assertEqual(stdout, returned_stdout)

    def test_running_playbook_os_error_exit(self):
        """Test running Ansible playbook with OSError causes SystemExit."""
        self.mock_subprocess_run.side_effect = OSError

        with self.assertRaises(SystemExit):
            run_ansible_playbook('playbook.yml')

    def test_running_playbook_failure_exit(self):
        """Test running Ansible playbook that fails causes SystemExit"""
        self.mock_subprocess_run.return_value.returncode = 1

        with self.assertRaises(SystemExit):
            run_ansible_playbook('playbook.yml')

    def test_running_playbook_os_error_no_exit(self):
        """Test running Ansible playbook with OSError and exit_on_err=False."""
        self.mock_subprocess_run.side_effect = OSError
        self.assertIsNone(run_ansible_playbook('playbook.yml', exit_on_err=False))

    def test_running_playbook_failure_no_exit(self):
        """Test running Ansible playbook that fails with exit_on_err=False."""
        self.mock_subprocess_run.return_value.returncode = 1
        self.assertIsNone(run_ansible_playbook('playbook.yml', exit_on_err=False))
