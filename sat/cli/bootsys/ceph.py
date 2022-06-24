#
# MIT License
#
# (C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
Contains classes and functions for checking, freezing and restarting Ceph.
"""
import json
import logging
import socket
import subprocess

from paramiko import SSHException

from sat.cli.bootsys.util import get_ssh_client
from sat.cli.bootsys.waiting import Waiter

LOGGER = logging.getLogger(__name__)


class CephHealthCheckError(Exception):
    """Ceph was determined to be unhealthy."""
    pass


class CephServiceRestartError(Exception):
    """There was an issue interacting with Ceph services."""
    pass


class CephHealthWaiter(Waiter):
    """Waiter for the Ceph cluster health status."""
    def __init__(self, timeout, storage_hosts, poll_interval=5, retries=1):
        super().__init__(timeout, poll_interval=poll_interval, retries=retries)
        self.storage_hosts = storage_hosts

    def condition_name(self):
        return "Ceph cluster in healthy state"

    def has_completed(self):
        try:
            check_ceph_health(allow_osdmap_flags=False)
            return True
        except CephHealthCheckError as err:
            LOGGER.debug('Ceph is not healthy: %s', err)
            return False

    def on_retry_action(self):
        """Restart the ceph services on all storage nodes.

        This action will restart the systemd units for the Ceph services on each
        storage node.

        Args: None.
        Returns: None.
        """
        for node in self.storage_hosts:
            client = get_ssh_client()
            try:
                try:
                    client.connect(node)
                except (SSHException, socket.error) as err:
                    raise CephServiceRestartError(err)

                _, stdout, stderr = client.exec_command('cephadm ls')
                stderr_contents = stderr.read().decode().strip()
                if stderr_contents:
                    raise CephServiceRestartError(f"Could not list Ceph systemd units: "
                                                  f"{stderr_contents}")

                try:
                    cephadm_result = json.load(stdout)
                    systemd_units = [service['systemd_unit'] for service in cephadm_result]
                except ValueError as err:
                    raise CephServiceRestartError(f"cephadm returned malformed JSON while "
                                                  f"listing services: {err}") from err
                except KeyError as err:
                    raise CephServiceRestartError(f"cephadm returned valid JSON, but it "
                                                  f"was missing the required 'systemd_unit' key")

                for systemd_unit in systemd_units:
                    LOGGER.debug("Restarting unit %s on node %s", systemd_unit, node)
                    _, _, stderr = client.exec_command(f'systemctl restart "{systemd_unit}"')
                    stderr_contents = stderr.read().decode().strip()
                    if stderr_contents:
                        raise CephServiceRestartError(f"Could not restart systemd unit {systemd_unit}: "
                                                      f"{stderr_contents}")
                    else:
                        LOGGER.debug(f"Restarted {systemd_unit} on {node}, stderr returned empty.")

            except CephServiceRestartError as err:
                LOGGER.warning("Could not restart Ceph services on storage node %s: %s", node, err)
            finally:
                client.close()


def validate_ceph_warning_state(ceph_check_data, allow_osdmap_flags=True):
    """Given Ceph health check information, determine Ceph health.

    The 'ceph_check_data' dictionary contains keys which are strings
    describing types of health checks which contribute to the overall status
    of 'HEALTH_WARN'. The values of this dictionary contain more detail about
    these health checks.

    Some types of warnings are considered acceptable (for example, 'too few
    PGs per OSD' and/or 'large omap objects'). If all the 'checks' in
    ceph_check_data are considered acceptable (by checking against a list of
    known 'acceptable' warnings, then Ceph is considered healthy.

    The 'OSDMAP_FLAGS' check (indicating that one or more OSD flags are set) is
    considered acceptable on two conditions:
        * allow_osdmap_flags is set to True.
        * The OSD flags that are set are a combination of 'noout', 'nobackfill',
          and 'norecover', i.e. the flags that are used to 'freeze' Ceph.

    If Ceph is considered healthy, then a warning is logged. If Ceph is
    considered unhealthy, then a CephHealthCheckError is raised.

    For a full list of Ceph health checks, see:
    https://docs.ceph.com/en/latest/rados/operations/health-checks/

    Args:
        ceph_check_data (dict): The value of the 'checks' key in
            the 'health' dictionary returned by `ceph -s --format=json`.
        allow_osdmap_flags (bool): if True, then certain OSD flags are
            allowed. Otherwise, the existence of any OSD flags will
            result in a CephHealthCheckError.

    Returns:
        None

    Raises:
        CephHealthCheckError: if Ceph is not healthy.
    """
    acceptable_checks = ['LARGE_OMAP_OBJECTS', 'TOO_FEW_PGS', 'POOL_NEAR_FULL', 'OSD_NEARFULL', 'OSDMAP_FLAGS']
    unacceptable_checks_found = [check for check in ceph_check_data if check not in acceptable_checks]
    if unacceptable_checks_found:
        raise CephHealthCheckError(
            f'The following fatal Ceph health warnings were found: {",".join(unacceptable_checks_found)}'
        )
    elif not ceph_check_data:
        raise CephHealthCheckError('Ceph is in HEALTH_WARN state with unknown warnings.')
    elif 'OSDMAP_FLAGS' in ceph_check_data:
        acceptable_flags = ['noout', 'nobackfill', 'norecover'] if allow_osdmap_flags else []
        try:
            summary_message = ceph_check_data['OSDMAP_FLAGS']['summary']['message']
            flags = summary_message.split()[0].split(',')
        except (IndexError, KeyError, AttributeError):
            flags = None
        if not flags:
            raise CephHealthCheckError('The OSDMAP_FLAGS check failed with unknown OSD flags.')
        elif not all(flag in acceptable_flags for flag in flags):
            raise CephHealthCheckError(f'The OSDMAP_FLAGS check failed. OSD flags: {",".join(flags)}')

    LOGGER.warning('Ceph is healthy with warnings: %s', ','.join(ceph_check_data.keys()))


def check_ceph_health(allow_osdmap_flags=True):
    """Check the current health of the Ceph cluster.

    This function uses the JSON object returned from `ceph -s --format=json`
    to determine Ceph health. The JSON object should contain a 'health' key
    whose value is a dictionary describing the health of the Ceph cluster.

    In the 'health' dictionary, there is a 'status' key whose value is a string
    describing the overall health of the Ceph cluster. If this value is 'HEALTH_OK',
    then the cluster is considered healthy, and the function will return.

    If the status is 'HEALTH_WARN', then the function will check the dictionary
    value of the 'checks' key in the 'health' dict. For a description of how
    the 'HEALTH_WARN' status is evaluated, see validate_ceph_warning_state().
    This will raise a CephHealthCheckError if Ceph is not healthy.

    If the status is anything other than 'HEALTH_WARN' or 'HEALTH_OK', then
    Ceph is considered unhealthy and the function will raise a
    CephHealthCheckError.

    Args:
        allow_osdmap_flags (bool): if True, then Ceph is considered healthy
            even when certain OSD flags are set. This is used in
            validate_ceph_warning_state.

    Returns:
        None

    Raises:
        CephHealthCheckError: if Ceph is not healthy.
    """
    LOGGER.info('Checking Ceph health')
    ceph_command = ['ceph', '-s', '--format=json']
    try:
        ceph_command_output = subprocess.check_output(ceph_command)

    except subprocess.CalledProcessError as cpe:
        raise CephHealthCheckError(f'Failed to check ceph health: {cpe}')

    try:
        ceph_response_dict = json.loads(ceph_command_output)
    except json.decoder.JSONDecodeError as jde:
        raise CephHealthCheckError(f'Received malformed response from Ceph: {jde}')

    try:
        overall_status = ceph_response_dict['health']['status']
        if overall_status == 'HEALTH_WARN':
            validate_ceph_warning_state(ceph_response_dict['health']['checks'], allow_osdmap_flags)
        elif overall_status != 'HEALTH_OK':
            raise CephHealthCheckError('Ceph health is not HEALTH_OK or HEALTH_WARN')
    except KeyError as e:
        raise CephHealthCheckError(f'Ceph JSON response is missing expected key: {e}')


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
            LOGGER.info('Command output: %s', output.decode().strip())
        except subprocess.CalledProcessError as e:
            raise RuntimeError(f'Failed to {("unfreeze", "freeze")[freeze]} Ceph: {e}')
