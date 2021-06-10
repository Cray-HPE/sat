"""
Class to aid with unified formatting and printing of data.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
from collections import OrderedDict

from prettytable import PrettyTable

from sat.config import get_config_value
from sat.constants import EMPTY_VALUE, MISSING_VALUE
from sat.filtering import filter_list, is_subsequence, ParseError, remove_constant_values
from sat.util import yaml_dump, get_rst_header


LOGGER = logging.getLogger(__name__)


class Report:
    """Designed to serve as a consistent output and formatter.
    """
    def __init__(self, headings, title=None,
                 sort_by=None, reverse=False,
                 no_headings=None, no_borders=None,
                 align='l', filter_strs=None,
                 show_empty=None, show_missing=None):
        """Create a new Report instance.

        Args:
            headings: Headings for the table's columns.
            title: Title for the table
            sort_by: Sort the output by the desired column when printing
                in tabular format. Can be the name of a heading, or a 0-based
                index.
            reverse: If True, then reverse the sorting order.
            no_headings: If True, then omit the title block and column
                headings from the display.
            no_borders: If True, then omit the borders around the table's cells.
            align: Set the alignment within cells. Defaults to left-alignment.
            filter_strs: a list of strings against which the rows in the
                report should be filtered. The queries are combined with a
                boolean "and".
            show_empty: If True, then show values for columns for which every
                row has the value EMPTY_VALUE.
            show_missing: If True, then show values for columns for which every
                row has the value MISSING_VALUE.
        """
        self.headings = headings
        self.title = title
        self.data = []

        config_opts_by_arg_name = {
            'no_headings': 'format.no_headings',
            'no_borders': 'format.no_borders',
            'show_empty': 'format.show_empty',
            'show_missing': 'format.show_missing'
        }

        for arg_name, config_opt in config_opts_by_arg_name.items():
            arg_value = locals()[arg_name]
            if arg_value is not None:
                setattr(self, arg_name, arg_value)
            else:
                setattr(self, arg_name, get_config_value(config_opt))

        # formatting options
        self.sort_by = sort_by
        self.reverse = reverse
        self.align = align
        self.filter_strs = filter_strs or []

        # find the heading to sort on
        if sort_by is not None:
            warn_str = "Element '%s' is not in %s. Output will be unsorted."
            try:
                self.sort_by = int(self.sort_by)
                self.sort_by = self.headings[self.sort_by]
            except IndexError:
                # sort_by is out of range.
                LOGGER.warning(warn_str, sort_by, self.headings)
                self.sort_by = None
            except ValueError:
                # sort_by is not an int.
                low = self.sort_by.lower()
                self.sort_by = None
                # use first exact match if there is one
                for key in headings:
                    if key.lower() == low:
                        self.sort_by = key
                        break
                if not self.sort_by:
                    matching_keys = [key for key in headings if is_subsequence(low, key.lower())]
                    if len(matching_keys) > 0:
                        self.sort_by = matching_keys[0]
                        if len(matching_keys) > 1:
                            LOGGER.warning(f"Element '{sort_by}' is ambiguous. "
                                           f"Using first match: '{self.sort_by}' "
                                           f"from {tuple(matching_keys)}.")

                if not self.sort_by:
                    LOGGER.warning(warn_str, sort_by, self.headings)

    def __str__(self):
        """Return this report as a pretty-looking table.

        Returns:
            This report as a pretty-looking table.
        """
        heading = ''
        if not self.no_headings and self.title:
            heading += get_rst_header(self.title, min_len=80)

        if not self.data:
            return heading

        pt = self.get_pretty_table()
        if pt is not None:
            return heading + str(pt)
        else:
            return ''

    def convert_row(self, row):
        """Returns a row as it should appear as an entry in the report.

        Also used by Report to validate new entries. Raises if the row
        is not valid for this report.

        Args:
            row: The data to convert. Can be a list or dict. If row is a dict,
                then every key in self.headings needs to be present. If it
                is a list, then it needs to have the same number of entries
                as self.headings.

        Returns:
            A valid entry that could be appended to this report's data.

        Raises:
            ValueError: If row is a list, then it did not have the same
                number of entries as self.headings. If row was a dict, then
                there were headings in this report that were not present in row.
            TypeError: row was not a list or dict.
        """
        if isinstance(row, list) or isinstance(row, tuple):
            if len(row) != len(self.headings):
                msg = (
                    'row contains an incorrect number of entries. '
                    'Expected {} but received {}'.format(
                        len(self.headings), len(row)))
                LOGGER.error(msg)
                raise ValueError(msg)

            return OrderedDict(zip(self.headings, row))
        elif isinstance(row, dict):
            try:
                return OrderedDict(zip(self.headings, [row[x] for x in self.headings]))
            except KeyError:
                raise ValueError(
                    'The headings {} need to be present.'.format(self.headings))
        else:
            raise TypeError('row must be list or dict.')

    def add_rows(self, rows):
        """Add a row to the table.

        An item in rows can be a list or a dict, but they all need to match
        the headings. No rows will be added if there is a mismatch.

        Args:
            rows: Rows to add. Can be a list that contains lists or dicts.

        Raises:
            See convert_row.
        """
        new_rows = [self.convert_row(row) for row in rows]
        self.data.extend(new_rows)

    def add_row(self, row):
        """Add a row to the table.

        Args:
            row: Row to add to the report. Must be acceptable by convert_row.

        Raises:
            See convert_row.
        """
        new_row = self.convert_row(row)
        self.data.append(new_row)

    def sort_data(self):
        """Sorts the data contained in the report.

        This sorts `self.data` in place using the field specified in
        `self.sort_by` as the key and reversing if specified by `self.reverse`.
        If `self.sort_by` is None, no sorting is done.
        """
        if self.sort_by is not None:
            try:
                self.data.sort(key=lambda d: d[self.sort_by], reverse=self.reverse)
            except TypeError:
                LOGGER.info("Converting all values of '%s' field to str "
                            "to allow sorting.", self.sort_by)
                self.data.sort(key=lambda d: str(d[self.sort_by]), reverse=self.reverse)

    def remove_empty_and_missing(self, data_rows):
        """Removes columns which have only EMPTY_VALUE or MISSING_VALUE.

        Args:
            data_rows: The list of dicts representing the rows of data in the
                report.

        Returns:
            A tuple containing the following two values:
                new_headings (list): list of headings that were kept
                data_rows (list): list of dicts with keys removed for which the
                    values are either all EMPTY_VALUE or all MISSING_VALUE.
        """
        if not data_rows:
            return self.headings, data_rows

        if not self.show_empty:
            data_rows = remove_constant_values(data_rows, EMPTY_VALUE)
        if not self.show_missing:
            data_rows = remove_constant_values(data_rows, MISSING_VALUE)

        # We could just take data_rows[0].keys(), but for extra assurance that
        # order is maintained, take from self.headings.
        new_headings = [heading for heading in self.headings
                        if heading in data_rows[0].keys()]
        return new_headings, data_rows

    def get_pretty_table(self):
        """Return a PrettyTable instance created from the data and format opts.

        Returns:
            A prettytable.PrettyTable reference. Returns None if an error
            occurred.
        """
        self.sort_data()

        try:
            rows_to_print = filter_list(self.data, self.filter_strs)
        except (KeyError, ParseError, TypeError, ValueError) as err:
            LOGGER.warning("An error occurred while filtering; "
                           "returning no output. (%s)", err)
            return None

        headings, rows_to_print = self.remove_empty_and_missing(rows_to_print)

        pt = PrettyTable()
        pt.field_names = headings
        pt.border = not self.no_borders
        pt.header = not self.no_headings

        for heading in headings:
            pt.align[heading] = self.align

        for row in rows_to_print:
            pt.add_row([str(r) for r in row.values()])

        return pt

    def get_yaml(self):
        """Retrieve the report's yaml representation.

        Returns:
            The data of the report formatted as a string in yaml format.
        """
        self.sort_data()

        try:
            rows_to_print = filter_list(self.data, self.filter_strs)

        except (KeyError, ParseError, TypeError, ValueError) as err:
            LOGGER.warning("An error occurred while filtering; "
                           "returning no output. (%s)", err)
            return ''

        _, rows_to_print = self.remove_empty_and_missing(rows_to_print)

        if not self.no_headings and self.title:
            return yaml_dump({self.title: rows_to_print})
        else:
            return yaml_dump(rows_to_print)
