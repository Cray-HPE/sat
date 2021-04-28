"""
Unit tests for the sat.sat.cli.showrev.system

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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

import logging
import os
import subprocess
import unittest
from argparse import Namespace
from unittest import mock
from urllib3.exceptions import MaxRetryError

from kubernetes.client.rest import ApiException
from tests.test_util import ExtendedTestCase

import sat.cli.showrev.system


samples = os.path.join(os.path.dirname(__file__), 'samples')


class TestSystem(ExtendedTestCase):

    def tearDown(self):
        mock.patch.stopall()

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

    def test_get_slurm_version_config_exception(self):
        """get_slurm_version kubernetes config failure test.
        """
        mock.patch(
            'sat.cli.showrev.system.kubernetes.config.load_kube_config',
            side_effect=ApiException).start()

        self.assertIsNone(sat.cli.showrev.system.get_slurm_version())

    def test_get_slurm_version_pod_exception(self):
        """get_slurm_version kubernetes list pod exception test.
        """
        mock.patch(
            'sat.cli.showrev.system.kubernetes.config.load_kube_config',
            return_value=None).start()

        mock.patch(
            'sat.cli.showrev.system.kubernetes.client.CoreV1Api.list_namespaced_pod',
            side_effect=ApiException).start()

        self.assertIsNone(sat.cli.showrev.system.get_slurm_version())

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

        self.assertIsNone(sat.cli.showrev.system.get_slurm_version())

    def test_get_slurm_version_kube_file_not_found(self):
        """get_slurm_version FileNotFound error when reading kube config.
        """
        mock.patch(
            'sat.cli.showrev.system.kubernetes.config.load_kube_config',
            side_effect=FileNotFoundError).start()

        self.assertIsNone(sat.cli.showrev.system.get_slurm_version())

    def test_get_slurm_version_kubernetes_max_retry_error(self):
        """get_slurm_version MaxRetryError when connecting to k8s.
        """
        mock.patch('sat.cli.showrev.system.kubernetes.config.load_kube_config').start()
        mock.patch(
            'sat.cli.showrev.system.kubernetes.client.CoreV1Api'
        ).start().return_value.list_namespaced_pod.side_effect = MaxRetryError(url='', pool=None)

        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertIsNone(sat.cli.showrev.system.get_slurm_version())
        self.assert_in_element('Error connecting to Kubernetes to retrieve list of pods', logs.output)

    def test_get_site_data_from_s3(self):
        """Test get_site_data downloads from S3."""
        sitefile = '/opt/cray/etc/site_info.yml'
        mock_s3 = mock.patch('sat.cli.showrev.system.get_s3_resource').start().return_value
        mock.patch('sat.cli.showrev.system.get_config_value', return_value='sat').start()
        mock_open = mock.patch('builtins.open').start()
        mock_yaml_load = mock.patch('sat.cli.showrev.system.yaml.safe_load').start()
        sat.cli.showrev.system.get_site_data(sitefile)
        mock_s3.Object.assert_called_once_with('sat', sitefile)
        mock_s3.Object.return_value.download_file.assert_called_once_with(sitefile)
        mock_open.assert_called_once_with(sitefile, 'r')
        mock_open.return_value.__enter__.return_value.read.assert_called_once_with()
        mock_yaml_load.assert_called_once_with(
            mock_open.return_value.__enter__.return_value.read.return_value
        )

    def test_get_system_version_null_values(self):
        """Test get_system_version does not return a row with a null Slurm version."""
        mock.patch('sat.cli.showrev.system.get_slurm_version', return_value=None).start()
        mock.patch('sat.cli.showrev.system.get_site_data').start()
        mock.patch('sat.cli.showrev.system.get_interconnects').start()
        sitefile = '/opt/cray/etc/site_info.yml'
        rows = sat.cli.showrev.system.get_system_version(sitefile)
        self.assertFalse(any(row[0] == 'Slurm version' for row in rows))


if __name__ == '__main__':
    unittest.main()
