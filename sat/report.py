#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Class to aid with unified formatting and printing of data.
"""
from collections import OrderedDict
import logging
import sys
from typing import Any, List

import inflect
from parsec import ParseError
from prettytable import PrettyTable

from sat.config import get_config_value
from sat.constants import EMPTY_VALUE, MISSING_VALUE
from sat.filtering import (
    parse_multiple_query_strings,
    remove_constant_values
)
from sat.util import (
    get_rst_header,
    match_query_key,
    yaml_dump,
    json_dump
)

LOGGER = logging.getLogger(__name__)
inf = inflect.engine()


def dump_structure(report_format: str, struct: Any) -> str:
    """Dump a Python structure (e.g. a dict) as a serialized string

    Args:
        report_format: "json" or "yaml", which determines
        struct: the structure to dump

    Returns:
        a string containing the structure's contents, serialized
        in the format given by `report_format`

    Raises:
        ValueError: if report_format is not a valid report format
    """
    if report_format == 'yaml':
        dump_fn = yaml_dump
    elif report_format == 'json':
        dump_fn = json_dump
    else:
        # This case theoretically shouldn't happen.
        raise ValueError('Invalid report format.')

    return dump_fn(struct)


class Report:
    """Designed to serve as a consistent output and formatter.
    """

    def __init__(self, headings, title=None,
                 sort_by=None, reverse=False,
                 no_headings=None, no_borders=None,
                 align='l', filter_strs=None,
                 filter_fns=None,
                 show_empty=None, show_missing=None,
                 force_columns=None,
                 display_headings=None,
                 print_format='pretty'):
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
            filter_fns: a list of boolean-valued predicate functions against which
                the report should be filtered. The filter functions are combined
                a boolean "and".
            show_empty: If True, then show values for columns for which every
                row has the value EMPTY_VALUE.
            show_missing: If True, then show values for columns for which every
                row has the value MISSING_VALUE.
            force_columns: a set of column names whose columns must always be present
                in the output, even if all their rows are EMPTY_VALUE or MISSING_VALUE.
                If None, then default to the normal behavior of show_empty and show_missing.
            display_headings: a list of headings which should be included in the
                output. This list should be a subset of headings.
            print_format: (str) The format to return the report. Expected to be 'pretty',
                'json', or 'yaml'.

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
        self.print_format = print_format

        self.force_columns = set(force_columns if force_columns is not None else [])

        try:
            if filter_strs or filter_fns:
                self.filter_fn = parse_multiple_query_strings(filter_strs, self.headings, filter_fns)
                self.force_columns |= self.filter_fn.get_filtered_fields()
            else:
                self.filter_fn = None
        except ParseError as err:
            LOGGER.error("The given filter has invalid syntax; returning no output. (%s)", err)
            LOGGER.warning("See the man page for this subcommand for further details on filter syntax.")
            sys.exit(1)

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
                self.sort_by = match_query_key(self.sort_by, headings)
                if not self.sort_by:
                    LOGGER.warning(warn_str, sort_by, self.headings)

        if display_headings is not None:
            self.display_headings = []

            unknown_headings = set()
            duplicate_headings = set()

            for heading in display_headings:
                matched_heading = match_query_key(heading, self.headings)

                if matched_heading is None:
                    unknown_headings.add(heading)
                elif matched_heading in self.display_headings:
                    duplicate_headings.add(heading)
                else:
                    self.display_headings.append(matched_heading)

            if unknown_headings:
                LOGGER.warning('%s %s %s not present in %s; ignoring',
                               inf.plural_noun('field', count=len(unknown_headings)),
                               inf.join(list(unknown_headings)),
                               inf.plural_verb('is', count=len(unknown_headings)),
                               f'table "{self.title}"' if self.title else 'output')
            if duplicate_headings:
                LOGGER.warning('%s %s %s duplicated in %s; using only the first instance',
                               inf.plural_noun('field', count=len(duplicate_headings)),
                               inf.join(list(duplicate_headings)),
                               inf.plural_verb('is', count=len(duplicate_headings)),
                               f'table "{self.title}"' if self.title else 'output')

            self.force_columns |= set(self.display_headings)

        else:
            self.display_headings = self.headings

    def __str__(self):
        """Return this report according to its format.

        Returns:
            The report formatted as a string.
        """
        return self.get_formatted_report(self.print_format)

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
            return self.display_headings, data_rows

        if not self.show_empty:
            data_rows = remove_constant_values(data_rows, EMPTY_VALUE, protect=self.force_columns)
        if not self.show_missing:
            data_rows = remove_constant_values(data_rows, MISSING_VALUE, protect=self.force_columns)

        # We could just take data_rows[0].keys(), but for extra assurance that
        # order is maintained, take from self.display_headings.
        new_headings = [heading for heading in self.display_headings
                        if heading in data_rows[0].keys()]
        return new_headings, data_rows

    def get_rows_to_print(self):
        """Creates a list of rows to print.

        Rows are sorted, filtered, and have the correct columns. Empty and
        missing columns are removed.

        Returns:
            a 2-tuple containing a list of headings for the output, and a
            list of OrderedDicts containing sorted rows which match the
            filters given in the filter strings of the Report. The columns
            returned are limited to those in the display_headings minus those
            whose rows contain only EMPTY or MISSING.
        """

        self.sort_data()
        try:
            selected = [OrderedDict(zip(self.display_headings, [row[column] for column in self.display_headings]))
                        for row in filter(self.filter_fn, self.data)]
        except KeyError as err:
            LOGGER.error('The query key "%s" does not match '
                         'any fields in the input; returning no output.',
                         err.args[0])
            LOGGER.info('Available field headings: %s', ', '.join(self.headings))
        except TypeError as err:
            LOGGER.error('%s', err.args[0])
        else:
            headings, culled = self.remove_empty_and_missing(selected)

            # If every row is empty, don't return any rows at all.
            if not any(culled):
                return headings, []

            return headings, culled

        # This is returned in the error case.
        return [], []

    def get_pretty_table(self):
        """Return a PrettyTable instance created from the data and format opts.

        Returns:
            A prettytable.PrettyTable reference. Returns None if an error
            occurred.
        """
        headings, rows_to_print = self.get_rows_to_print()
        if not rows_to_print:
            return ''

        pt = PrettyTable()
        pt.field_names = headings
        pt.border = not self.no_borders
        pt.header = not self.no_headings

        for heading in headings:
            pt.align[heading] = self.align

        for row in rows_to_print:
            pt.add_row([str(r) for r in row.values()])

        return pt

    def get_dumpable_structure(self):
        """Get a structure which can be natively dumped as YAML or JSON.

        Returns:
            Union[List, Dict]: if the report has a title, then return
                a dict which has the title as its only key, and a list
                of the rows as its value. Otherwise, return a list of
                dicts representing the rows.
        """
        _, rows_to_print = self.get_rows_to_print()

        if not self.no_headings and self.title:
            return {self.title: rows_to_print}
        else:
            if not rows_to_print:
                return []
            return rows_to_print

    def get_formatted_report(self, report_format):
        """Retrieve the report's data according to the given format.

        Args:
            report_format (str): The format to print the report in. Expected
            to be 'pretty', 'yaml', or 'json'.

        Returns:
            The report formatted as a string.

        Raises:
            ValueError: if report_format is not a valid format
        """
        if report_format == 'pretty':
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
        else:
            return dump_structure(report_format, self.get_dumpable_structure())


class MultiReport:
    """A container for multiple reports"""

    def __init__(self, **kwargs):
        """Constructor for MultiReports.

        Args:
            kwargs: kewyord arguments to be passed to each created Report class.
                See the Report() constructor.
        """
        self._print_format = kwargs.get('print_format')
        self.report_kwargs = kwargs
        self.reports: List[Report] = []

    def add_report(self, title: str, headings: List[str], **kwargs) -> Report:
        """Add a new Report to this MultiReport.

        Args:
            title: the title of the report
            headings: headings to use for the new report
            kwargs: keyword arguments accepted by Report() to be passed
                through to each Report. If no kwargs are passed, then
                the kwargs passed into the MultiReport constructor will
                be passed into the Report constructor. Otherwise, default
                values will be used for the Report kwargs.

        Returns:
            the constructed Report
        """
        new_report = Report(headings, title=title, **(kwargs or self.report_kwargs))
        self.reports.append(new_report)
        return new_report

    @property
    def print_format(self) -> str:
        """The print format to use for the MultiReport.

        If the print_format argument was passed to the MultiReport constructor
        or the print_format attribute is set on the MultiReport object, then
        that format is used. Otherwise, if all constituent Reports have the
        same format, that is used; otherwise, the default value is "pretty".
        """
        if self._print_format:
            return self._print_format
        report_formats_in_use = set(r.print_format for r in self.reports)
        if len(report_formats_in_use) != 1:
            LOGGER.warning('Multiple report formats are in use (%s); defaulting to "pretty"',
                           ', '.join(report_formats_in_use))
            return 'pretty'
        else:
            return report_formats_in_use.pop()

    @print_format.setter
    def print_format(self, value: str):
        self._print_format = value

    def __str__(self):
        return self.get_formatted_report(self.print_format)

    def get_formatted_report(self, report_format: str) -> str:
        """Get a string of the report in the given format.

        Args:
            report_format: the format to use. May be "pretty",
                "yaml", or "json".

        Returns:
            The formatted report
        """
        if report_format == 'pretty':
            return '\n'.join(report.get_formatted_report(report_format)
                             for report in self.reports)
        else:
            all_reports = {}
            for report in self.reports:
                dump = report.get_dumpable_structure()

                # defaultdict is not natively supported by PyYAML,
                # so we do this by hand.
                if report.title not in all_reports:
                    all_reports[report.title] = []
                all_reports[report.title].extend(dump[report.title])
            return dump_structure(report_format, all_reports)
