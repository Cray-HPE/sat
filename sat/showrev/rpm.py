"""
sat showrev uses the functions in this module to display information about
rpms that are available.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import shlex
import subprocess


def get_rpms(substr=''):
    """Collect version information about installed rpms.

    Returns a list of all rpms and their versions that are installed on
    the system.

    Args:
        substr: Only return packages that contain the substr.
    Returns:
        List of lists where each entry contains the name of an rpm and its
        associated version.

        Returns None if an error occurred.
    """

    fmt = '"%{NAME} %{VERSION}\n"'
    cmd = 'rpm -qa --queryformat {}'.format(fmt)
    toks = shlex.split(cmd)

    try:
        packages = subprocess.check_output(toks).decode('utf-8').splitlines()
    except Exception as e:
        return None

    rpms = []
    for line in packages:
        rpms.append(line.split())

    if substr:
        rpms[:] = [x for x in rpms if substr in x[0]]

    rpms.sort()
    return rpms
