"""
Contains classes and functions for checking, freezing and restarting Ceph.

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
import json
import logging
import socket
import subprocess
import sys

from paramiko import SSHClient, SSHException

from sat.cli.bootsys.util import get_mgmt_ncn_hostnames
from sat.cli.bootsys.waiting import Waiter
from sat.config import get_config_value
from sat.util import BeginEndLogger

LOGGER = logging.getLogger(__name__)


class CephHealthWaiter(Waiter):
    """Waiter for the Ceph cluster health status."""

    def __init__(self, timeout, poll_interval=1, allow_ceph_health_warn=False):
        self.host = 'ncn-m001'

        self.ssh_client = SSHClient()
        self.ssh_client.load_system_host_keys()
        self.ssh_client.connect(self.host)
        self.allow_ceph_health_warn = allow_ceph_health_warn

        super().__init__(timeout, poll_interval=poll_interval)

    def condition_name(self):
        return "Ceph cluster in healthy state"

    def has_completed(self):
        try:
            ceph_command = 'ceph -s --format=json'
            _, stdout, _ = self.ssh_client.exec_command(ceph_command)

        except SSHException:
            LOGGER.error('Failed to execute command "%s" on host "%s".', ceph_command, self.host)
            return False

        try:
            rsp_dict = json.load(stdout)

        except json.decoder.JSONDecodeError as jde:
            LOGGER.error('Received malformed response from Ceph: %s', jde)
            return False

        try:
            # TODO: If the Ceph health criteria are updated, this will
            # need to be changed. (See SAT-559 for further
            # information.)
            acceptable_statuses = ['HEALTH_OK', 'HEALTH_WARN'] if self.allow_ceph_health_warn else ['HEALTH_OK']
            return rsp_dict['health']['status'] in acceptable_statuses

        except KeyError:
            LOGGER.error('Ceph JSON response is well-formed, but has an unexpected schema.')

            if 'health' not in rsp_dict:
                LOGGER.error('Missing top-level "health" key in Ceph JSON response.')
            elif 'status' not in rsp_dict['health']:
                LOGGER.error('Missing "status" key under "health" key in Ceph JSON response.')

            return False


def restart_ceph_services():
    """Restart ceph services on the storage nodes.

    This uses the hosts file to get the list of nodes designated as
    'storage' nodes.

    It iterates first over the nodes on which to restart the services,
    and then over the services to restart, restarting all the services for
    one node before proceeding to the next node.  This is different from the
    documented Shasta 1.3 procedure, on which this function is based.  The
    documented procedure restarts one service across all the nodes before
    proceeding to the next service.

    Raises:
        SystemExit: if connecting to one of the hosts failed, or if restarting
            one of the services failed
    """
    storage_nodes = get_mgmt_ncn_hostnames(['storage'])
    ceph_services = ['ceph-mon.target', 'ceph-mgr.target', 'ceph-mds.target']
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()

    for storage_node in storage_nodes:
        try:
            ssh_client.connect(storage_node)
        except (SSHException, socket.error) as err:
            LOGGER.error(f'Connecting to {storage_node} failed.  Error: {err}')
            raise SystemExit(1)

        for ceph_service in ceph_services:
            command = f'systemctl restart {ceph_service}'
            try:
                _, stdout, stderr = ssh_client.exec_command(f'systemctl restart {ceph_service}')
            except SSHException as err:
                LOGGER.error(f'Command "{command}" failed.  Host: {storage_node}.  Error: {err}')
                raise SystemExit(1)

            # Command may run successfully but still return nonzero, which is an error.
            # Checking return status also blocks until the command completes.
            if stdout.channel.recv_exit_status():
                LOGGER.error(f'Command "{command}" failed.  Host: {storage_node}.  Stderr: {stderr.read()}')
                raise SystemExit(1)


def validate_ceph_warning_state(ceph_check_data, expecting_osdmap_flags=False):
    """Given Ceph health check information, determine Ceph health.

    The 'ceph_check_data' dictionary contains keys which are strings
    describing types of health checks which contribute to the overall status
    of 'HEALTH_WARN'. The values of this dictionary contain more detail about
    these health checks.

    Some types of warnings are considered acceptable (for example, 'too few
    PGs per OSD' and/or 'large omap objects'). If all the 'checks' in
    ceph_check_data are considered acceptable (by checking against a list of
    known 'acceptable' warnings, then Ceph is considered healthy and the
    function will return True.

    The 'OSDMAP_FLAGS' check (indicating that one or more OSD flags are set) is
    considered acceptable but only on the condition that the specific OSD flags
    which are set are considered acceptable. If the flags are 'noout',
    'nobackfill', or 'norecover' (or any combination of the three), then Ceph
    is considered healthy. Otherwise, it is considered unhealthy.

    If Ceph is healthy with warnings, a warning is logged. If Ceph is
    unhealthy, an error is logged. However, if the only warning that
    exists is OSDMAP_FLAGS, then the warning will be skipped when
    expecting_osdmap_flags is set to True.

    For a full list of Ceph health checks, see:
    https://docs.ceph.com/en/latest/rados/operations/health-checks/

    Args:
        ceph_check_data (dict): The value of the 'checks' key in
            the 'health' dictionary returned by `ceph -s --format=json`.
        expecting_osdmap_flags (bool): If False, then log a warning even
            if the only failed health check is OSDMAP_FLAGS and the flags
            are all acceptable. Otherwise, skip logging this warning.

    Returns:
        True if the given health check information amounts to an 'acceptable'
            warning state.

    Raises:
        KeyError: if an expected dictionary key is missing.
    """
    acceptable_checks = ['LARGE_OMAP_OBJECTS', 'TOO_FEW_PGS', 'POOL_NEAR_FULL', 'OSD_NEARFULL', 'OSDMAP_FLAGS']
    unacceptable_checks_found = [check for check in ceph_check_data if check not in acceptable_checks]
    if ceph_check_data and unacceptable_checks_found:
        LOGGER.error(
            'Ceph is not healthy. The following fatal Ceph health warnings were found: %s ',
            ','.join(unacceptable_checks_found)
        )
        ceph_is_healthy = False
    elif not ceph_check_data:
        LOGGER.error('Ceph is not healthy. Ceph is in HEALTH_WARN state with unknown warnings.')
        ceph_is_healthy = False
    elif 'OSDMAP_FLAGS' in ceph_check_data:
        acceptable_flags = ['noout', 'nobackfill', 'norecover']
        try:
            summary_message = ceph_check_data['OSDMAP_FLAGS']['summary']['message']
            flags = summary_message.split()[0].split(',')
        except (IndexError, KeyError, AttributeError):
            flags = None
        if not flags:
            LOGGER.error(
                'Ceph is not healthy. The OSDMAP_FLAGS check failed with unknown OSD flags.'
            )
            ceph_is_healthy = False
        elif not all(flag in acceptable_flags for flag in flags):
            LOGGER.error(
                'Ceph is not healthy. The OSDMAP_FLAGS check failed. OSD flags: %s', ','.join(flags)
            )
            ceph_is_healthy = False
        else:
            # Ceph has OSDMAP_FLAGS, and 'acceptable' flags, and is otherwise healthy.
            ceph_is_healthy = True
    else:
        # Ceph has only 'acceptable' flags.
        ceph_is_healthy = True

    if ceph_is_healthy and (list(ceph_check_data.keys()) != ['OSDMAP_FLAGS'] or not expecting_osdmap_flags):
        LOGGER.warning('Ceph is healthy with warnings: %s', ','.join(ceph_check_data.keys()))

    return ceph_is_healthy


def ceph_healthy(expecting_osdmap_flags=False):
    """Get the current health of the Ceph cluster.

    This function uses the JSON object returned from `ceph -s --format=json`
    to determine Ceph health. The JSON object should contain a 'health' key
    whose value is a dictionary describing the health of the Ceph cluster.

    In the 'health' dictionary, there is a 'status' key whose value is a string
    describing the overall health of the Ceph cluster. If this value is 'HEALTH_OK',
    then the cluster is considered healthy, and the function will return True.

    If the status is 'HEALTH_WARN', then the function will check the dictionary
    value of the 'checks' key in the 'health' dict. For a description of how
    the 'HEALTH_WARN' status is evaluated, see validate_ceph_warning_state().

    If the status is anything other than 'HEALTH_WARN' or 'HEALTH_OK', then
    Ceph is considered unhealthy and the function will return False.

    TODO (SAT-788): Module organization and slight differences in behavior
    This function is used by do_platform_stop in platform.py, in the
    platform-services stage of `sat bootsys shutdown`, but not in the
    CephHealthWaiter class, which simply allows both HEALTH_OK and HEALTH_WARN.

    Args:
        expecting_osdmap_flags (bool): If False, then log a warning even
            if the only failed health check is OSDMAP_FLAGS and the flags
            are all acceptable. Otherwise, skip logging this warning.

    Returns:
        True if the Ceph cluster is healthy, otherwise False.
    """
    LOGGER.info('Checking Ceph health')
    ceph_command = ['ceph', '-s', '--format=json']
    try:
        ceph_command_output = subprocess.check_output(ceph_command)

    except subprocess.CalledProcessError as cpe:
        LOGGER.error('Failed to check ceph health: %s', cpe)
        return False

    try:
        ceph_response_dict = json.loads(ceph_command_output)
    except json.decoder.JSONDecodeError as jde:
        LOGGER.error('Received malformed response from Ceph: %s', jde)
        return False

    try:
        overall_status = ceph_response_dict['health']['status']
        if overall_status == 'HEALTH_OK':
            return True
        elif overall_status == 'HEALTH_WARN':
            return validate_ceph_warning_state(ceph_response_dict['health']['checks'], expecting_osdmap_flags)
        return False
    except KeyError as e:
        LOGGER.error('Ceph JSON response is missing expected key: %s', e)
        return False


def toggle_ceph_freeze_flags(freeze=True):
    """Freeze or unfreeze the Ceph cluster.

    Args:
        freeze (bool): if True, set flags to freeze Ceph, otherwise unset flags
            to unfreeze Ceph.

    Raises:
        RuntimeError: if a command failed.
    """
    action = ('unset', 'set')[freeze]
    ceph_freeze_commands = [
        ['ceph', 'osd', action, 'noout'],
        ['ceph', 'osd', action, 'norecover'],
        ['ceph', 'osd', action, 'nobackfill'],
    ]
    LOGGER.info('%s Ceph', ('Unfreezing', 'Freezing')[freeze])
    for ceph_freeze_command in ceph_freeze_commands:
        try:
            output = subprocess.check_output(ceph_freeze_command,
                                             stderr=subprocess.STDOUT)
            LOGGER.info('Running command: %s', ' '.join(ceph_freeze_command))
            LOGGER.info('Command output: %s', output.decode())
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to {("unfreeze", "freeze")[freeze]} Ceph: {e}')


def do_ceph_check(args):
    """Restart Ceph services and wait for Ceph health.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this stage.
    """
    print('Restarting ceph services and waiting for ceph to be healthy.')
    with BeginEndLogger('restart ceph services on storage nodes'):
        restart_ceph_services()

    with BeginEndLogger('wait for ceph health'):
        ceph_waiter = CephHealthWaiter(get_config_value('bootsys.ceph_timeout'))
        if not ceph_waiter.wait_for_completion():
            sys.exit(1)
        else:
            print('Ceph is healthy.')
