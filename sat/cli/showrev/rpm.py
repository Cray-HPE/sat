"""
sat showrev uses the functions in this module to display information about
rpms that are available.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
