#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Fields for the site data used by 'sat setrev' and 'sat showrev'.
"""

from datetime import datetime
import logging
from prettytable import PrettyTable
from textwrap import fill

LOGGER = logging.getLogger(__name__)


# Parameters for validating fields
SHORT_FIELD_MIN_LEN = 3
SHORT_FIELD_MAX_LEN = 50
LONG_FIELD_MIN_LEN = 1
LONG_FIELD_MAX_LEN = 60
# Map valid system types to a short description.
SYSTEM_TYPES = {
    'EX-1C': '"Shasta" liquid-cooled system',
    'EX-1S': '"Shasta" air-cooled system',
    'WB': 'workbench, for development purposes'
}
SYSTEM_IDENTIFICATION_PURPOSE = (
    'System identification. This will affect how SDU snapshots are identified '
    'in the HPE backend services.'
)
RDA_PURPOSE = 'Settings used by Remote Device Access (RDA).'
MAX_TABLE_WIDTH = 80


class SiteDataEntry:
    """Base class for site data entries."""
    # The data type for a site file entry.
    # Note: currently, data type is just printed as a part of the interactive prompt,
    # and all values are string type. In the future, it may be desirable to convert
    # certain fields to other types, e.g. numeric types.
    data_type = str
    # A description of possible values for the entry. Subclasses should set this
    # to a string which will be printed when printing the description of the entry.
    valid_values_description = None

    def __init__(self, name, description, purpose, default=None):
        """Create a SiteDataEntry.

        Args:
            name(str): The name of the entry.
            description(str): A short description of the entry.
            default(str): An optional default value for the entry.
        """
        self.name = name
        self.description = description
        self.purpose = purpose
        self._default = default

    @staticmethod
    def validate(value):
        """Check that this value is valid. Must be implemented by subclasses."""
        raise NotImplementedError

    @property
    def default(self):
        """Get this entry's default value."""
        return self._default

    @staticmethod
    def _format_value(value, max_value_width):
        """Format a value in the site entry description table.

        This function formats the values to be printable in the table
        printed by _print_entry_description. This is a helper to
        _print_entry_description().

        Args:
            value (str): the value to format.
            max_value_width (int): the maximum length of lines
                for value.

        Returns:
            str: The value wrapped based on max_value_width.
        """
        if value is None:
            return None

        # Add empty quotes to empty string values
        if value == '':
            value = '""'

        # Wrap lines individually using splitlines() so that newlines in 'value' are respected.
        return '\n'.join(
            fill(line, width=max_value_width)
            for line in f'{value}'.splitlines()
        )

    def _print_entry_description(self, data):
        """Print a prompt describing this site file entry.

        This function prints a table that describes this entry, including
        things like the setting's name, the setting's purpose, its valid
        values, default and current values.

        Then, this function prints out several options for how the user
        may want to proceed, e.g. "press enter to keep the current value".

        This is a helper to prompt().

        Args:
            data: A dictionary representing the current site file data.

        Returns: None
        """
        entry_attributes = {
            'Setting:': self.name,
            'Purpose:': self.purpose,
            'Description:': self.description,
            'Valid values:': self.valid_values_description,
            'Type:': self.data_type,
            'Default:': self.default,
            'Current value:': data.get(self.name)
        }
        # The width of the lefthand column is the longest field plus one space for padding
        key_column_width = max(len(fn) for fn in entry_attributes) + 1

        # Wrap values such that they do not extend beyond MAX_TABLE_WIDTH
        max_value_width = MAX_TABLE_WIDTH - key_column_width

        # Construct a table describing the entry
        entry_table = PrettyTable()
        for entry_attribute_name, entry_attribute_value in entry_attributes.items():
            entry_table.add_row(
                [entry_attribute_name, self._format_value(entry_attribute_value, max_value_width)]
            )
        entry_table.header = False
        entry_table.border = False
        entry_table.left_padding_width = 0
        entry_table.align = 'l'

        print('-' * MAX_TABLE_WIDTH)
        # Remove trailing white space from lines
        print('\n'.join(line.rstrip() for line in entry_table.get_string().splitlines()))
        print('-' * MAX_TABLE_WIDTH)

        print('Please do one of the following to set the value of the above setting:')
        if self.name in data:
            current_value = '""' if data[self.name] == '' else data[self.name]
            print(f'  - Press enter to keep the current value: {current_value}')
        elif self.default:
            print(f'  - Press enter to use the default value: {self.default}')
        print(f'  - Input a new value')
        print(f'  - Press CTRL-C to exit')

    def prompt(self, data):
        """Prompt for an entry for a given field in a loop.

        Args:
            data (dict): the current site data

        Returns:
            str: The validated value that the user supplied, the previous
            value, or default.
        """
        self._print_entry_description(data)

        # Loop until a valid input was given and return it.
        while True:
            entry_data = input(f'{self.name}: ')

            if not entry_data:
                # If user entered nothing and there is a current value, take it.
                if self.name in data:
                    return data[self.name]
                # If user entered nothing and there is no current value, take the default.
                elif self.default:
                    return self.default

            # If there was no default or previous value, validate the current input.
            # Whitespace is stripped from the input, which means you can set a value
            # to an empty string by supplying only whitespace.
            try:
                return self.validate(entry_data.strip())
            except ValueError as err:
                LOGGER.error(err)


