"""
Generic common utilities for the bootsys subcommand.

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

from collections import defaultdict
import logging
import re

LOGGER = logging.getLogger(__name__)


# Maps from management NCN subroles to prefixes for those hostnames
MGMT_NCN_HOSTNAME_PREFIXES = {
    'managers': 'ncn-m',
    'workers': 'ncn-w',
    'storage': 'ncn-s'
}


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
