"""
Custom exception classes for handling bootprep schema validation errors.

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
from collections import defaultdict
from textwrap import indent

from sat.cached_property import cached_property

NESTED_ERROR_INDENT = ' ' * 4


class BootPrepInternalError(Exception):
    """An internal error occurred in bootprep (e.g. loading the schema)."""
    pass


class BootPrepValidationError(Exception):
    """An error occurred while opening, parsing, or validating input file against schema."""


class ValidationErrorCollection(BootPrepValidationError):
    """A group of errors occurred validating the schema."""

    def __init__(self, errors):
        """Create a ValidationErrorCollection.

        Args:
            errors (Iterable of jsonschema.ValidationError): An iterable of the
                errors that occurred.
        """
        self.errors = [EnhancedValidationError(error) for error in errors]

    def __str__(self):
        ret = 'Input file is invalid with the following validation errors:\n'
        ret += indent('\n'.join([str(err) for err in self.errors]), NESTED_ERROR_INDENT)
        return ret


class EnhancedValidationError(Exception):
    """An error occurred while validating input file against schema.

    This class adds functionality to the jsonschema.ValidationError by
    composition. It implements a heuristic to determine the most relevant
    contextual errors when an instance fails to validate against a schema with
    anyOf or oneOf keywords.
    """

    def __init__(self, base_error):
        """Create a new EnhancedValidationError.

        Args:
            base_error (jsonschema.ValidationError): the base validation error
                from jsonschema to wrap.
        """
        self.base_error = base_error

    @cached_property
    def best_context(self):
        """list of EnhancedValidationError: list of most relevant contextual errors"""
        # If this is not an error validating against 'oneOf' or 'anyOf' keywords,
        # there are no additional relevant contextual errors.
        if self.base_error.schema_path[-1] not in ('oneOf', 'anyOf'):
            return []

        errors_by_subschema_idx = defaultdict(list)

        for context_err in self.base_error.context:
            # This is relative to the parent oneOf or anyOf schema, so it
            # tells us which alternative we are looking at.
            subschema_idx = context_err.relative_schema_path[0]
            errors_by_subschema_idx[subschema_idx].append(context_err)

        # Get the smallest group of errors. These will be the errors against
        # the subschema that was the closest match.
        minimal_subschema_errs = min(errors_by_subschema_idx.values(), key=len)

        # Wrap in EnhancedValidationError for more info on nested anyOf/oneOf errors
        return [EnhancedValidationError(err) for err in minimal_subschema_errs]

    def __str__(self):
        """str: A description of the error with location and context"""
        path_description = ''.join(f'[{repr(p)}]' for p in self.base_error.absolute_path)
        if self.base_error.schema_path[-1] in ('oneOf', 'anyOf'):
            # Shorten this error message to not include full instance
            err_msg = "Not valid under any of the given schemas"
        else:
            err_msg = self.base_error.message

        description = f'{path_description}: {err_msg}'
        if self.best_context:
            description += ':\n' + indent('\n'.join(str(ctx) for ctx in self.best_context),
                                          NESTED_ERROR_INDENT)
        return description


class UserAbortException(Exception):
    """The user chose to abort execution."""
    pass


class InputItemCreateError(Exception):
    """A fatal error occurred during the creation of an item from the input file."""
    pass


class InputItemValidateError(Exception):
    """An error occurred while validating an item specified in the input file."""
    pass


class ConfigurationCreateError(InputItemCreateError):
    """A fatal error occurred during the creation of CFS configurations."""
    pass


class ImageCreateError(InputItemCreateError):
    """A fatal error occurred during the creation of IMS images."""
    pass


class PublicKeyError(ImageCreateError):
    """An error occurred when getting the IMS public key."""
    pass


class ImageCreateCycleError(ImageCreateError):
    """A cycle exists in image dependencies."""
    def __init__(self, cycle_members):
        """Create a new ImageCreateCycleError.

        Args:
            cycle_members (list of str): the names of the members of the cycle
        """
        self.cycle_members = cycle_members

    def __str__(self):
        """str: a description of the cycle that exists"""
        return (f'The following circular dependency exists: '
                f'{" -> ".join(self.cycle_members + self.cycle_members[:1])}')


class SessionTemplateCreateError(InputItemCreateError):
    """A fatal error occurred during the creation of BOS session templates."""
    pass
