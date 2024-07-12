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
Manage cron job definitions on the system (i.e. those run by the cron systemd service).
"""
import logging

LOGGER = logging.getLogger(__name__)


class CronJobError(Exception):
    """Error modifying a system cron job."""
    pass


def modify_cron_job(ssh_client, hostname, job_file_path, enabled=False):
    """Disable or enable a systemd cron job.

    Disable or enable a cron job defined in the given file path by commenting
    out or uncommenting its crontab entry.

    This function can only enable or disable all crontab entries in a single
    file, e.g. a file inside the `/etc/cron.d` directory.

    Args:
        ssh_client (paramiko.SSHClient): the SSH client connected to the host
            where commands should be executed
        hostname (str): the hostname associated with the ssh_client (for logging)
        job_file_path (str): the path to the file defining the cronjob
        enabled (bool): if True, then ensure the cron job is enabled. If False,
            then ensure the cron job is disabled.

    Raises:
        paramiko.SSHException: if there is an error executing the command via SSH
        CronJobError: if there is an error while executing the command to enable
            or disable the cron job, or if the cron job should be enabled but the
            given file path does not exist
    """
    action = ('disable', 'enable')[enabled]

    _, stdout, stderr = ssh_client.exec_command(f'test -e {job_file_path}')
    exit_code = stdout.channel.recv_exit_status()
    if exit_code:
        if not enabled:
            LOGGER.info(f'Cron job {job_file_path} does not exist on {hostname}, '
                        f'so it does not need to be disabled')
            return
        else:
            raise CronJobError(
                f'Cron job {job_file_path} does not exist on {hostname}, '
                f'so it cannot be enabled'
            )

    magic_string = 'COMMENTED_BY_SAT'
    if enabled:
        # Only uncomment lines containing magic_string, which indicates SAT commented them out
        sed_cmd = fr"sed -i 's/^# {magic_string} //' {job_file_path}"
    else:
        # Add magic_string to allow us to see which lines were commented out by SAT
        sed_cmd = fr"sed -i 's/^\([^#]\)/# {magic_string} \1/' {job_file_path}"

    _, stdout, stderr = ssh_client.exec_command(sed_cmd)
    exit_code = stdout.channel.recv_exit_status()
    if exit_code:
        raise CronJobError(
            f'Command "{sed_cmd}" failed to {action} cron job {job_file_path}'
            f'on {hostname}: {stderr.read()}'
        )
