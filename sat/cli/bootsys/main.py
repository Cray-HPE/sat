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
import os
import shlex
import subprocess
import sys
from datetime import datetime
from subprocess import CalledProcessError

from sat.cli.bootsys.service_activity import do_service_activity_check
from sat.config import get_config_value


LOGGER = logging.getLogger(__name__)


DEFAULT_DIR = '/var/sat/podstates/'
DEFAULT_PODSTATE = DEFAULT_DIR + 'pod-state.json'


def do_boot(args):
    """Perform a shutdown operation on the system.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    LOGGER.error("Boot not implemented.")
    sys.exit(1)


def get_pods_as_json():
    """Get K8s pod information as a JSON string.

    Returns:
        K8s pod information as a JSON string.

    Raises:
        CalledProcessError: kubectl failed.
    """
    cmd = 'kubectl get pods -A -o json'
    toks = shlex.split(cmd)

    try:
        kubectl_output = subprocess.check_output(toks).decode('utf-8')
    except CalledProcessError as err:
        raise CalledProcessError(
            'kubectl was unable to gather pod information: {}'.format(err))

    return kubectl_output


def _new_file_name():
    """Helper function for _rotate_files. Returns the new filename.

    This function was created to help testing since datetime.utc was
    proving difficult to mock.
    """
    now = datetime.utcnow()
    return os.path.join(DEFAULT_DIR, 'pod-state.{}.json'.format(now.strftime('%Y-%m-%dT%H:%M:%S')))


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
        os.remove(DEFAULT_PODSTATE)
    except FileNotFoundError:
        pass

    os.symlink(new_file, DEFAULT_PODSTATE)

    # the symlink will always be at the front.
    files = [x for x in sorted(os.listdir(DEFAULT_DIR)) if x.startswith('pod-state') and x != 'pod-state.json']

    # remove number of pod states until compliant.
    max_pod_states = get_config_value('bootsys.max_pod_states')
    for i in range(len(files) - max_pod_states):
        os.remove(os.path.join(DEFAULT_DIR, files[i]))


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
    if path == DEFAULT_PODSTATE:
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

    Currently this only does the service activity check to verify that it is
    okay to begin shutting down.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    LOGGER.debug('Capturing state of K8s pods.')

    try:
        dump_pods(args.pod_state_file)
    except (CalledProcessError, FileNotFoundError, PermissionError) as err:
        msg = str(err)
        if args.ignore_pod_failures:
            LOGGER.warning(msg)
        else:
            LOGGER.error(msg)
            sys.exit(1)

    do_service_activity_check(args)
    print('It is safe to continue with the shutdown procedure. Please proceed.')


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
