"""
Unit tests for the sat.cli.showrev.rpm . This corresponds to the
'sat showrev --packages' command.

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


import unittest
from subprocess import CalledProcessError
from unittest import mock

import sat.cli.showrev


# mock output from rpm query
fakerpms = (
    b'yyy 1.0.0\n'
    b'zzz 2.0.0\n'
    b'hhh 3.0.0\n'
    b'baa 4.0.0\n'
    b'aaa 5.0.0\n'
    b'ccc 4.0.0\n'
)


class TestRpms(unittest.TestCase):

    @mock.patch('sat.cli.showrev.rpm.subprocess.check_output', return_value=fakerpms)
    def test_get_rpms(self, _):
        """Positive test case for get_rpms. Verifies a sorted list of returns.
        """
        result = sat.cli.showrev.rpm.get_rpms()
        comp = [x.split() for x in fakerpms.decode('utf-8').splitlines()]
        self.assertEqual(result, sorted(comp))

    @mock.patch('sat.cli.showrev.rpm.subprocess.check_output', return_value=fakerpms)
    def test_get_rpms_substr_filter(self, _):
        """Positive test case for filtering on substring.
        """
        result = sat.cli.showrev.rpm.get_rpms('aa')
        self.assertEqual(result, [['aaa', '5.0.0'], ['baa', '4.0.0']])

    @mock.patch('sat.cli.showrev.rpm.subprocess.check_output', side_effect=CalledProcessError)
    def test_get_rpms_error(self, _):
        """get_rpms should return None if there was an error.
        """
        result = sat.cli.showrev.rpm.get_rpms()
        self.assertEqual(result, None)

    @mock.patch('sat.cli.showrev.rpm.subprocess.check_output', return_value=fakerpms)
    def test_get_rpms_no_match(self, _):
        """get_rpms should return an empty list when there are no matches.
        """
        result = sat.cli.showrev.rpm.get_rpms('idontexist')
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