class ShortStringEntry(SiteDataEntry):
    """A short (SHORT_FIELD_MIN_LEN - SHORT_FIELD_MAX_LEN characters) entry."""
    valid_values_description = f'Alpha-numeric string, {SHORT_FIELD_MIN_LEN} - {SHORT_FIELD_MAX_LEN} characters.'

    @staticmethod
    def validate(value):
        """Check that the value is within the length constraints.

        Args:
            value (str): the value to check

        Returns:
            str: The value to check, unmodified.

        Raises:
            ValueError: if the value is not within the length constraints.
        """
        if not SHORT_FIELD_MIN_LEN <= len(value) <= SHORT_FIELD_MAX_LEN:
            raise ValueError(
                f'Value "{value}" is not between {SHORT_FIELD_MIN_LEN} and {SHORT_FIELD_MAX_LEN} characters.'
            )
        return value


class LongStringEntry(SiteDataEntry):
    """A long (LONG_FIELD_MIN_LEN - LONG_FIELD_MAX_LEN characters) entry."""
    valid_values_description = f'Alpha-numeric string, {LONG_FIELD_MIN_LEN} - {LONG_FIELD_MAX_LEN} characters.'

    @staticmethod
    def validate(value):
        """Check that the value is within the length constraints.

        Args:
            value (str): the value to check

        Returns:
            str: The value to check, unmodified.

        Raises:
            ValueError: if the value is not within the length constraints.
        """
        if not LONG_FIELD_MIN_LEN <= len(value) <= LONG_FIELD_MAX_LEN:
            raise ValueError(
                f'Value "{value}" is not between {LONG_FIELD_MIN_LEN} and {LONG_FIELD_MAX_LEN} characters.'
            )
        return value


class DateEntry(SiteDataEntry):
    """A date entry."""
    sat_date_format = '%Y-%m-%d'
    valid_values_description = f'A date in YYYY-M-D format.'

    @staticmethod
    def validate(value):
        """Check that the value is a date in YYYY-M-D format.

        This also allows non-zero-padded values for month and day,
        e.g. 2021-1-1, but will return them in zero-padded form.

        Args:
            value (str): the value to check

        Returns:
            str: The value to check, normalized to YYYY-MM-DD format.

        Raises:
            ValueError: if the value is not in YYYY-M-D format.
        """
        try:
            date = datetime.strptime(value, DateEntry.sat_date_format)
        except ValueError:
            raise ValueError(
                f'Value "{value}" must be YYYY-M-D format.'
            )
        return datetime.strftime(date, DateEntry.sat_date_format)

    @property
    def default(self):
        return datetime.today().strftime(DateEntry.sat_date_format)


class SystemTypeEntry(SiteDataEntry):
    """A system type entry."""
    default = 'EX-1C'
    valid_values_description = '\n'.join(
        f'* {value_name}: ({value_description})'
        for value_name, value_description in SYSTEM_TYPES.items()
    )

    @staticmethod
    def validate(value):
        """Check that the value is one of the predefined system types.

        Args:
            value (str): the value to check

        Returns:
            str: The value to check, unmodified.

        Raises:
            ValueError: if the value is not one of the predefined system types.
        """
        if value not in SYSTEM_TYPES:
            raise ValueError(
                f'Value "{value}" is not a valid system type. Please choose from: {", ".join(sorted(SYSTEM_TYPES))}.'
            )
        return value


class CountryCodeEntry(SiteDataEntry):
    """A country code entry."""
    valid_values_description = 'Two-letter ISO 3166 country code.'

    @staticmethod
    def validate(value):
        """Check that the given value is 2 characters and uppercase.

        Args:
            value (str): the value to check

        Returns:
            str: The value to check, unmodified.

        Raises:
            ValueError: if the value is not 2 characters and uppercase.
        """
        # TODO: consider validating against a list of country codes
        if not all((len(value) == 2, value.isupper(), value.isalpha())):
            raise ValueError(
                f'Value "{value}" must be two uppercase letters.'
            )
        return value


SITE_FIELDS = [
    ShortStringEntry(
        name='Serial number',
        description=(
            'This is the top-level serial number which uniquely identifies '
            'the system. It can be requested from an HPE representative. '
            'Coupled with the product number, this provides a unique system '
            'identification in HPE Salesforce.'
        ),
        purpose=SYSTEM_IDENTIFICATION_PURPOSE
    ),
    ShortStringEntry(
        name='System name',
        description='The name of the system.',
        purpose=SYSTEM_IDENTIFICATION_PURPOSE
    ),
    SystemTypeEntry(
        name='System type',
        description='The type of the system.',
        purpose=SYSTEM_IDENTIFICATION_PURPOSE
    ),
    LongStringEntry(
        name='System description',
        description=(
            'A description of the system. The purpose of this field is to '
            'allow the customer to add any additional information that may be '
            'helpful to HPE for debugging. For example, "This is the system '
            'labeled XYZ on the west side of server room ABC."'
        ),
        purpose=SYSTEM_IDENTIFICATION_PURPOSE
    ),
    ShortStringEntry(
        name='Product number',
        description=(
            'This, along with serial number, is the primary identifier for '
            'the system in HPE Salesforce. An HPE Cray EX Supercomputer will '
            'have a product number similar to "R4K98A".'
        ),
        purpose=SYSTEM_IDENTIFICATION_PURPOSE
    ),
    LongStringEntry(
        name='Company name',
        description='Company name.',
        purpose=RDA_PURPOSE
    ),
    LongStringEntry(
        name='Site name',
        description='Company site.',
        purpose=RDA_PURPOSE
    ),
    CountryCodeEntry(
        name='Country code',
        description='ISO 3166 country code.',
        purpose=RDA_PURPOSE
    ),
    DateEntry(
        name='System install date',
        description='The date of installation.',
        purpose='System installation.'
    )
]
