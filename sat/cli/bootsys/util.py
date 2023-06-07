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
Generic common utilities for the bootsys subcommand.
"""

import logging
import re
from collections import defaultdict

import yaml
from paramiko import SSHClient, WarningPolicy

from sat.util import pester_choices

LOGGER = logging.getLogger(__name__)


# Maps from management NCN subroles to prefixes for those hostnames
MGMT_NCN_HOSTNAME_PREFIXES = {
    'managers': 'ncn-m',
    'workers': 'ncn-w',
    'storage': 'ncn-s'
}


class FatalBootsysError(Exception):
    """A fatal error has occurred during bootsys."""
    pass


def get_mgmt_ncn_hostnames(subroles):
    """Get a set of management non-compute node (NCN) hostnames.

    The hostnames of the NCNs are parsed from the hosts file on the local host
    where this is executed.

    Args:
        subroles (list of str): subroles for which to get hostnames, possible
            values are keys of `MGMT_NCN_HOSTNAME_PREFIXES`.

    Returns:
        Set of hostnames for the management NCNs which have the given subroles.

    Raises:
        ValueError: if given any invalid subroles values
    """
    ncn_hostnames = set()

    invalid_subroles = [subrole for subrole in subroles
                        if subrole not in MGMT_NCN_HOSTNAME_PREFIXES]
    if invalid_subroles:
        raise ValueError(f'Invalid subroles given: {", ".join(invalid_subroles)}')

    # The NCN hostname should have whitespace before it and after it unless
    # it is the end of the line.
    hostname_regexes = [
        re.compile(fr'{MGMT_NCN_HOSTNAME_PREFIXES[subrole]}\d{{3}}')
        for subrole in subroles
    ]

    try:
        with open('/etc/hosts', 'r') as f:
            for line in f.readlines():
                # Strip comments
                stripped_line = line.split('#', 1)[0]
                for word in stripped_line.split():
                    for hostname_regex in hostname_regexes:
                        match = hostname_regex.fullmatch(word)
                        if match:
                            ncn_hostnames.add(word)

    except OSError as err:
        LOGGER.error('Unable to read /etc/hosts to obtain management NCN '
                     'hostnames: %s', err)

    return ncn_hostnames


def k8s_pods_to_status_dict(v1_pod_list):
    """Helper function to convert a V1PodList to a dict.

    It is used for recording the pod phase for every pod in the system.

    The dict has the following schema:
    {
        namespace (str): {
            name_in_namespace (str): pod_phase (str)
        }
    }

    Args:
        v1_pod_list: a V1PodList object from the kubernetes library

    Returns:
        a defaultdict in the above form

    """
    pods_dict = defaultdict(dict)
    for pod in v1_pod_list.items:
        pods_dict[pod.metadata.namespace][pod.metadata.name] = pod.status.phase

    return pods_dict


def get_mgmt_ncn_groups(excluded_ncns=None):
    """Get included and excluded management NCNs grouped by subrole.

    Args:
        excluded_ncns (set of str): A set of NCN hostnames to exclude, or None
            if no NCNs should be excluded.

    Returns:
        included, excluded: A tuple of dictionaries for included and excluded
            management NCNs, each of which is a mapping from NCN subrole to
            sorted lists of the included or excluded nodes with that subrole.

    Raises:
        FatalBootsysError: if unable to identify members of any subrole
    """
    excluded_ncns = set() if excluded_ncns is None else excluded_ncns
    ncns_by_subrole = {
        subrole: sorted(get_mgmt_ncn_hostnames([subrole]))
        for subrole in MGMT_NCN_HOSTNAME_PREFIXES.keys()
    }
    incl_ncns_by_subrole = {}
    excl_ncns_by_subrole = {}
    for subrole, members in ncns_by_subrole.items():
        incl_ncns_by_subrole[subrole] = [m for m in members if m not in excluded_ncns]
        excl_ncns_by_subrole[subrole] = [m for m in members if m in excluded_ncns]

    empty_subroles = [subrole for subrole, members in ncns_by_subrole.items()
                      if not members]
    if empty_subroles:
        raise FatalBootsysError(f'Failed to identify members of the following '
                                f'NCN subrole(s): {empty_subroles}')

    return incl_ncns_by_subrole, excl_ncns_by_subrole


def prompt_for_ncn_verification(incl_ncns_by_subrole, excl_ncns_by_subrole):
    """Prompt the user for verification of the included and excluded NCNs.

    Args:
        incl_ncns_by_subrole (dict): A dict mapping from NCN subrole to sorted
            lists of NCNs to include in the operation.
        excl_ncns_by_subrole (dict): A dict mapping from NCN subrole to sorted
            lists of NCNs to exclude from the operation.

    Returns:
        None

    Raises:
        FatalBootsysError: if unable to identify members of any group or user
            answers prompt by saying NCN subroles are incorrect.
    """
    print('The following Non-compute Nodes (NCNs) will be included in this operation:')
    print(yaml.dump(incl_ncns_by_subrole))

    exclusions_exist = any(members for members in excl_ncns_by_subrole.values())
    if exclusions_exist:
        print('The following Non-compute Nodes (NCNs) will be excluded from this operation:')
        print(yaml.dump(excl_ncns_by_subrole))

    prompt = f'Are the above NCN groupings {"and exclusions " if exclusions_exist else ""}correct?'
    if pester_choices(prompt, ('yes', 'no')) == 'no':
        raise FatalBootsysError('User indicated NCN groups are incorrect.')


def get_and_verify_ncn_groups(excluded_ncns=None):
    """Get NCNs by group with possible exclusions and prompt user for confirmation of correctness.

    Args:
        excluded_ncns (set of str): A set of NCN hostnames to exclude, or None
            if no NCNs should be excluded.

    Returns:
        A dictionary mapping from NCN group name to sorted lists of the included
        nodes in group.

    Raises:
        FatalBootsysError: if unable to identify members of any group or if
            unable to identify members of any group or user answers prompt by
            saying NCN groups are incorrect.
    """
    incl_ncns_by_subrole, excl_ncns_by_subrole = get_mgmt_ncn_groups(excluded_ncns)
    prompt_for_ncn_verification(incl_ncns_by_subrole, excl_ncns_by_subrole)

    # The 'kubernetes' grouping is just shorthand for 'managers' and 'workers'.
    # It is used by the platform-services stage for convenience.
    incl_ncns_by_subrole['kubernetes'] = sorted(incl_ncns_by_subrole['managers'] +
                                                incl_ncns_by_subrole['workers'])

    return incl_ncns_by_subrole


def get_ssh_client(host_keys=None):
    """Get a paramiko SSH client.

    Returns:
        A paramiko.SSHClient instance with host keys loaded and the policy for
        missing host keys set to warn rather than fail.
    """
    ssh_client = SSHClient()
    if host_keys is not None:
        ssh_client._system_host_keys = host_keys
    ssh_client.load_system_host_keys()
    ssh_client.set_missing_host_key_policy(WarningPolicy)

    return ssh_client
