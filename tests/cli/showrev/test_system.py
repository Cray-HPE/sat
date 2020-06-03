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
import subprocess
import unittest
from argparse import Namespace
from unittest import mock

from kubernetes.client.rest import ApiException

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

    def tearDown(self):
        mock.patch.stopall()

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

    def test_get_release_version_correct_format(self):
        """Positive test case for get_release_version.
        """
        file_ = '{}/cray-release'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            short = '{}/cray-release'.format(samples)
            result = sat.cli.showrev.system.get_release_version()
            self.assertTrue(os.path.exists(short))
            self.assertEqual(result, '1.2')

    def test_get_release_version_file_not_found(self):
        """get_release_version should return a certain error string on file-not-found.

        The underlying path to os-release is hardcoded in this function, so its
        error string won't match the path in our lambda. That's expected.
        """
        mock_open = mock.mock_open()
        mock_open.side_effect = FileNotFoundError

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            result = sat.cli.showrev.system.get_release_version()
            self.assertEqual(result, 'ERROR')
            self.assertFalse(os.path.exists('idontexist'))

    def test_get_sles_version_correct_format(self):
        """Positive test case for get_sles_version.
        """
        file_ = '{}/os-release'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            short = '{}/os-release'.format(samples)
            result = sat.cli.showrev.system.get_sles_version()
            self.assertTrue(os.path.exists(short))
            self.assertEqual(result, 'SLES 15')

    def test_get_sles_version_file_not_found(self):
        """get_sles_version should return a certain error string on file-not-found.

        The underlying path to os-release is hardcoded in this function, so its
        error string won't match the path in our lambda. That's expected.
        """
        mock_open = mock.mock_open()
        mock_open.side_effect = FileNotFoundError

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            result = sat.cli.showrev.system.get_sles_version()
            self.assertEqual(result, 'ERROR')
            self.assertFalse(os.path.exists('idontexist'))

    def test_get_sles_version_empty_osrel(self):
        """get_sles_version should return error message on empty read.
        """
        file_ = '{}/empty'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            short = '{}/empty'.format(samples)
            result = sat.cli.showrev.system.get_sles_version()
            self.assertTrue(os.path.exists(short))
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_missing_sles(self):
        """Test behavior if /etc/os-release is missing required fields.
        """
        file_ = '{}/os-release-missing-sles'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            short = '{}/os-release-missing-sles'.format(samples)
            result = sat.cli.showrev.system.get_sles_version()
            self.assertTrue(os.path.exists(short))
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_bad_osrel_permissions(self):
        """get_sles_version should report an error on bad permissions.
        """
        mock_open = mock.mock_open()
        mock_open.side_effect = PermissionError

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            result = sat.cli.showrev.system.get_sles_version()
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_name_and_version_empty(self):
        """get_sles_version should report error on empty NAME or VERSION fields.
        """
        file_ = '{}/os-release-empty-sles'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.system.open', mock_open):
            result = sat.cli.showrev.system.get_sles_version()
            self.assertEqual(result, 'ERROR')

    def test_get_slurm_version_config_exception(self):
        """get_slurm_version kubernetes config failure test.
        """
        mock.patch(
            'sat.cli.showrev.system.kubernetes.config.load_kube_config',
            side_effect=ApiException).start()

        slurm_version = sat.cli.showrev.system.get_slurm_version()

        self.assertEqual('ERROR', slurm_version)

    def test_get_slurm_version_pod_exception(self):
        """get_slurm_version kubernetes list pod exception test.
        """
        mock.patch(
            'sat.cli.showrev.system.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.showrev.system.kubernetes.client.CoreV1Api.list_namespaced_pod',
            side_effect=ApiException).start()

        slurm_version = sat.cli.showrev.system.get_slurm_version()
        self.assertEqual('ERROR', slurm_version)

    def test_get_slurm_version_subprocess_exception(self):
        """get_slurm_version subprocess parsing had an error.

        If the subprocess call within get_slurm_version returned non-zero,
        then get_slurm_version should return 'ERROR'.
        """
        # These classes mock the return from 'list_namespaced_pod'.
        class Pod:
            def __init__(self, name):
                self.metadata = Namespace()
                self.metadata.name = name

        class Pods:
            def __init__(self):
                self.items = [
                    Pod('doesnt-matter')
                ]

        mock.patch(
            'sat.cli.showrev.system.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.showrev.system.kubernetes.client.CoreV1Api.list_namespaced_pod',
            return_value=Pods()).start()

        mock.patch(
            'sat.cli.showrev.system.subprocess.check_output',
            side_effect=subprocess.CalledProcessError(cmd=['whatever'], returncode=1)).start()

        slurm_version = sat.cli.showrev.system.get_slurm_version()
        self.assertEqual('ERROR', slurm_version)

    def test_get_slurm_version_kube_file_not_found(self):
        """get_slurm_version FileNotFound error when reading kube config.
        """
        mock.patch(
            'sat.cli.showrev.system.kubernetes.config.load_kube_config',
            side_effect=FileNotFoundError).start()

        slurm_version = sat.cli.showrev.system.get_slurm_version()
        self.assertEqual('ERROR', slurm_version)


if __name__ == '__main__':
    unittest.main()
