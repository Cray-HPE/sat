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
Classes for managing variables that can be used in bootprep input files.
"""
from functools import cached_property
import logging
import yaml

from sat.cli.bootprep.constants import LATEST_VERSION_VALUE
from sat.recipe import HPCSoftwareRecipeCatalog, HPCSoftwareRecipeError
from sat.util import collapse_keys, deep_update_dict

LOGGER = logging.getLogger(__name__)


class VariableContextError(Exception):
    """A fatal error occurred while loading variable context."""


class VariableContext:
    """A context containing variables that can be substituted in bootprep files.

    Attributes:
        recipe_version: see constructor
        vars_file_path: see constructor
        cli_vars: see constructor
        vars (dict): the full set of variables to use as context, constructed by
            combining recipe-defined variables with any variables provided by
            the user in a file or as command-line args.
    """

    def __init__(self, recipe_version=None, vars_file_path=None, cli_vars=None):
        """Create a new VariableContext.

        Args:
            recipe_version (str, optional): The recipe version to use when
                loading variables from the HPC software recipe. If omitted,
                do not load variables from recipe. If LATEST_VERSION_VALUE
                is specified, load from latest available recipe version.
            vars_file_path (str, optional): The variable file from which variables
                should be loaded. Overrides variables in HPC software recipe.
            cli_vars (dict, optional): Dictionary of variables specified on the
                command line. Overrides variables from the `vars_file` and from
                the HPC software recipe.
        """
        self.recipe_version = recipe_version
        self.vars_file_path = vars_file_path
        self.cli_vars = cli_vars or {}
        # Variables are loaded by `load_vars`
        self.vars = {}

    def load_vars(self):
        """Load variables from the HPC software recipe, vars file, and command-line.

        Variables from the software recipe, vars file, and command line are loaded into
        the `vars` attribute.

        Raises:
            VariableContextError: if there is a failure to load variables from a file.
        """
        deep_update_dict(self.vars, self.software_recipe_vars)
        deep_update_dict(self.vars, self.file_vars)
        deep_update_dict(self.vars, self.cli_vars)

    @cached_property
    def file_vars(self):
        """Get variables from the vars file.

        Returns:
            dict: the variables loaded from the file.

        Raises:
            VariableContextError: if there is a problem reading the file,
                parsing it as YAML, or if it does not contain a dict
        """
        if not self.vars_file_path:
            return {}

        # Unlike failures to load vars from recipe, failures to load variables
        # from a file should raise an exception because the user specifically
        # requested variables be loaded from a file.
        try:
            with open(self.vars_file_path, 'r') as vars_file:
                file_vars = yaml.safe_load(vars_file)
        except OSError as err:
            raise VariableContextError(f'Failed to open variables file '
                                       f'{self.vars_file_path}: {err}') from err
        except yaml.YAMLError as err:
            raise VariableContextError(f'Failed to load YAML from variables file '
                                       f'{self.vars_file_path}: {err}') from err

        if not isinstance(file_vars, dict):
            raise VariableContextError(f'Variables file {self.vars_file_path} '
                                       f'must define a mapping at the top level.')

        return file_vars

    @cached_property
    def software_recipe_vars(self):
        """Get variables from the HPC software recipe.

        Returns:
            dict: the variables loaded from the HPC software recipe.
        """
        try:
            recipe_catalog = HPCSoftwareRecipeCatalog()
            if self.recipe_version == LATEST_VERSION_VALUE:
                recipe = recipe_catalog.get_latest_version()
            else:
                recipe = recipe_catalog.get_recipe_version(self.recipe_version)

            return recipe.all_vars
        except HPCSoftwareRecipeError as err:
            # Only issue a warning because the input file may not use the variables provided
            # by the recipe, or the variables may be provided by --vars-file or --vars.
            LOGGER.warning(
                f'Failed to load variables defined by HPC software recipe version '
                f'{self.recipe_version}: {err}'
            )
            return {}

    def enumerate_vars_and_sources(self):
        """Generate 3-tuples of variable names, values, and sources

        Yields:
            (name: str, value: str, source: str):
                name: dot-separated variable name
                value: value of variable
                source: "--vars", vars file path, or "recipe ..."
        """
        var_attr_by_source = {
            f'--vars': 'cli_vars',
            self.vars_file_path: 'file_vars',
            f'{self.recipe_version} recipe': 'software_recipe_vars',
        }
        yielded_keys = set()
        for source, attr in var_attr_by_source.items():
            vars_from_source = getattr(self, attr)
            if vars_from_source:
                variables = collapse_keys(vars_from_source)
                for fq_var_name, var_value in variables.items():
                    if fq_var_name not in yielded_keys:
                        yield fq_var_name, var_value, source
                        yielded_keys.add(fq_var_name)
