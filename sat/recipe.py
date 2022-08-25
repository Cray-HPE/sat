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
Defines a class for accessing the HPC software recipe manifest.

The manifest defines the versions of the products that are included in a given
version of the HPC software recipe.
"""
from contextlib import contextmanager
from functools import total_ordering
import logging
import os
import re
from tempfile import TemporaryDirectory
from urllib.parse import ParseResult, urlunparse

from semver import VersionInfo
import yaml

from sat.apiclient.vcs import VCSError, VCSRepo
from sat.cached_property import cached_property
from sat.config import get_config_value

HPC_SOFTWARE_RECIPE_REPO_ORG = 'cray'
HPC_SOFTWARE_RECIPE_REPO_NAME = 'hpc-shasta-software-recipe'
HPC_SOFTWARE_RECIPE_REPO_PATH = f'/vcs/{HPC_SOFTWARE_RECIPE_REPO_ORG}/{HPC_SOFTWARE_RECIPE_REPO_NAME}.git'
# Be generous with what is allowed after cray/hpc-software-recipe/
HPC_SOFTWARE_RECIPE_RELEASE_REGEX = rf'refs/heads/(cray/{HPC_SOFTWARE_RECIPE_REPO_NAME}/(.+))'
HPC_SOFTWARE_RECIPE_VARS_FILE = 'product_vars.yaml'

LOGGER = logging.getLogger(__name__)


class HPCSoftwareRecipeError(Exception):
    """An error occurred querying the software recipes on the system."""


@total_ordering
class HPCSoftwareRecipe:

    def __init__(self, version, vcs_repo, vcs_branch):
        """Create a new HPCSoftwareRecipe object.

        Args:
            version (str): the recipe version string
            vcs_repo (VCSRepo): the VCS repository containing software recipe information
            vcs_branch: the full branch name of the `vcs_repo` that defines this recipe version

        Raises:
            ValueError: if `version` is not a valid Semantic Version
        """
        # Allows for comparison of two software recipes. Original string can be
        # retrieved by calling `str` on it.
        self.version = VersionInfo.parse(version)
        self.vcs_repo = vcs_repo
        self.vcs_branch = vcs_branch

    def __eq__(self, other):
        return self.version == other.version

    def __lt__(self, other):
        return self.version < other.version

    @cached_property
    def all_vars(self):
        """dict: the variables defined by the products"""
        with self.clone_content() as clone_dir:
            vars_file_path = os.path.join(clone_dir, HPC_SOFTWARE_RECIPE_VARS_FILE)
            try:
                with open(vars_file_path) as f:
                    return yaml.safe_load(f)
            except OSError as err:
                raise HPCSoftwareRecipeError(
                    f'Failed to open product variables file {HPC_SOFTWARE_RECIPE_VARS_FILE} '
                    f'in branch {self.vcs_branch} of VCS repo {self.vcs_repo.repo_name}.'
                ) from err
            except yaml.YAMLError as err:
                raise HPCSoftwareRecipeError(
                    f'Failed to parse YAML from product variables file {HPC_SOFTWARE_RECIPE_VARS_FILE} '
                    f'in branch {self.vcs_branch} of VCS repo {self.vcs_repo.repo_name}.'
                ) from err

    @contextmanager
    def clone_content(self):
        """Context manager to clone this branch of the software recipe repo to a temporary directory"""
        with TemporaryDirectory() as temp_dir:
            self.vcs_repo.clone(branch=self.vcs_branch, directory=temp_dir,
                                single_branch=True, depth=1)
            yield temp_dir


class HPCSoftwareRecipeCatalog:
    """A catalog of installed HPC software recipe versions.

    Attributes:
        clone_url (str): the clone url to the VCS repository containing the
            HPC software recipes.
        vcs_repo (VCSRepo): the VCS repository containing the HPC software
            recipes
    """

    def __init__(self):
        """Create a new HPCSoftwareRecipeCatalog."""
        self.clone_url = urlunparse(
            ParseResult(scheme='https', netloc=get_config_value('api_gateway.host'),
                        path=HPC_SOFTWARE_RECIPE_REPO_PATH,
                        params=None, query=None, fragment=None)
        )
        self.vcs_repo = VCSRepo(self.clone_url)

    @cached_property
    def recipes(self):
        """dict: a mapping from recipe versions to HPCSoftwareRecipe objects"""
        recipes = {}
        try:
            repo_refs = self.vcs_repo.remote_refs
        except VCSError as err:
            raise HPCSoftwareRecipeError(f'Unable to get installed recipes on system: {err}') from VCSError

        for ref_name in repo_refs:
            match = re.match(HPC_SOFTWARE_RECIPE_RELEASE_REGEX, ref_name)
            if not match:
                continue

            branch_name = match.group(1)
            recipe_version = match.group(2)
            try:
                recipes[recipe_version] = HPCSoftwareRecipe(recipe_version, self.vcs_repo, branch_name)
            except ValueError:
                LOGGER.warning('Recipe version "%s" does not conform to semantic versioning syntax; ignoring.',
                               recipe_version)

        return recipes

    def get_recipe_version(self, version):
        """Get a particular version of the HPC software recipe available on the system.

        Args:
            version (str): the requested software recipe version

        Returns:
            HPCSoftwareRecipe: the requested HPC software recipe

        Raises:
            HPCSoftwareRecipeError: if no such recipe version is found
        """
        try:
            return self.recipes[version]
        except KeyError:
            raise HPCSoftwareRecipeError(f'No recipe with version {version} is installed on the system.')

    def get_latest_version(self):
        """Get the latest version of the HPC software recipe available on the system.

        Returns:
            HPCSoftwareRecipe: the latest HPC software recipe on the system.

        Raises:
            HPCSoftwareRecipeError: if no recipe versions are found
        """
        if not self.recipes:
            raise HPCSoftwareRecipeError('No recipes detected on the system.')

        return max(self.recipes.values())
