"""
Tests for sat.cli.showrev.products module.

Copyright 2020 Cray Inc. All Rights Reserved.
"""
import os
import unittest
from unittest.mock import patch

from sat.cli.showrev.products import get_product_versions, RELEASE_FILE_COLUMN
from sat.constants import MISSING_VALUE

SAMPLES_DIR = os.path.join(os.path.dirname(__file__), 'samples')


class TestProducts(unittest.TestCase):

    def test_get_product_versions_good(self):
        """Test get_product_versions with a good release directory."""
        release_dir = os.path.join(SAMPLES_DIR, 'good_release')
        headers, versions = get_product_versions(release_dir)

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

    def test_get_product_versions_messy(self):
        """Test get_product_versions with a messy release directory.

        This release directory will contain an empty file, a normal product
        version file, a product version file without all its typical keys and
        a blank line, a product version file with an extra key, a file that
        contains a bunch of garbage in it, and a nested directory that should
        be ignored.

        The get_product_versions function should handle all of this gracefully.
        """
        release_dir = os.path.join(SAMPLES_DIR, 'messy_release')
        headers, versions = get_product_versions(release_dir)

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
    def test_get_product_versions_empty_dir(self, _):
        """Test get_product_versions with an empty release directory."""
        headers, versions = get_product_versions('empty_dir')
        self.assertEqual([], headers)
        self.assertEqual([], versions)

    @patch('os.listdir', side_effect=FileNotFoundError)
    def test_get_product_versions_non_existent_dir(self, _):
        """Test get_product_versions with a non-existent release dir"""
        headers, versions = get_product_versions('does_not_exist')
        self.assertEqual([], headers)
        self.assertEqual([], versions)

    @patch('os.listdir', side_effect=NotADirectoryError)
    def test_get_product_versions_release_non_directory(self, _):
        """Test get_product_versions with release dir not being a dir."""
        headers, versions = get_product_versions('not_a_directory')
        self.assertEqual([], headers)
        self.assertEqual([], versions)

    @patch('os.listdir', return_value=['bad_perms', 'other_unreadable'])
    @patch('builtins.open', side_effect=[PermissionError, OSError])
    @patch('os.path.isfile', return_value=True)
    def test_get_product_versions_unreadable_files(self, *_):
        """Test get_product_versions with a unreadable files."""
        headers, versions = get_product_versions()
        self.assertEqual([], headers)
        self.assertEqual([], versions)


if __name__ == '__main__':
    unittest.main()
