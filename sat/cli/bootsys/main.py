"""
Entry point for the bootsys subcommand.

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
from datetime import datetime
import json
import logging
import os
import sys
from subprocess import CalledProcessError
import warnings

from kubernetes.client import CoreV1Api
from kubernetes.config import load_kube_config
from kubernetes.config.config_exception import ConfigException
from paramiko.client import SSHClient
from yaml import YAMLLoadWarning

from sat.cli.bootsys.bos import BOSFailure, do_bos_operations
from sat.cli.bootsys.defaults import DEFAULT_PODSTATE_DIR, DEFAULT_PODSTATE_FILE
from sat.cli.bootsys.mgmt_boot_power import do_mgmt_boot
from sat.cli.bootsys.mgmt_hosts import do_enable_hosts_entries
from sat.cli.bootsys.mgmt_shutdown_ansible import do_shutdown_playbook
from sat.cli.bootsys.mgmt_shutdown_power import do_mgmt_shutdown_power
from sat.cli.bootsys.service_activity import do_service_activity_check
from sat.cli.bootsys.util import k8s_pods_to_status_dict
from sat.config import get_config_value
from sat.util import get_username_and_password_interactively, prompt_continue

LOGGER = logging.getLogger(__name__)


def do_boot(args):
    """Perform a boot operation on the system.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    do_mgmt_boot(args)

    try:
        do_bos_operations('boot')
    except BOSFailure as err:
        LOGGER.error("Failed BOS boot of computes and UAN: %s", err)
        sys.exit(1)


def get_pods_as_json():
    """Get K8s pod information as a JSON string.

    Returns:
        K8s pod information as a JSON string.

    Raises:
        subprocess.CalledProcessError: if kubectl failed
        kubernetes.config.config_exception.ConfigException: if failed to load
            kubernetes config.
    """
    # Load k8s configuration before trying to use API
    try:
        with warnings.catch_warnings():
            warnings.filterwarnings('ignore', category=YAMLLoadWarning)
            load_kube_config()
    # Earlier versions: FileNotFoundError; later versions: ConfigException
    except (FileNotFoundError, ConfigException) as err:
        raise ConfigException(
            'Failed to load kubernetes config to get pod status: '
            '{}'.format(err)
        )

    k8s_api = CoreV1Api()
    all_pods = k8s_api.list_pod_for_all_namespaces()
    pods_dict = k8s_pods_to_status_dict(all_pods)

    return json.dumps(pods_dict)


def _new_file_name():
    """Helper function for _rotate_files. Returns the new filename.

    This function was created to help testing since datetime.utc was
    proving difficult to mock.
    """
    now = datetime.utcnow()
    return os.path.join(DEFAULT_PODSTATE_DIR, 'pod-state.{}.json'.format(now.strftime('%Y-%m-%dT%H:%M:%S')))


def _rotate_files():
    """Helper function for dump_pods.

    Create a new podstate file and redirect the symlink. Also removes
    podstate files until compliant with the config setting.

    Raises:
        FileNotFoundError: The directory was never created during install.
        PermissionError: User was not root.
    """
    new_file = _new_file_name()

    # create the new entry and redirect symlink.
    with open(new_file, 'w') as f:
        f.write('')

    try:
        os.remove(DEFAULT_PODSTATE_FILE)
    except FileNotFoundError:
        pass

    os.symlink(new_file, DEFAULT_PODSTATE_FILE)

    # the symlink will always be at the front.
    files = [x for x in sorted(os.listdir(DEFAULT_PODSTATE_DIR)) if x.startswith('pod-state') and x != 'pod-state.json']

    # remove number of pod states until compliant.
    max_pod_states = get_config_value('bootsys.max_pod_states')
    for i in range(len(files) - max_pod_states):
        os.remove(os.path.join(DEFAULT_PODSTATE_DIR, files[i]))


def dump_pods(path):
    """Dump pod info to a file.

    If the pod file is the same as the default, then check the count of
    files in the dir against config.bootsys.max_pod_states

    Args:
        path: Output file.

    Raises:
        CalledProcessError: Can be raised by get_pods_as_json.
        FileNotFoundError: The file could not be created.
        PermissionError: Did not have permission to write to the file.
    """
    # this can raise
    lines = get_pods_as_json()

    fnf_msg = 'Containing directory for "{}" does not exist.'.format(path)
    perm_msg = 'Insufficient permissions to write "{}".'.format(path)

    # move the symlink
    if path == DEFAULT_PODSTATE_FILE:
        try:
            _rotate_files()
        except FileNotFoundError:
            raise FileNotFoundError(fnf_msg)
        except PermissionError:
            raise PermissionError(perm_msg)

    try:
        with open(path, 'w') as f:
            f.write(lines)
    except FileNotFoundError:
        raise FileNotFoundError(fnf_msg)
    except PermissionError:
        raise PermissionError(perm_msg)


def do_shutdown(args):
    """Perform a shutdown operation on the system.

    This first dumps pod state to a file, then checks for active sessions in
    various services, and then does a BOS shutdown of all computes and UANs.

    Then it tells the user to manually run the 'platform-shutdown.yml' ansible
    playbook and then will proceed with shutting down the management NCNs and
    powering them off. In the future, that manual step will be automated.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    print('Capturing state of k8s pods.')

    try:
        dump_pods(args.pod_state_file)
    except (CalledProcessError, ConfigException, FileNotFoundError, PermissionError) as err:
        msg = str(err)
        if args.ignore_pod_failures:
            LOGGER.warning(msg)
        else:
            LOGGER.error(msg)
            sys.exit(1)

    if not args.dry_run:
        do_service_activity_check(args)

    action_msg = 'BOS shutdown of computes and UAN'
    prompt_continue(action_msg)
    try:
        do_bos_operations('shutdown')
    except BOSFailure as err:
        LOGGER.error("Failed %s: %s", action_msg, err)
        sys.exit(1)

    action_msg = 'shutdown of management platform services'
    prompt_continue(action_msg)
    do_shutdown_playbook()
    print('Succeeded with {}.'.format(action_msg))

    print('Enabling required entries in /etc/hosts for NCN mgmt interfaces.')
    do_enable_hosts_entries()

    action_msg = 'shutdown of management NCNs'
    prompt_continue(action_msg)
    username, password = get_username_and_password_interactively(username_prompt='IPMI username',
                                                                 password_prompt='IPMI password')
    ssh_client = SSHClient()
    ssh_client.load_system_host_keys()

    do_mgmt_shutdown_power(ssh_client, username, password, args.ipmi_timeout, args.dry_run)
    print('Succeeded with {}.'.format(action_msg))


def do_bootsys(args):
    """Perform a boot or shutdown operation on the system.

    A full system shutdown includes the following steps at a high level:

        * Checking for service idleness
        * Shutting down all computes and UANs using BOS
        * Shutting down management software on NCNs
        * Shutting down and powering off all NCNs

    A full system boot includes the following steps at a high level:

        * Powering on and booting all NCNs
        * Starting all management software on NCNs
        * Verifying health of management software services
        * Booting the computes and UANs using BOS

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    if args.ignore_failures:
        args.ignore_service_failures = True
        args.ignore_pod_failures = True

    if args.action == 'boot':
        do_boot(args)
    elif args.action == 'shutdown':
        do_shutdown(args)
    else:
        # This should not happen based on the way args are parsed
        LOGGER.error('Invalid action received by bootsys command: %s',
                     args.action)
        sys.exit(1)
