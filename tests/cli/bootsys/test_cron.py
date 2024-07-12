#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
Tests for cron job enable/disable functionality in cron module.
"""
import logging
import os
import shlex
import subprocess
from tempfile import NamedTemporaryFile
import unittest
from unittest.mock import MagicMock
import uuid

from sat.cli.bootsys.cron import CronJobError, modify_cron_job


class TestModifyCronJob(unittest.TestCase):

    def setUp(self):
        """Create temporary files containing fake cron tab entries."""
        self.enabled_cron_file = NamedTemporaryFile(mode='w', delete=False)
        self.enabled_cron_lines = [
            '# This job executes some-script.sh every minute',
            '* * * * * root /usr/bin/some-script.sh'
        ]
        self.enabled_cron_file.write('\n'.join(self.enabled_cron_lines) + '\n')
        self.enabled_cron_file.close()

        self.disabled_cron_file = NamedTemporaryFile(mode='w', delete=False)
        self.disabled_cron_lines = [
            '# This job executes another-script.sh every hour on the hour',
            '# COMMENTED_BY_SAT 0 * * * * root /usr/bin/another-script.sh'
        ]
        self.disabled_cron_file.write('\n'.join(self.disabled_cron_lines) + '\n')
        self.disabled_cron_file.close()

        self.other_disabled_cron_file = NamedTemporaryFile(mode='w', delete=False)
        self.other_disabled_cron_lines = [
            '# This job executes yet-another-script.sh every day at midnight',
            '# 0 0 * * * root /usr/bin/yet-another-script.sh'
        ]
        self.other_disabled_cron_file.write('\n'.join(self.other_disabled_cron_lines) + '\n')
        self.other_disabled_cron_file.close()

        def fake_ssh_exec_command(command):
            """Fake execution of a command via SSH by executing it locally."""
            process = subprocess.run(shlex.split(command), capture_output=True)
            stdin = MagicMock()
            stderr = MagicMock()
            stdout = MagicMock()
            stdout.channel.recv_exit_status.return_value = process.returncode
            return stdin, stdout, stderr

        self.mock_ssh_client = MagicMock()
        self.mock_ssh_client.exec_command.side_effect = fake_ssh_exec_command

    def tearDown(self):
        os.remove(self.enabled_cron_file.name)
        os.remove(self.disabled_cron_file.name)

    def test_disable_enabled_cron_job(self):
        """Test disabling an enabled cron job"""
        modify_cron_job(self.mock_ssh_client, 'localhost', self.enabled_cron_file.name, enabled=False)
        with open(self.enabled_cron_file.name) as f:
            self.assertEqual(
                [
                    self.enabled_cron_lines[0],
                    f'# COMMENTED_BY_SAT {self.enabled_cron_lines[1]}'
                ],
                f.read().splitlines()
            )

    def test_disable_then_enable_cron_job(self):
        """Test disabling and then re-enabling a cron job results in no changes."""
        modify_cron_job(self.mock_ssh_client, 'localhost', self.enabled_cron_file.name, enabled=False)
        modify_cron_job(self.mock_ssh_client, 'localhost', self.enabled_cron_file.name, enabled=True)
        with open(self.enabled_cron_file.name) as f:
            self.assertEqual(self.enabled_cron_lines, f.read().splitlines())

    def test_disable_disabled_cron_job(self):
        """Test disabling a disabled cron job"""
        modify_cron_job(self.mock_ssh_client, 'localhost', self.disabled_cron_file.name, enabled=False)
        with open(self.disabled_cron_file.name) as f:
            self.assertEqual(
                self.disabled_cron_lines,
                f.read().splitlines()
            )

    def test_enable_disabled_cron_job(self):
        """Test enabling a disabled cron job"""
        modify_cron_job(self.mock_ssh_client, 'localhost', self.disabled_cron_file.name, enabled=True)
        with open(self.disabled_cron_file.name) as f:
            self.assertEqual(
                [
                    self.disabled_cron_lines[0],
                    '0 * * * * root /usr/bin/another-script.sh'
                ],
                f.read().splitlines()
            )

    def test_enable_enabled_cron_job(self):
        """Test enabling an already enabled cron job"""
        modify_cron_job(self.mock_ssh_client, 'localhost', self.enabled_cron_file.name, enabled=True)
        with open(self.enabled_cron_file.name) as f:
            self.assertEqual(self.enabled_cron_lines, f.read().splitlines())

    def test_enable_then_disable_cron_job(self):
        """Test enabling and then disabling a disable cron job results in no changes"""
        modify_cron_job(self.mock_ssh_client, 'localhost', self.disabled_cron_file.name, enabled=True)
        modify_cron_job(self.mock_ssh_client, 'localhost', self.disabled_cron_file.name, enabled=False)
        with open(self.disabled_cron_file.name) as f:
            self.assertEqual(self.disabled_cron_lines, f.read().splitlines())

    def test_enable_cron_job_not_disabled_by_sat(self):
        """Test enabling a cron job that was not disabled by SAT"""
        modify_cron_job(self.mock_ssh_client, 'localhost', self.other_disabled_cron_file.name, enabled=True)
        with open(self.other_disabled_cron_file.name) as f:
            self.assertEqual(self.other_disabled_cron_lines, f.read().splitlines())

    def test_disable_non_existent_cron_job(self):
        """Test disabling a non-existent cronjob"""
        non_existent_file_path = f'/some/non/existent/file/path/{uuid.uuid4()}'
        with self.assertLogs(level=logging.INFO) as logs_cm:
            modify_cron_job(self.mock_ssh_client, 'localhost', non_existent_file_path, enabled=False)
        self.assertEqual(1, len(logs_cm.records))
        self.assertEqual(f'Cron job {non_existent_file_path} does not exist on localhost, '
                         f'so it does not need to be disabled',
                         logs_cm.records[0].message)

    def test_enable_non_existent_cron_job(self):
        """Test enabling a non-existent cronjob"""
        non_existent_file_path = f'/some/non/existent/file/path/{uuid.uuid4()}'
        with self.assertRaisesRegex(CronJobError,
                                    f'Cron job {non_existent_file_path} does not '
                                    f'exist on localhost, so it cannot be enabled'):
            modify_cron_job(self.mock_ssh_client, 'localhost', non_existent_file_path, enabled=True)


if __name__ == '__main__':
    unittest.main()
