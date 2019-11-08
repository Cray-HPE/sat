"""
Class to aid with unified formatting and printing of data.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import logging

from prettytable import PrettyTable

from sat.util import yaml_dump, get_rst_header


LOGGER = logging.getLogger(__name__)


class Report:
    """Designed to serve as a consistent output and formatter.
    """
    def __init__(self, headings, title=None,
                 sort_by=None, reverse=False,
                 no_headings=False, no_borders=False, align='l'):
        """Create a new SatTable instance.

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
        """
        self.headings = headings
        self.title = title
        self.data = []

        # formatting options
        self.sort_by = sort_by
        self.reverse = reverse
        self.no_headings = no_headings
        self.no_borders = no_borders
        self.align = align

        # find the heading to sort on
        if sort_by is not None:
            warn_str = (
                'Element %s is not in %s. '
                'Defaulting to sorting on the first column.')
            try:
                self.sort_by = int(self.sort_by)
                self.sort_by = self.headings[self.sort_by]
            except IndexError:
                # sort_by is out of range.
                LOGGER.warning(warn_str, self.sort_by, self.headings)
                self.sort_by = None
            except ValueError:
                # sort_by is not an int.
                up = self.sort_by.upper()
                try:
                    idx = [h.upper() for h in headings].index(up)
                    self.sort_by = self.headings[idx]
                except ValueError:
                    LOGGER.warning(warn_str, self.sort_by, self.headings)
                    self.sort_by = None

    def __str__(self):
        """Return this report as a pretty-looking table.

        Returns:
            This report as a pretty-looking table.
        """
        return self.get_pretty_table()

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
        if isinstance(row, list):
            if len(row) != len(self.headings):
                msg = (
                    'row contains an incorrect number of entries. '
                    'Expected {} but received {}'.format(
                        len(self.headings), len(row)))
                LOGGER.error(msg)
                raise ValueError(msg)

            return dict(zip(self.headings, row))
        elif isinstance(row, dict):
            try:
                return dict(zip(self.headings, [row[x] for x in self.headings]))
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

    def get_pretty_table(self):
        """Return a pretty-looking string from the data.

        Returns:
            The contents formatted as a tabular-string.
        """
        pt = PrettyTable()
        pt.field_names = self.headings
        pt.reversesort = self.reverse
        pt.border = not self.no_borders
        pt.header = not self.no_headings

        table_str = ''
        if not self.no_headings and self.title:
            table_str += get_rst_header(self.title, min_len=80)

        if not self.data:
            return table_str

        if self.sort_by is not None:
            try:
                pt.sortby = self.sort_by
            except Exception:
                # The checks in __init__ should prevent this, but just in case.
                LOGGER.warning(
                    'Element %s is not in %s. '
                    'Defaulting to no sorting.', self.sort_by, self.headings)

        for heading in self.headings:
            pt.align[heading] = self.align

        for row in self.data:
            pt.add_row(row.values())

        return table_str + str(pt)

    def get_yaml(self):
        """Retrieve the report's yaml representation.

        Returns:
            The data of the report formatted as a string in yaml format.
        """
        return yaml_dump(self.data)
