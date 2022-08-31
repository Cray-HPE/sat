#
# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.recipe module.
"""

from unittest.mock import Mock, PropertyMock, patch
import unittest

from semver import VersionInfo

from sat.apiclient.vcs import VCSError
from sat.recipe import (
    HPCSoftwareRecipe,
    HPCSoftwareRecipeCatalog,
    HPCSoftwareRecipeError,
    HPC_SOFTWARE_RECIPE_REPO_NAME,
    HPC_SOFTWARE_RECIPE_REPO_ORG,
    HPC_SOFTWARE_RECIPE_REPO_PATH
)


class TestRecipeVersioning(unittest.TestCase):
    """Tests for handling of the recipe version"""

    def test_rc_version_is_older(self):
        """Test that release candidate recipe versions come first in ordering"""
        rc = HPCSoftwareRecipe('22.9.0-rc.1', 'repo_path', 'repo_branch')
        release = HPCSoftwareRecipe('22.9.0', 'repo_path', 'repo_branch')
        self.assertLess(rc, release)


class TestHPCSoftwareRecipeCatalog(unittest.TestCase):
    """Tests for the HPCSoftwareRecipeCatalog."""

    def setUp(self):
        self.mock_api_gw_host = 'api-gw-service-nmn.local'
        self.mock_get_config_value = patch('sat.recipe.get_config_value').start()
        self.mock_get_config_value.return_value = self.mock_api_gw_host
        self.expected_clone_url = f'https://{self.mock_api_gw_host}{HPC_SOFTWARE_RECIPE_REPO_PATH}'

        self.mock_vcs_repo_cls = patch('sat.recipe.VCSRepo').start()
        self.mock_vcs_repo = self.mock_vcs_repo_cls.return_value
        self.good_versions = ['22.3.0', '22.6.0', '22.6.1', '22.7.0', '22.7.1']
        self.bad_versions = ['22.09', '22.11.dev12']
        self.recipe_versions = self.good_versions + self.bad_versions
        self.short_branch_names = [
            # These branches follow the expected release branch format
            f'{HPC_SOFTWARE_RECIPE_REPO_ORG}/{HPC_SOFTWARE_RECIPE_REPO_NAME}/{recipe_version}'
            for recipe_version in self.recipe_versions
        ] + [
            # These branches do not follow the expect release branch format
            'master',
            'admin-created-branch'
        ]
        self.mock_refs = {f'refs/heads/{branch}': Mock() for branch in self.short_branch_names}
        type(self.mock_vcs_repo).remote_refs = PropertyMock(return_value=self.mock_refs)

    def tearDown(self):
        patch.stopall()

    def test_init(self):
        """Test creation of a new HPCSoftwareRecipeCatalog."""
        recipe_catalog = HPCSoftwareRecipeCatalog()
        self.assertEqual(self.expected_clone_url, recipe_catalog.clone_url)
        self.assertEqual(self.mock_vcs_repo, recipe_catalog.vcs_repo)

    def test_recipes_property(self):
        """Test the recipes property of HPCSoftwareRecipeCatalog"""
        recipe_catalog = HPCSoftwareRecipeCatalog()

        self.assertEqual(len(self.good_versions), len(recipe_catalog.recipes))
        for recipe_version in self.good_versions:
            self.assertIn(recipe_version, recipe_catalog.recipes)
            recipe = recipe_catalog.recipes[recipe_version]
            self.assertEqual(VersionInfo.parse(recipe_version), recipe.version)
            self.assertEqual(f'cray/hpc-csm-software-recipe/{recipe_version}',
                             recipe.vcs_branch)
            self.assertEqual(self.mock_vcs_repo, recipe.vcs_repo)

    def test_recipes_with_bad_versions_missing(self):
        """Test that versions with invalid versions are not included in the catalog"""
        self.assertFalse(set(self.bad_versions).intersection(set(HPCSoftwareRecipeCatalog().recipes)))

    def test_recipes_property_vcs_error(self):
        """Test the recipes property when there is an error accessing VCS."""
        type(self.mock_vcs_repo).remote_refs = PropertyMock(side_effect=VCSError)
        err_regex = 'Unable to get installed recipes on system'
        recipe_catalog = HPCSoftwareRecipeCatalog()

        with self.assertRaisesRegex(HPCSoftwareRecipeError, err_regex):
            _ = recipe_catalog.recipes

    def test_get_recipe_version(self):
        """Test the get_recipe_version method of HPCSoftwareRecipeCatalog."""
        recipe_catalog = HPCSoftwareRecipeCatalog()
        recipe = recipe_catalog.get_recipe_version(self.good_versions[0])
        self.assertEqual(VersionInfo.parse(self.good_versions[0]), recipe.version)

    def test_get_recipe_version_unknown_version(self):
        """Test the get_recipe_version method of HPCSoftwareRecipeCatalog with an unknown version."""
        recipe_catalog = HPCSoftwareRecipeCatalog()
        unknown_version = '21.09'
        err_regex = f'No recipe with version {unknown_version} is installed on the system'
        with self.assertRaisesRegex(HPCSoftwareRecipeError, err_regex):
            recipe_catalog.get_recipe_version(unknown_version)

    def test_get_latest_version(self):
        """Test the get_latest_version method of HPCSoftwareRecipeCatalog."""
        recipe_catalog = HPCSoftwareRecipeCatalog()
        recipe = recipe_catalog.get_latest_version()
        self.assertEqual(VersionInfo.parse(self.good_versions[-1]), recipe.version)

    def test_get_latest_version_no_recipes(self):
        """Test the get_latest_version method of HPCSoftwareRecipeCatalog when non are available."""
        type(self.mock_vcs_repo).remote_refs = PropertyMock(return_value={})

        recipe_catalog = HPCSoftwareRecipeCatalog()
        err_regex = f'No recipes detected on the system.'
        with self.assertRaisesRegex(HPCSoftwareRecipeError, err_regex):
            recipe_catalog.get_latest_version()


if __name__ == '__main__':
    unittest.main()
