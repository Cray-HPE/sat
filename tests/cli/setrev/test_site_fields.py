"""
Unit tests for the sat.cli.setrev.site_fields module.

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
from textwrap import dedent
import unittest
from unittest import mock

from tests.test_util import ExtendedTestCase

from sat.cli.setrev import site_fields


FAKE_DESCRIPTION = (
    'Example site file entry. This string is intentionally long for '
    'testing that line wrapping works as expected. It must be long '
    'enough to show that line wrapping works.'
)


class FakeSiteDataEntry(site_fields.SiteDataEntry):
    valid_values_description = dedent("""\
        * Any value is valid
        * Some further description of what values are valid. This string is intentionally long.
    """)

    @staticmethod
    def validate(value):
        """Do not raise an exception."""
        return value


class TestFakeSiteDataEntry(ExtendedTestCase):
    def setUp(self):
        """Sets up patches."""
        self.entry_name = 'Example field'
        self.entry_purpose = 'For unit testing'
        self.entry = FakeSiteDataEntry(
            name=self.entry_name,
            description=FAKE_DESCRIPTION,
            purpose=self.entry_purpose,
        )
        self._output_lines = []
        self.mock_print = mock.patch('builtins.print', side_effect=lambda x: self._output_lines.append(x)).start()
        self.mock_input = mock.patch('builtins.input').start()

    def tearDown(self):
        """Stops all patches."""
        mock.patch.stopall()

    def get_mock_print_output(self):
        """Get a multiline text string representing everything that was printed by mock_print."""
        return '\n'.join(f'{line}' for line in self._output_lines)

    def test_prompt_with_no_current_data(self):
        """Test the prompt looks correct when there is no current data and the user's input is returned."""
        current_data = {}
        self.mock_input.return_value = 'Value of example field'
        returned_value = self.entry.prompt(current_data)

        expected_prompt = dedent(f"""\
            --------------------------------------------------------------------------------
            Setting:       {self.entry_name}
            Purpose:       {self.entry_purpose}
            Description:   Example site file entry. This string is intentionally long for
                           testing that line wrapping works as expected. It must be long
                           enough to show that line wrapping works.
            Valid values:  * Any value is valid
                           * Some further description of what values are valid. This string
                           is intentionally long.
            Type:          <class 'str'>
            Default:       None
            Current value: None
            --------------------------------------------------------------------------------
            Please do one of the following to set the value of the above setting:
              - Input a new value
              - Press CTRL-C to exit""")

        self.assertEqual(expected_prompt, self.get_mock_print_output())
        self.assertEqual(self.mock_input.return_value, returned_value)

    def test_prompt_accepting_current_data(self):
        """Test the prompt takes the current value if one exists and the user hit enter."""
        current_data = {
            self.entry_name: 'foo'
        }
        self.mock_input.return_value = ''
        returned_value = self.entry.prompt(current_data)
        expected_prompt = dedent(f"""\
            --------------------------------------------------------------------------------
            Setting:       {self.entry_name}
            Purpose:       {self.entry_purpose}
            Description:   Example site file entry. This string is intentionally long for
                           testing that line wrapping works as expected. It must be long
                           enough to show that line wrapping works.
            Valid values:  * Any value is valid
                           * Some further description of what values are valid. This string
                           is intentionally long.
            Type:          <class 'str'>
            Default:       None
            Current value: foo
            --------------------------------------------------------------------------------
            Please do one of the following to set the value of the above setting:
              - Press enter to keep the current value: foo
              - Input a new value
              - Press CTRL-C to exit""")

        self.assertEqual(expected_prompt, self.get_mock_print_output())
        self.assertEqual('foo', returned_value)

    def test_prompt_accepting_default_value(self):
        """Test the prompt takes the default if one exists and the user hit enter."""
        self.entry = FakeSiteDataEntry(
            name=self.entry_name,
            description=FAKE_DESCRIPTION,
            purpose=self.entry_purpose,
            default='foo'
        )
        current_data = {}
        self.mock_input.return_value = ''
        returned_value = self.entry.prompt(current_data)
        expected_prompt = dedent(f"""\
            --------------------------------------------------------------------------------
            Setting:       {self.entry_name}
            Purpose:       {self.entry_purpose}
            Description:   Example site file entry. This string is intentionally long for
                           testing that line wrapping works as expected. It must be long
                           enough to show that line wrapping works.
            Valid values:  * Any value is valid
                           * Some further description of what values are valid. This string
                           is intentionally long.
            Type:          <class 'str'>
            Default:       foo
            Current value: None
            --------------------------------------------------------------------------------
            Please do one of the following to set the value of the above setting:
              - Press enter to use the default value: foo
              - Input a new value
              - Press CTRL-C to exit""")

        self.assertEqual(expected_prompt, self.get_mock_print_output())
        self.assertEqual('foo', returned_value)

    def test_prompt_accepting_current_value_with_default(self):
        """Test the prompt takes the current value if both a default and current value exist."""
        self.entry = FakeSiteDataEntry(
            name=self.entry_name,
            description=FAKE_DESCRIPTION,
            purpose=self.entry_purpose,
            default='foo'
        )
        current_data = {
            self.entry_name: 'bar'
        }
        self.mock_input.return_value = ''
        returned_value = self.entry.prompt(current_data)
        expected_prompt = dedent(f"""\
            --------------------------------------------------------------------------------
            Setting:       {self.entry_name}
            Purpose:       {self.entry_purpose}
            Description:   Example site file entry. This string is intentionally long for
                           testing that line wrapping works as expected. It must be long
                           enough to show that line wrapping works.
            Valid values:  * Any value is valid
                           * Some further description of what values are valid. This string
                           is intentionally long.
            Type:          <class 'str'>
            Default:       foo
            Current value: bar
            --------------------------------------------------------------------------------
            Please do one of the following to set the value of the above setting:
              - Press enter to keep the current value: bar
              - Input a new value
              - Press CTRL-C to exit""")

        self.assertEqual(expected_prompt, self.get_mock_print_output())
        self.assertEqual('bar', returned_value)

    def test_prompt_with_current_data(self):
        """Test the prompt suggests to keep the current value if one exists, but takes user-specified input"""
        # There is no need to test the prompt format again.
        current_data = {
            self.entry_name: 'foo'
        }
        self.mock_input.return_value = 'Something the user typed in'
        returned_value = self.entry.prompt(current_data)
        self.assertEqual(returned_value, self.mock_input.return_value)

    def test_prompt_with_current_data_whitespace(self):
        """Test the prompt suggests to keep the current value if one exists, but takes user-specified input"""
        # There is no need to test the prompt format again.
        current_data = {
            self.entry_name: 'foo'
        }
        self.mock_input.return_value = ' '
        mock_validate = mock.patch.object(self.entry, 'validate').start()
        returned_value = self.entry.prompt(current_data)
        mock_validate.assert_called_once_with('')
        self.assertEqual(returned_value, mock_validate.return_value)

    def test_prompt_with_default_value(self):
        """Test the prompt suggests to take the default if one exists, but takes user-specified input"""
        # There is no need to test the prompt format again.
        current_data = {}
        self.entry = FakeSiteDataEntry(
            name=self.entry_name,
            description=FAKE_DESCRIPTION,
            purpose=self.entry_purpose,
            default='foo'
        )
        self.mock_input.return_value = 'Something the user typed in'
        returned_value = self.entry.prompt(current_data)
        self.assertEqual(returned_value, self.mock_input.return_value)

    def test_prompt_with_default_value_whitespace(self):
        """Test we get an empty string when giving only whitespace to an entry with a default."""
        # There is no need to test the prompt format again.
        current_data = {}
        self.entry = FakeSiteDataEntry(
            name=self.entry_name,
            description=FAKE_DESCRIPTION,
            purpose=self.entry_purpose,
            default='foo'
        )
        self.mock_input.return_value = ' '
        mock_validate = mock.patch.object(self.entry, 'validate').start()
        returned_value = self.entry.prompt(current_data)
        mock_validate.assert_called_once_with('')
        self.assertEqual(returned_value, mock_validate.return_value)

    def test_prompt_validation_fails_once(self):
        """Test the prompt will loop until validation succeeds."""
        current_data = {}
        mock_validate = mock.patch.object(self.entry, 'validate').start()
        # should fail to validate once, and then successfully validate.
        mock_validate.side_effect = [ValueError('invalid entry'), self.mock_input.return_value]
        with self.assertLogs(level=logging.ERROR) as logs:
            returned_value = self.entry.prompt(current_data)
        self.assertEqual(len(mock_validate.mock_calls), 2)
        self.assert_in_element('invalid entry', logs.output)
        self.assertEqual(returned_value, self.mock_input.return_value)


