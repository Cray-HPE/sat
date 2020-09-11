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
import logging
import sys

from paramiko.client import SSHClient

from sat.cli.bootsys.bos import BOSFailure, do_bos_operations
from sat.cli.bootsys.mgmt_boot_power import do_mgmt_boot
from sat.cli.bootsys.mgmt_hosts import do_enable_hosts_entries
from sat.cli.bootsys.mgmt_shutdown_ansible import do_shutdown_playbook
from sat.cli.bootsys.mgmt_shutdown_power import do_mgmt_shutdown_power
from sat.cli.bootsys.state_recorder import PodStateRecorder, StateError
from sat.cli.bootsys.service_activity import do_service_activity_check
from sat.util import BeginEndLogger, get_username_and_password_interactively, prompt_continue

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


def do_shutdown(args):
    """Perform a full-system shutdown operation.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    print('Capturing state of k8s pods.')
    with BeginEndLogger('kubernetes pod state capture'):
        try:
            PodStateRecorder().dump_state()
        except StateError as err:
            msg = str(err)
            if args.ignore_pod_failures:
                LOGGER.warning(msg)
            else:
                LOGGER.error(msg)
                sys.exit(1)

    if not args.dry_run:
        with BeginEndLogger('service activity check'):
            do_service_activity_check(args)

    action_msg = 'BOS shutdown of computes and UAN'
    prompt_continue(action_msg)
    try:
        with BeginEndLogger(action_msg):
            do_bos_operations('shutdown')
    except BOSFailure as err:
        LOGGER.error("Failed %s: %s", action_msg, err)
        sys.exit(1)

    action_msg = 'shutdown of management platform services'
    prompt_continue(action_msg)
    with BeginEndLogger(action_msg):
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

    with BeginEndLogger(action_msg):
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
