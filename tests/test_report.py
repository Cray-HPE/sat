"""
Unit tests for sat/util.py .

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest
from collections import defaultdict

import yaml

from sat.report import Report


def get_report_printed_list(report):
    """Return a reports data as it would be printed.

    Strips the 'pretty' out of the pretty table and splits all the strings
    and returns each cell as a list.

    Cannot use pt._rows because they are only sorted when printed.
    """
    pt = report.get_pretty_table()
    pt.header = False
    pt.border = False
    return [x.split() for x in str(pt).splitlines()]


class TestReport(unittest.TestCase):
    """Tests the Report class internals.
    """
    def setUp(self):
        self.headings = ['name', 'place', 'color']

        # Entries are ordered such that sorting on each column yields a
        # a different order. Specifically, by each column:
        #   'name':  e1 < e2 < e3
        #   'place': e3 < e1 < e2
        #   'color': e2 < e3 < e1
        self.e1 = ['alice', 'mars', 'red']
        self.e2 = ['bob', 'venus', 'blue']
        self.e3 = ['charlie', 'earth', 'purple']

        self.entries = [self.e1, self.e2, self.e3]

    def test_heading_assignment(self):
        """Verify that a list of headings is stored correctly by Report.
        """
        report = Report(self.headings)
        self.assertEqual(self.headings, report.headings)

    def test_adding_single_list(self):
        """Verify that a single list can be added to a Report.
        """
        report = Report(self.headings)

        report.add_row(self.e1)

        self.assertEqual(self.headings, report.headings)
        self.assertEqual(1, len(report.data))
        self.assertEqual(self.e1, list(report.data[0].values()))

    def test_adding_single_dict(self):
        """Verify that a single dict can be added to a Report.
        """
        report = Report(self.headings)

        entry = dict(zip(self.headings, self.e1))
        report.add_row(entry)

        self.assertEqual(1, len(report.data))
        self.assertEqual(entry, report.data[0])

    def test_adding_default_dict(self):
        """Verify that a default dict can be added to a Report.
        """
        report = Report(self.headings)

        entry = defaultdict(lambda: 'hello')
        report.add_row(entry)

        self.assertEqual(1, len(report.data))
        self.assertEqual(entry, report.data[0])

    def test_adding_multiple_lists(self):
        """Verify that multiple lists can be added to a Report.
        """
        report = Report(self.headings)
        report.add_rows(self.entries)

        self.assertEqual(len(self.entries), len(report.data))
        for expected, actual in zip(self.entries, report.data):
            self.assertEqual(len(expected), len(actual))
            self.assertEqual(expected, list(actual.values()))

    def test_adding_multiple_dicts(self):
        """Verify that multiple dicts can be added to a Report.
        """
        headings = ['name', 'place', 'color']
        report = Report(headings)

        self.assertEqual(headings, report.headings)

        dicts = [dict(zip(headings, x)) for x in self.entries]
        report.add_rows(dicts)

        self.assertEqual(len(self.entries), len(report.data))
        for expected, actual in zip(dicts, report.data):
            self.assertEqual(len(expected), len(actual))
            self.assertEqual(expected, actual)

    def test_adding_list_too_many(self):
        """Lists should not have more entries than report.headings.
        """
        report = Report(self.headings)
        entry = ['too', 'many', 'entries', 'here']

        with self.assertRaises(ValueError):
            report.add_row(entry)

    def test_adding_list_too_few(self):
        """Lists should not have fewer entries than report.headings.
        """
        report = Report(self.headings)

        entry = ['too', 'few']

        with self.assertRaises(ValueError):
            report.add_row(entry)

    def test_adding_super_dict(self):
        """A dict that contains extra headings should be a valid entry.
        """
        report = Report(self.headings)

        entry = dict(zip(self.headings, self.e1))
        entry['extra'] = 'extra'

        report.add_row(entry)
        self.assertEqual(1, len(report.data))
        self.assertEqual(self.e1, list(report.data[0].values()))

    def test_adding_invalid_dict(self):
        """A dict should contain 'at least' the same headings.
        """
        report = Report(self.headings)

        entry = {'name': 'too', 'place': 'few'}
        with self.assertRaises(ValueError):
            report.add_row(entry)

    def test_report_unmodified_by_invalid_entry(self):
        """A report should not be modified if an invalid row is sent.
        """
        report = Report(self.headings)

        valid = self.e1
        invalid = ['too', 'few']

        with self.assertRaises(ValueError):
            report.add_row(valid)
            report.add_row(invalid)

        self.assertEqual(1, len(report.data))
        self.assertEqual(valid, list(report.data[0].values()))

    def test_storing_mixed_primitives(self):
        """Verify that entries can contain any mixture of primitive types.

        The report should store entries and not modify their type.
        """
        headings = ['h1', 'h2', 'h3', 'h4', 'h5']

        entries = []
        entries.append([None, 1, 2.0, True, 'str'])
        entries.append([1, 2.0, True, 'str', None])
        entries.append([2.0, True, 'str', None, 1])
        entries.append([True, 'str', None, 1, 2.0])
        entries.append(['str', None, 1, 2.0, True])

        report = Report(headings, sort_by=0)
        report.add_rows(entries)

        for expected, actual in zip(entries, report.data):
            exp_types = [type(x) for x in expected]
            act_types = [type(x) for x in actual.values()]
            self.assertEqual(exp_types, act_types)

    def test_yaml_dump(self):
        """Verify that yaml dumps can be read by python3-yaml.
        """
        report = Report(self.headings)
        report.add_rows(self.entries)

        yaml_s = report.get_yaml()

        data = yaml.safe_load(yaml_s)
        for expected, actual in zip(self.entries, data):
            # yaml.safe_load sorts keys
            self.assertEqual(sorted(expected), sorted(actual.values()))


class TestReportFormatting(unittest.TestCase):
    """Begin test the Report class's tabular formatting.
    """
    def setUp(self):
        self.headings = ['name', 'place', 'color']

        # Entries are ordered such that sorting on each column yields a
        # a different order. Specifically, by each column:
        #   'name':  e1 < e2 < e3
        #   'place': e3 < e1 < e2
        #   'color': ""
        e1 = ['alice', 'mars', 'red']
        e2 = ['bob', 'venus', 'blue']
        e3 = ['charlie', 'earth', 'purple']

        self.entries = [e1, e2, e3]
        self.entries_as_dict = [dict(zip(self.headings, e))
                                for e in self.entries]
        self.reverse_entries = [e3, e2, e1]
        self.out_of_order = [e1, e3, e2]
        self.sorted_1 = [e3, e1, e2]
        self.sorted_2 = [e2, e3, e1]

    def test_empty_print(self):
        """An empty report should print an empty string.
        """
        report = Report(self.headings)
        self.assertEqual('', str(report))

    def test_regular_print(self):
        """The internal PT should not sort.
        """
        report = Report(self.headings)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.out_of_order, pt_s):
            self.assertEqual(expected, actual)

    def test_sorted_print(self):
        """The internal PT should be sorted on the first column.
        """
        report = Report(self.headings, sort_by=0)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.entries, pt_s):
            self.assertEqual(expected, actual)

    def test_sorted_yaml(self):
        """The YAML output list should be sorted as well.
        """
        report = Report(self.headings, sort_by=0)

        report.add_rows(self.out_of_order)

        loaded_yaml = yaml.safe_load(report.get_yaml())
        self.assertEqual(self.entries_as_dict, loaded_yaml)

    def test_reverse_sorting(self):
        """The internal PT should reverse its order if report.reverse.
        """
        report = Report(self.headings, sort_by=0, reverse=True)

        report.add_rows(self.entries)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.reverse_entries, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_heading_idx(self):
        """Report's PT should sort on a non-zero index.
        """
        report = Report(self.headings, sort_by=1)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.sorted_1, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_heading_name(self):
        """Report's PT should sort on a heading name.
        """
        report = Report(self.headings, sort_by='place')

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.sorted_1, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_heading_case_agnostic(self):
        """Report's PT should sort without regard to case.
        """
        report = Report(self.headings, sort_by='pLaCe')

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.sorted_1, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_heading_invalid(self):
        """The PT should default to not sorting if the heading is not present.
        """
        report = Report(self.headings, sort_by='does-not-exist')

        self.assertEqual(None, report.sort_by)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.out_of_order, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_heading_idx_invalid(self):
        """The PT should not sort if the idx is out-of-range.
        """
        report = Report(self.headings, sort_by=len(self.headings))

        self.assertEqual(None, report.sort_by)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.out_of_order, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_heading_abbreviation(self):
        """The PT should sort if provided an abbreviation of a heading.
        """
        report = Report(self.headings, sort_by='pl')

        self.assertEqual('place', report.sort_by)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.sorted_1, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_unique_subsequence(self):
        """The report should sort on a unique subsequence.
        """
        report = Report(self.headings, sort_by='clr')
        self.assertEqual('color', report.sort_by)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.sorted_2, pt_s):
            self.assertEqual(expected, actual)

    def test_sort_ambiguous_subsequence(self):
        """The report should sort on the first match.
        """
        report = Report(self.headings, sort_by='ae')
        self.assertEqual('name', report.sort_by)

        report.add_rows(self.out_of_order)
        pt_s = get_report_printed_list(report)

        for expected, actual in zip(self.entries, pt_s):
            self.assertEqual(expected, actual)

    def test_sorting_mixed_primitives(self):
        """Verify that entries can contain any mixture of primitive types.

        The report should be capable of printing and sorting any mixture.
        """
        headings = ['h1', 'h2', 'h3', 'h4', 'h5']

        entries = []
        entries.append([None, 1, 2.0, True, 'str'])
        entries.append([1, 2.0, True, 'str', None])
        entries.append([2.0, True, 'str', None, 1])
        entries.append([True, 'str', None, 1, 2.0])
        entries.append(['str', None, 1, 2.0, True])

        str_entries = []
        for entry in entries:
            str_entries.append([str(x) for x in entry])
        str_entries.sort()

        report = Report(headings, sort_by=0)
        report.add_rows(entries)

        pt_s = get_report_printed_list(report)

        for expected, actual in zip(str_entries, pt_s):
            self.assertEqual(expected, actual)
