"""
Unit tests for the sat.showrev.rpm . This corresponds to the
'sat showrev --packages' command.

Copyright 2019 Cray Inc. All Rights Reserved.
"""


import unittest
from subprocess import CalledProcessError
from unittest import mock

import sat.showrev


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

    @mock.patch('sat.showrev.rpm.subprocess.check_output', return_value=fakerpms)
    def test_get_rpms(self, _):
        """Positive test case for get_rpms. Verifies a sorted list of returns.
        """
        result = sat.showrev.rpm.get_rpms()
        comp = [x.split() for x in fakerpms.decode('utf-8').splitlines()]
        self.assertEqual(result, sorted(comp))

    @mock.patch('sat.showrev.rpm.subprocess.check_output', return_value=fakerpms)
    def test_get_rpms_substr_filter(self, _):
        """Positive test case for filtering on substring.
        """
        result = sat.showrev.rpm.get_rpms('aa')
        self.assertEqual(result, [['aaa', '5.0.0'], ['baa', '4.0.0']])

    @mock.patch('sat.showrev.rpm.subprocess.check_output', side_effect=CalledProcessError)
    def test_get_rpms_error(self, _):
        """get_rpms should return None if there was an error.
        """
        result = sat.showrev.rpm.get_rpms()
        self.assertEqual(result, None)

    @mock.patch('sat.showrev.rpm.subprocess.check_output', return_value=fakerpms)
    def test_get_rpms_no_match(self, _):
        """get_rpms should return an empty list when there are no matches.
        """
        result = sat.showrev.rpm.get_rpms('idontexist')
        self.assertEqual(result, [])


if __name__ == '__main__':
    unittest.main()
