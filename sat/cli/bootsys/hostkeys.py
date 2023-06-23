#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
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
Support for filtering large host keys files
"""

import tempfile

from paramiko import HostKeys
from paramiko.hostkeys import HostKeyEntry


class FilteredHostKeys(HostKeys):
    """
    Host keys loader which filters all hosts except the specified ones.

    This is needed to speed up known_hosts file parsing as paramiko's implementation
    (up to and including 3.2.0) has quadratic time complexity. To get around this,
    we can hackily cut down a large known hosts file to just a few hosts in linear
    time before parsing, which should help tremendously in the case of a very large
    known_hosts file with non-hashed hostnames.
    """
    def __init__(self, filename=None, hostnames=None):
        """Construct a FilteredHostKeys object.

        Args:
            filename (str): path to the known hosts file
            hostnames ([str]): list of hostnames for which to load host keys from the
                known_hosts file
        """
        self.hostnames = hostnames
        super().__init__(filename)

    def load(self, filename):
        """Load known hosts from the specified known_hosts file.

        Args:
            filename (str): path to the known_hosts file
        """
        if not self.hostnames:
            return super().load(filename)

        with open(filename) as known_hosts, \
                tempfile.NamedTemporaryFile(mode='w+') as tmp_known_hosts:
            for line in known_hosts:
                entry = HostKeyEntry.from_line(line)
                if any(hn in entry.hostnames for hn in self.hostnames):
                    tmp_known_hosts.write(entry.to_line())
            tmp_known_hosts.flush()
            super().load(tmp_known_hosts.name)

    def save(self, filename):
        """(Don't) save the known_hosts file.

        This is a no-op since we don't want to accidentally destructively
        modify the user's known hosts file.
        """
        return
