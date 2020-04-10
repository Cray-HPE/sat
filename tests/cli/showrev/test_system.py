"""
Unit tests for the sat.sat.cli.showrev.system

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

import codecs
import os
import unittest
from unittest import mock

import sat.cli.showrev.system


samples = os.path.join(os.path.dirname(__file__), 'samples')


# Helpers for mock-decorations.

def bad_zypper_return(package):
    """Used by mock to replace sat.cli.showrev.system.subprocess.check_output.

    Used to send 'unreadable' output to within zypper_seach method, which
    commands zypper to report in xml.

    Args:
        package: Used to insert a 'real' package name into the result.
    """
    return codecs.encode(' | {} | package | 19.05.0-6 | x86_64 | Cray Module SLES'.format(package))


def zypper_good_xml(packages):
    """Reads from zypper-good-xml to pretend the zypper query succeeded.

    Args:
        package: Used to format the string inside the file to insert the
            package name.

    Returns:
        The contents of the file formatted with the package name encoded
        as a byte string. This is the expected return format of
        subprocess.check_output .
    """
    s = ''
    with open('{}/zypper-good-xml'.format(samples), 'r') as f:
        s = f.read().format(packages[-1])
    return codecs.encode(s)


class TestSystem(unittest.TestCase):

    @mock.patch('sat.cli.showrev.system.subprocess.check_output', bad_zypper_return)
    def test_get_zypper_versions_bad_return(self):
        """Ensures the get_zypper_versions method return 'ERROR' on bad output.
        """
        result = sat.cli.showrev.system.get_zypper_versions(['slurm-slurmd'])
        self.assertEqual(result['slurm-slurmd'], 'ERROR')

    @mock.patch('sat.cli.showrev.system.subprocess.check_output', zypper_good_xml)
    def test_get_zypper_versions_good_return(self):
        """Ensures the get_zypper_versions method can parse correct xml return.
        """
        result = sat.cli.showrev.system.get_zypper_versions(['slurm-slurmd'])
        self.assertEqual(result['slurm-slurmd'], '19.05.0-6')

    @mock.patch(
        'sat.cli.showrev.system.subprocess.check_output',
        side_effect=sat.cli.showrev.system.subprocess.CalledProcessError(
            cmd=['echo'], returncode=104))
    def test_get_zypper_versions_package_not_found(self, mocksubprocess):
        """The get_zypper_versions method should return None if zypper query failed.
        """
        result = sat.cli.showrev.system.get_zypper_versions(['idontexist'])
        self.assertIs(result['idontexist'], None)

    @mock.patch(
        'sat.cli.showrev.system._get_hsm_components',
        lambda: [
            {'NetType': 'sling'},
            {'NetType': 'sling'},
            {'NetType': 'asdf'}])
    def test_get_interconnects_unique(self):
        """get_interconnects should parse out the unique values.
        """
        result = sat.cli.showrev.system.get_interconnects()
        expected = ['asdf', 'sling']
        self.assertEqual(expected, result)

    @mock.patch('sat.cli.showrev.system._get_hsm_components', side_effect=sat.cli.showrev.system.APIError)
    def test_get_interconnects_error(self, mock_get_hsm_components):
        """Error test case for get_interconnects.

        get_interconnects should return 'ERROR' if it could not retrieve a
        list of components from the HSM API.
        """
        result = sat.cli.showrev.system.get_interconnects()
        self.assertEqual(['ERROR'], result)

    @mock.patch('sat.cli.showrev.system.open', lambda x, y: open('{}/os-release'.format(samples), y))
    def test_get_sles_version_correct_format(self):
        """Positive test case for get_sles_version.
        """
        short = '{}/os-release'.format(samples)
        result = sat.cli.showrev.system.get_sles_version()
        self.assertTrue(os.path.exists(short))
        self.assertEqual(result, 'SLES 15')

    @mock.patch('sat.cli.showrev.system.open', lambda x, y: open('idontexist', y))
    def test_get_sles_version_file_not_found(self):
        """get_sles_version should return a certain error string on file-not-found.

        The underlying path to os-release is hardcoded in this function, so its
        error string won't match the path in our lambda. That's expected.
        """

        result = sat.cli.showrev.system.get_sles_version()
        self.assertEqual(result, 'ERROR')
        self.assertFalse(os.path.exists('idontexist'))

    @mock.patch('sat.cli.showrev.system.open', lambda x, y: open('{}/empty'.format(samples), y))
    def test_get_sles_version_empty_osrel(self):
        """get_sles_version should return error message on empty read.
        """

        short = '{}/empty'.format(samples)
        result = sat.cli.showrev.system.get_sles_version()
        self.assertTrue(os.path.exists(short))
        self.assertEqual(result, 'ERROR')

    @mock.patch('sat.cli.showrev.system.open', lambda x, y: open('{}/os-release-missing-sles'.format(samples), y))
    def test_get_sles_version_missing_sles(self):
        """Test behavior if /etc/os-release is missing required fields.
        """
        short = '{}/os-release-missing-sles'.format(samples)
        result = sat.cli.showrev.system.get_sles_version()
        self.assertTrue(os.path.exists(short))
        self.assertEqual(result, 'ERROR')

    @mock.patch('sat.cli.showrev.system.open', lambda x, y: PermissionError)
    def test_get_sles_version_bad_osrel_permissions(self):
        """get_sles_version should report an error on bad permissions.
        """
        result = sat.cli.showrev.system.get_sles_version()
        self.assertEqual(result, 'ERROR')

    @mock.patch('sat.cli.showrev.system.open', lambda x, y: open('{}/os-release-empty-sles'.format(samples), y))
    def test_get_sles_version_name_and_version_empty(self):
        """get_sles_version should report error on empty NAME or VERSION fields.
        """
        result = sat.cli.showrev.system.get_sles_version()
        self.assertEqual(result, 'ERROR')


if __name__ == '__main__':
    unittest.main()
