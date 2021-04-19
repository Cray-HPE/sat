"""
Tests for sat.cli.showrev.products module.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
import copy
import logging
import os
import unittest
from unittest.mock import patch
from urllib3.exceptions import MaxRetryError
from yaml import safe_dump

from kubernetes.client.rest import ApiException
from kubernetes.config import ConfigException

from sat.cli.showrev.products import get_product_versions, get_release_file_versions, RELEASE_FILE_COLUMN
from sat.constants import MISSING_VALUE
from tests.test_util import ExtendedTestCase

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'samples')

MOCK_CONFIG_MAP = {
    'cos': safe_dump({
        '1.4.0': {
            'configuration': {
                'clone_url': 'https://vcs.fakesystem.dev.cray.com/vcs/cray/cos-config-management.git',
                'commit': 'bbc306f48ca5505df7e0ed0ca632ee7e40babd72',
                'import_branch': 'cray/cos/1.4.0',
                'ssh_url': 'git@vcs.fakesystem.dev.cray.com:cray/cos-config-management.git',
            },
            'images': {
                'cray-shasta-compute-sles15sp1.x86_64-1.4.23': {
                    'id': '51c9e0af-21a8-4bd1-b446-6d38a6914f2d'
                }
            },
            'recipes': {
                'cray-shasta-compute-sles15sp1.x86_64-1.4.23': {
                    'id': 'a89a1013-f1dd-4ef9-b0f8-ed2b1311c98a'
                }
            }
        }
    }),
    'uan': safe_dump({
        '2.0.0': {
            'configuration': {
                'clone_url': 'https://vcs.fakesystem.dev.cray.com/vcs/cray/uan-config-management.git',
                'commit': '28bdb828b30fb23c30afe87f7e2414a504377b4c',
                'import_branch': 'cray/uan/2.0.0',
                'ssh_url': 'git@vcs.fakesystem.dev.cray.com:cray/pbs-config-management.git',
            },
            'images': {
                'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0': {
                    'id': '51c9e0af-21a8-4bd1-b446-6d38a6914f2d'
                }
            },
            'recipes': {
                'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0': {
                    'id': 'a89a1013-f1dd-4ef9-b0f8-ed2b1311c98a'
                }
            }
        }
    }),
    'pbs': safe_dump({
        '0.1.0': {
            'configuration': {
                'clone_url': 'https://vcs.fakesystem.dev.cray.com/vcs/cray/pbs-config-management.git',
                'commit': 'b7eee8434bf1d55f0ab88c8785f843aba3d02184',
                'import_branch': 'cray/pbs/0.1.0',
                'ssh_url': 'git@vcs.fakesystem.dev.cray.com:cray/pbs-config-management.git',
            },
        }
    })
}


class TestGetProducts(ExtendedTestCase):

    def setUp(self):
        """Sets up patches."""
        self.mock_get_config = patch('sat.cli.showrev.products.load_kube_config').start()
        self.mock_corev1_api = patch('sat.cli.showrev.products.CoreV1Api').start().return_value
        self.mock_config_map = copy.deepcopy(MOCK_CONFIG_MAP)
        self.mock_corev1_api.read_namespaced_config_map.return_value.data = self.mock_config_map

    def tearDown(self):
        """Stops all patches"""
        patch.stopall()

    def test_get_product_versions(self):
        """Test a basic invocation of get_product_versions."""
        expected_headers = ['product_name', 'product_version', 'images', 'image_recipes']
        expected_fields = [
            ['cos', '1.4.0', 'cray-shasta-compute-sles15sp1.x86_64-1.4.23',
             'cray-shasta-compute-sles15sp1.x86_64-1.4.23'],
            ['uan', '2.0.0', 'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0',
             'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0'],
            ['pbs', '0.1.0', '-', '-']
        ]
        actual_headers, actual_fields = get_product_versions()
        self.mock_get_config.assert_called_once_with()
        self.mock_corev1_api.read_namespaced_config_map.assert_called_once_with(
            name='cray-product-catalog',
            namespace='services'
        )
        self.assertEqual(expected_headers, actual_headers)
        self.assertEqual(expected_fields, actual_fields)

    def test_get_product_versions_multiple_versions(self):
        """Test an invocation of get_product_versions with multiple of one product."""
        self.mock_config_map['uan'] = safe_dump({
            '2.0.0': {
                'configuration': {
                    'clone_url': 'https://vcs.fakesystem.dev.cray.com/vcs/cray/uan-config-management.git',
                    'commit': '28bdb828b30fb23c30afe87f7e2414a504377b4c',
                    'import_branch': 'cray/uan/2.0.0',
                    'ssh_url': 'git@vcs.fakesystem.dev.cray.com:cray/pbs-config-management.git',
                },
                'images': {
                    'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0': {
                        'id': '51c9e0af-21a8-4bd1-b446-6d38a6914f2d'
                    }
                },
                'recipes': {
                    'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0': {
                        'id': 'a89a1013-f1dd-4ef9-b0f8-ed2b1311c98a'
                    }
                }
            },
            '2.0.1': {
                'configuration': {
                    'clone_url': 'https://vcs.fakesystem.dev.cray.com/vcs/cray/uan-config-management.git',
                    'commit': 'a9e80009cd7bd4cf65d434f638afc4b53bd17091',
                    'import_branch': 'cray/uan/2.0.1',
                    'ssh_url': 'git@vcs.fakesystem.dev.cray.com:cray/pbs-config-management.git',
                },
                'images': {
                    'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.1': {
                        'id': 'b60de670-8a51-4ede-989d-cd02156d7da7'
                    }
                },
                'recipes': {
                    'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.1': {
                        'id': '09dc015b-2a64-44a6-b428-8ff479501dde'
                    }
                }
            }
        })
        expected_headers = ['product_name', 'product_version', 'images', 'image_recipes']
        expected_fields = [
            ['cos', '1.4.0', 'cray-shasta-compute-sles15sp1.x86_64-1.4.23',
             'cray-shasta-compute-sles15sp1.x86_64-1.4.23'],
            ['uan', '2.0.0', 'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0',
             'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0'],
            ['uan', '2.0.1', 'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.1',
             'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.1'],
            ['pbs', '0.1.0', '-', '-']
        ]
        actual_headers, actual_fields = get_product_versions()
        self.mock_get_config.assert_called_once_with()
        self.mock_corev1_api.read_namespaced_config_map.assert_called_once_with(
            name='cray-product-catalog',
            namespace='services'
        )
        self.assertEqual(expected_headers, actual_headers)
        self.assertEqual(expected_fields, actual_fields)

    def test_get_product_versions_multiple_images_recipes(self):
        """Test an invocation of get_product_versions where products have multiple images and recipes."""
        self.mock_config_map['uan'] = safe_dump({
            '2.0.0': {
                'configuration': {
                    'clone_url': 'https://vcs.fakesystem.dev.cray.com/vcs/cray/uan-config-management.git',
                    'commit': '28bdb828b30fb23c30afe87f7e2414a504377b4c',
                    'import_branch': 'cray/uan/2.0.0',
                    'ssh_url': 'git@vcs.fakesystem.dev.cray.com:cray/pbs-config-management.git',
                },
                'images': {
                    'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0': {
                        'id': '51c9e0af-21a8-4bd1-b446-6d38a6914f2d'
                    },
                    'cray-shasta-uan-cos-sles15sp1.aarch64-2.0.0': {
                        'id': '00d35ab0-ca81-4530-9daa-63a6bdec7681'
                    }
                },
                'recipes': {
                    'cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0': {
                        'id': 'a89a1013-f1dd-4ef9-b0f8-ed2b1311c98a'
                    },
                    'cray-shasta-uan-cos-sles15sp1.aarch64-2.0.0': {
                        'id': '0aee952d-6b84-45e0-937b-23119ed09149'
                    }
                }
            }
        })
        expected_headers = ['product_name', 'product_version', 'images', 'image_recipes']
        expected_fields = [
            ['cos', '1.4.0', 'cray-shasta-compute-sles15sp1.x86_64-1.4.23',
             'cray-shasta-compute-sles15sp1.x86_64-1.4.23'],
            ['uan', '2.0.0', 'cray-shasta-uan-cos-sles15sp1.aarch64-2.0.0\ncray-shasta-uan-cos-sles15sp1.x86_64-2.0.0',
             'cray-shasta-uan-cos-sles15sp1.aarch64-2.0.0\ncray-shasta-uan-cos-sles15sp1.x86_64-2.0.0'],
            ['pbs', '0.1.0', '-', '-']
        ]
        actual_headers, actual_fields = get_product_versions()
        self.mock_get_config.assert_called_once_with()
        self.mock_corev1_api.read_namespaced_config_map.assert_called_once_with(
            name='cray-product-catalog',
            namespace='services'
        )
        self.assertEqual(expected_headers, actual_headers)
        self.assertEqual(expected_fields, actual_fields)

    def test_get_product_versions_no_product_catalog(self):
        """Test that the case when the product catalog configuration map does not exist is handled."""
        # A 404 ApiException is raised when the config map is not found
        self.mock_corev1_api.read_namespaced_config_map.side_effect = ApiException(reason='Not Found')
        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertEqual(get_product_versions(), ([], []))
        self.assert_in_element('Error reading cray-product-catalog configuration map: Not Found', logs.output)

    def test_get_product_versions_connection_refused(self):
        """Test that the case when connecting to kubernetes fails is handled."""
        # A urllib3.exceptions.MaxRetryError is raised when we can't connect to the k8s API.
        self.mock_corev1_api.read_namespaced_config_map.side_effect = MaxRetryError(url='', pool=None)
        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertEqual(get_product_versions(), ([], []))
        self.assert_in_element(
            'Unable to connect to Kubernetes to read cray-product-catalog configuration map',
            logs.output
        )

    def test_get_product_versions_config_exception(self):
        """Test that the case when loading the kubernetes configuration fails is handled."""
        self.mock_corev1_api.read_namespaced_config_map.side_effect = ConfigException('Bad config')
        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertEqual(get_product_versions(), ([], []))
        self.assert_in_element('Unable to load kubernetes configuration: Bad config', logs.output)

    def test_get_product_versions_null_data(self):
        """Test that the case when the product catalog has a null value for .data is handled."""
        self.mock_corev1_api.read_namespaced_config_map.return_value.data = None
        with self.assertLogs(level=logging.ERROR) as logs:
            self.assertEqual(get_product_versions(), ([], []))
        self.assert_in_element('No product information found in cray-product-catalog configuration map', logs.output)


class TestReleaseFiles(unittest.TestCase):

    def test_get_release_file_versions_good(self):
        """Test get_release_file_versions with a good release directory."""
        release_dir = os.path.join(SAMPLES_DIR, 'good_release')
        headers, versions = get_release_file_versions(release_dir)

        expected_headers = [
            RELEASE_FILE_COLUMN,
            'PRODUCT',
            'OS',
            'ARCH',
            'VERSION',
            'DATE',
        ]
        expected_versions = [
            ['analytics',
             "Cray's Analytics Programming Environment Packages",
             'SLES15SP1',
             'x86_64',
             'base',
             '20200309155039'],
            ['cle',
             "Cray's Linux Environment",
             'SLES15SP1',
             'x86_64',
             '1.2.0',
             '20200306143455'],
            ['pe-base',
             "Cray's Programming Environment BASE Packages",
             'SLES15SP1',
             'x86_64',
             'master',
             '20200309154143'],
        ]

        self.assertEqual(expected_headers, headers)
        self.assertEqual(expected_versions, versions)

    def test_get_release_file_versions_messy(self):
        """Test get_release_file_versions with a messy release directory.

        This release directory will contain an empty file, a normal product
        version file, a product version file without all its typical keys and
        a blank line, a product version file with an extra key, a file that
        contains a bunch of garbage in it, and a nested directory that should
        be ignored.

        The get_release_file_versions function should handle all of this gracefully.
        """
        release_dir = os.path.join(SAMPLES_DIR, 'messy_release')
        headers, versions = get_release_file_versions(release_dir)

        expected_headers = [
            RELEASE_FILE_COLUMN,
            'PRODUCT',
            'OS',
            'ARCH',
            'VERSION',
            'DATE',
            'EXTRA_STUFF'
        ]
        expected_versions = [
            ['analytics',
             "Cray's Analytics Programming Environment Packages",
             'SLES15SP1',
             MISSING_VALUE,
             MISSING_VALUE,
             MISSING_VALUE,
             MISSING_VALUE],
            ['cle',
             "Cray's Linux Environment",
             'SLES15SP1',
             'x86_64',
             '1.2.0',
             '20200306143455',
             'hello=goodbye'],
            ['pe-base',
             "Cray's Programming Environment BASE Packages",
             'SLES15SP1',
             'x86_64',
             'master',
             '20200309154143',
             MISSING_VALUE],
        ]

        self.assertEqual(expected_headers, headers)
        self.assertEqual(expected_versions, versions)

    @patch('os.listdir', return_value=[])
    def test_get_release_file_versions_empty_dir(self, _):
        """Test get_release_file_versions with an empty release directory."""
        headers, versions = get_release_file_versions('empty_dir')
        self.assertEqual([], headers)
        self.assertEqual([], versions)

    @patch('os.listdir', side_effect=FileNotFoundError)
    def test_get_release_file_versions_non_existent_dir(self, _):
        """Test get_release_file_versions with a non-existent release dir"""
        headers, versions = get_release_file_versions('does_not_exist')
        self.assertEqual([], headers)
        self.assertEqual([], versions)

    @patch('os.listdir', side_effect=NotADirectoryError)
    def test_get_release_file_versions_release_non_directory(self, _):
        """Test get_release_file_versions with release dir not being a dir."""
        headers, versions = get_release_file_versions('not_a_directory')
        self.assertEqual([], headers)
        self.assertEqual([], versions)

    @patch('os.listdir', return_value=['bad_perms', 'other_unreadable'])
    @patch('builtins.open', side_effect=[PermissionError, OSError])
    @patch('os.path.isfile', return_value=True)
    def test_get_release_file_versions_unreadable_files(self, *_):
        """Test get_release_file_versions with a unreadable files."""
        headers, versions = get_release_file_versions()
        self.assertEqual([], headers)
        self.assertEqual([], versions)


if __name__ == '__main__':
    unittest.main()
