"""
Validation functions for the bootprep input file based on the schema.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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
import pkgutil

from jsonschema import SchemaError
from jsonschema.validators import validator_for
from yaml import safe_load, YAMLError

from sat.cli.bootprep.errors import BootPrepInternalError, BootPrepValidationError, ValidationErrorCollection

LOGGER = logging.getLogger(__name__)

# The path to the bootprep schema file, relative to the top level of the sat
# package. Note that the file is in a YAML format, but it defines a schema using
# the JSON Schema standard.
SCHEMA_FILE_RELATIVE_PATH = 'data/schema/bootprep_schema.yaml'


def load_and_validate_schema():
    """Load the bootprep input file schema and check its validity.

    Returns:
        A two-tuple containing the schema file contents as bytes and the schema
        validator object from the jsonschema library.

    Raises:
        BootPrepInternalError: if unable to open or read the schema file, load
            its YAML contents, or validate its schema against the appropriate
            JSONSchema metaschema.
    """
    sat_pkg_name = __name__.split('.')[0]

    try:
        schema_file_contents = pkgutil.get_data(sat_pkg_name, SCHEMA_FILE_RELATIVE_PATH)
    except OSError as err:
        raise BootPrepInternalError(f'Unable to open bootprep schema file: {err}')

    if schema_file_contents is None:
        raise BootPrepInternalError(f'Unable to find installed {sat_pkg_name} package.')

    try:
        schema = safe_load(schema_file_contents)
    except YAMLError as err:
        raise BootPrepInternalError(f'Invalid YAML in bootprep schema file: {err}')

    validator_cls = validator_for(schema)

    try:
        validator_cls.check_schema(schema)
    except SchemaError as err:
        raise BootPrepInternalError(f'bootprep schema file is invalid: {err}')

    return schema_file_contents, validator_cls(schema)


def load_bootprep_schema():
    """Helper function to load the schema and return only the validator.

    Returns: the schema validator object from the jsonschema
        library.

    Raises:
        BootPrepInternalError: if unable to open or read the schema file, load
            its YAML contents, or validate its schema against the appropriate
            JSONSchema metaschema.
    """
    _, validator_cls = load_and_validate_schema()
    return validator_cls


def validate_instance(instance, schema_validator):
    """Validate a given instance against the schema validator.

    Args:
        instance: The instance data loaded from the input file
        schema_validator: The validator object from the jsonschema library

    Raises:
        BootPrepValidationError: if the given instance does not validate against
            the given schema_validator.
    """
    errors = list(schema_validator.iter_errors(instance))
    if errors:
        raise ValidationErrorCollection(errors)


def load_and_validate_instance(instance_file_path, schema_validator):
    """Load and validate a given input file against the bootprep schema.

    Args:
        instance_file_path (str): the input file for bootprep
        schema_validator: the validator object from the jsonschema library.

    Returns:
        dict: the instance defined in the YAML input file, if valid.

    Raises:
        BootPrepValidationError: if the file cannot be opened or does not
            validate against the bootprep input file schema
    """
    try:
        with open(instance_file_path, 'r') as f:
            instance = safe_load(f)
    except OSError as err:
        raise BootPrepValidationError(f'Failed to open input file: {err}')
    except YAMLError as err:
        raise BootPrepValidationError(f'Failed to load YAML from input file '
                                      f'{instance_file_path}: {err}')

    validate_instance(instance, schema_validator)

    return instance
