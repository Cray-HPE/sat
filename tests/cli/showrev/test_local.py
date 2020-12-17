"""
Unit tests for the sat.sat.cli.showrev.local

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
import os
import unittest
from unittest import mock

from sat.cli.showrev.local import get_sles_version


samples = os.path.join(os.path.dirname(__file__), 'samples')


class TestGetSLESVersion(unittest.TestCase):
    def test_get_sles_version_correct_format(self):
        """Positive test case for get_sles_version.
        """
        file_ = '{}/os-release'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.local.open', mock_open):
            short = '{}/os-release'.format(samples)
            result = get_sles_version()
            self.assertTrue(os.path.exists(short))
            self.assertEqual(result, 'SLES 15')

    def test_get_sles_version_file_not_found(self):
        """get_sles_version should return a certain error string on file-not-found.
        """
        mock_open = mock.mock_open()
        mock_open.side_effect = FileNotFoundError

        with mock.patch('sat.cli.showrev.local.open', mock_open):
            result = get_sles_version()
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_empty_osrel(self):
        """get_sles_version should return error message on empty read.
        """
        file_ = '{}/empty'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.local.open', mock_open):
            short = '{}/empty'.format(samples)
            result = get_sles_version()
            self.assertTrue(os.path.exists(short))
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_missing_sles(self):
        """Test behavior if /etc/os-release is missing required fields.
        """
        file_ = '{}/os-release-missing-sles'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.local.open', mock_open):
            short = '{}/os-release-missing-sles'.format(samples)
            result = get_sles_version()
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_bad_osrel_permissions(self):
        """get_sles_version should report an error on bad permissions.
        """
        mock_open = mock.mock_open()
        mock_open.side_effect = PermissionError

        with mock.patch('sat.cli.showrev.local.open', mock_open):
            result = get_sles_version()
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_name_and_version_empty(self):
        """get_sles_version should report error on empty NAME or VERSION fields.
        """
        file_ = '{}/os-release-empty-sles'.format(samples)
        with open(file_) as f:
            data = f.read()

        mock_open = mock.mock_open(read_data=data)

        with mock.patch('sat.cli.showrev.local.open', mock_open):
            result = get_sles_version()
            self.assertEqual(result, 'ERROR')

    def test_get_sles_version_default_file(self):
        """By default get_sles_version should read from 'sat' location if it exists"""
        mock.patch('sat.cli.showrev.local.os.path.isfile', return_value=True).start()
        mock_open = mock.mock_open(read_data='')
        with mock.patch('sat.cli.showrev.local.open', mock_open):
            get_sles_version()
        mock_open.assert_called_with('/opt/cray/sat/etc/os-release', 'r')

    def test_get_sles_version_fallback_file(self):
        """By default get_sles_version should read from default location if 'sat' location doesn't exist"""
        mock.patch('sat.cli.showrev.local.os.path.isfile', return_value=False).start()
        mock_open = mock.mock_open(read_data='')
        with mock.patch('sat.cli.showrev.local.open', mock_open):
            get_sles_version()
        mock_open.assert_called_with('/etc/os-release', 'r')
