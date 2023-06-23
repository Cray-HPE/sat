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
Unit tests for the sat.cli.bootsys.hostkeys module.
"""
import os
import tempfile
import unittest

from sat.cli.bootsys.hostkeys import FilteredHostKeys

host_keys = b"""\
host1,host1-alt ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAILDDtImwzXDR/R6rYn56D1ycKuGRPx8mCLqqAVM/60z+
host10,host10-alt ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIOeEKLY8+G+TPZirATL6JlFYFw46KLdvOkxpJPlnt30E
host100,host100-alt ssh-ed25519 AAAAC3NzaC1lZDI1NTE5AAAAIAN65RI9aIzKbBmreFlk7jB63+RAsWZ/CXDqX/h/Hyzs
"""


class TestFilteredHostKeys(unittest.TestCase):
    """Tests for the FilteredHostKeys class"""
    def setUp(self):
        with tempfile.NamedTemporaryFile(delete=False) as tmp:
            tmp.write(host_keys)
            self.known_hosts_path = tmp.name

    def tearDown(self):
        os.unlink(self.known_hosts_path)

    def test_filtered_host_keys_loading(self):
        """Test filtering a known_hosts file"""
        hk = FilteredHostKeys(filename=self.known_hosts_path, hostnames=['host1'])
        self.assertIn('host1', hk)
        for host in ['host10', 'host100']:
            self.assertNotIn(host, hk.keys())

    def test_unfiltered_host_keys_loading(self):
        """Test that filtering is opt-in"""
        hk = FilteredHostKeys(filename=self.known_hosts_path)
        for host in ['host1', 'host10', 'host100']:
            self.assertIn(host, hk)