class TestValidation(unittest.TestCase):

    def tearDown(self):
        """Stops all patches."""
        mock.patch.stopall()

    def test_short_string_valid(self):
        """Test a ShortStringEntry allows entries of the correct length."""
        # Minimum-length and maximum-length strings
        valid_strings = [
            'A1A',
            'A9' * 25
        ]
        for valid_string in valid_strings:
            self.assertEqual(
                valid_string, site_fields.ShortStringEntry.validate(valid_string)
            )

    def test_short_string_invalid(self):
        """Test a ShortStringEntry doesn't allow entries that are too short or too long."""
        invalid_strings = [
            'A1',
            'A9' * 25 + 'A'
        ]
        for invalid_string in invalid_strings:
            with self.assertRaisesRegex(ValueError, f'Value "{invalid_string}" is not between 3 and 50 characters.'):
                site_fields.ShortStringEntry.validate(invalid_string)

    def test_long_string_valid(self):
        """Test a LongStringEntry allows strings up to the maximum length."""
        # Exactly 60 characters
        valid_strings = [
            'ABC123' * 10,
            'A'
        ]
        for valid_string in valid_strings:
            self.assertEqual(
                valid_string, site_fields.LongStringEntry.validate(valid_string)
            )

    def test_long_string_invalid(self):
        """Test a LongStringEntry doesn't allow entries that are too long or too short."""
        invalid_strings = [
            'ABC123' * 10 + 'A',
            ''
        ]
        for invalid_string in invalid_strings:
            with self.assertRaisesRegex(ValueError, f'Value "{invalid_string}" is not between 1 and 60 characters.'):
                site_fields.LongStringEntry.validate(invalid_string)

    def test_date_string_valid(self):
        """Test that DateEntry allows YYYY-MM-DD strings."""
        valid_date = '2021-04-22'
        self.assertEqual(valid_date, site_fields.DateEntry.validate(valid_date))

    def test_date_string_no_padding(self):
        """Test that DateEntry allows YYYY-M-D strings and returns them with 0-padding."""
        valid_date = '2021-4-1'
        expected_result = '2021-04-01'
        self.assertEqual(expected_result, site_fields.DateEntry.validate(valid_date))

    def test_date_string_month_out_of_range(self):
        """Test that DateEntry does not allow a string with a 13th month."""
        invalid_date_string = '2021-13-22'
        with self.assertRaisesRegex(ValueError, f'Value "{invalid_date_string}" must be YYYY-M-D format.'):
            site_fields.DateEntry.validate(invalid_date_string)

    def test_date_string_wrong_order(self):
        """Test that DateEntry does not allow a string where the month/day/year are out of order."""
        invalid_date_string = '22-04-2021'
        with self.assertRaisesRegex(ValueError, f'Value "{invalid_date_string}" must be YYYY-M-D format.'):
            site_fields.DateEntry.validate(invalid_date_string)

    def test_date_string_validation(self):
        """Test that DateEntry only allows YYYY-MM-DD strings."""
        valid_date_string = '2021-04-22'
        invalid_date_string = '2021-13-22'  # there is no 13th month
        with self.assertRaisesRegex(ValueError, f'Value "{invalid_date_string}" must be YYYY-M-D format.'):
            site_fields.DateEntry.validate(invalid_date_string)

        site_fields.DateEntry.validate(valid_date_string)

    def test_system_type_validation(self):
        """SystemTypeEntry only allows things from the predefined list of system types."""
        valid_system_type = 'EX-1C'
        invalid_system_type = 'Cray XC Series'
        with self.assertRaisesRegex(
                ValueError,
                f'Value "{invalid_system_type}" is not a valid system type. Please choose from: EX-1C, EX-1S, WB'):
            site_fields.SystemTypeEntry.validate(invalid_system_type)

        site_fields.SystemTypeEntry.validate(valid_system_type)

    def test_country_code_valid(self):
        """CountryCodeEntry allows things that look like two-letter ISO 3166 country codes."""
        valid_country_code = 'US'
        self.assertEqual(valid_country_code, site_fields.CountryCodeEntry.validate(valid_country_code))

    def test_country_code_full_name(self):
        """Test CountryCodeEntry does not allow full country names."""
        invalid_country_code = 'United States'
        with self.assertRaisesRegex(ValueError, f'Value "{invalid_country_code}" must be two uppercase letters.'):
            site_fields.CountryCodeEntry.validate(invalid_country_code)

    def test_country_code_with_digits(self):
        """Test CountryCodeEntry does not allow codes with digits."""
        country_code_with_digits = 'A9'
        with self.assertRaisesRegex(ValueError, f'Value "{country_code_with_digits}" must be two uppercase letters.'):
            site_fields.CountryCodeEntry.validate(country_code_with_digits)

    def test_country_code_lowercase(self):
        """Test CountryCodeEntry does not allow lowercase country codes."""
        lowercase_country_code = 'us'
        with self.assertRaisesRegex(ValueError, f'Value "{lowercase_country_code}" must be two uppercase letters.'):
            site_fields.CountryCodeEntry.validate(lowercase_country_code)


if __name__ == '__main__':
    unittest.main()
