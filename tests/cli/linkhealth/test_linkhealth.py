"""
Unit tests for the sat.sat.cli.linkhealth.main functions.

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


import unittest
from unittest import mock
from argparse import Namespace
from sat.apiclient import APIError
from sat.xname import XName

import sat.cli.linkhealth.main


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.xnames = []
    namespace.xname_file = ""
    namespace.redfish_username = "yogibear"
    namespace.no_borders = True
    namespace.no_headings = False
    namespace.format = 'pretty'
    namespace.reverse = object()
    namespace.sort_by = object()
    namespace.filter_strs = object()


class FakeReport:
    """Used for mocking the return from get_report."""
    def get_yaml(self):
        return '---'


class TestDoLinkhealth(unittest.TestCase):
    """Unit test for linkhealth do_linkhealth()."""

    def setUp(self):
        """Mock things outside of do_linkhealth."""

        self.mock_log_debug = mock.patch('sat.logging.LOGGER.debug',
                                         autospec=True).start()
        self.mock_log_error = mock.patch('sat.logging.LOGGER.error',
                                         autospec=True).start()

        self.mock_bmc_xnames = [XName('x1000c0r0b0'), XName('x1000c12r13b14'), XName('x3000c0r0b0')]
        self.mock_get_bmc_xnames = mock.patch(
            'sat.redfish.get_bmc_xnames',
            autospec=True).start()
        self.mock_get_bmc_xnames.return_value = self.mock_bmc_xnames

        self.mock_port_mappings = {'x1000c0r0b0j0p0': ['addr-stuff']}
        self.mock_get_jack_port_ids = mock.patch(
            'sat.cli.linkhealth.main.get_jack_port_ids',
            autospec=True).start()
        self.mock_get_jack_port_ids.return_value = self.mock_port_mappings

        self.mock_get_username_and_pass = mock.patch(
            'sat.redfish.get_username_and_pass',
            autospec=True).start()
        self.mock_get_username_and_pass.return_value = ('ginger', 'Spice32')

        self.mock_query = mock.patch(
            'sat.redfish.query',
            autospec=True).start()
        self.mock_query.return_value = ('url', {'Members': []})

        self.mock_disable_warnings = mock.patch(
            'urllib3.disable_warnings',
            autospec=True).start()

        self.mock_report_cls = mock.patch('sat.cli.linkhealth.main.Report',
                                          autospec=True).start()
        self.mock_report_obj = self.mock_report_cls.return_value

        self.mock_get_report = mock.patch('sat.cli.linkhealth.main.get_report',
                                          autospec=True).start()
        self.mock_get_report.return_value = FakeReport()

        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.parsed = Namespace()
        set_options(self.parsed)

    def tearDown(self):
        mock.patch.stopall()

    def test_no_xname_option(self):
        """Test Linkhealth: do_linkhealth() no xname option"""
        sat.cli.linkhealth.main.do_linkhealth(self.parsed)
        self.mock_get_bmc_xnames.assert_called_once()
        # List returned by get_bmc_xnames becomes argument:
        self.mock_get_jack_port_ids.assert_called_once_with(
            self.mock_bmc_xnames, 'ginger', 'Spice32'
        )
        self.mock_get_report.assert_called_once()
        self.mock_print.assert_called_once()

    def test_no_xname_option_yaml(self):
        """Test Linkhealth: do_linkhealth() no xname option, yaml output"""
        self.parsed.format = 'yaml'
        sat.cli.linkhealth.main.do_linkhealth(self.parsed)
        self.mock_get_bmc_xnames.assert_called_once()
        self.mock_get_jack_port_ids.assert_called_once_with(
            self.mock_bmc_xnames, 'ginger', 'Spice32')
        self.mock_get_report.assert_called_once()
        self.mock_print.assert_called_once()

    def test_with_one_xname(self):
        """Test Linkhealth: do_linkhealth() with one xname"""
        self.parsed.xnames = ['x1000c12r13b14']
        sat.cli.linkhealth.main.do_linkhealth(self.parsed)
        self.mock_get_bmc_xnames.assert_called_once()
        # Set returned by get_matches becomes argument.
        self.mock_get_jack_port_ids.assert_called_once_with(
            {XName('x1000c12r13b14')}, 'ginger', 'Spice32')
        self.mock_get_report.assert_called_once()
        self.mock_print.assert_called_once()

    def test_with_two_xnames(self):
        """Test Linkhealth: do_linkhealth() with two xnames"""
        self.parsed.xnames = ['x1000c12r13b14', 'x3000c0r0b0']
        sat.cli.linkhealth.main.do_linkhealth(self.parsed)
        # Set returned by get_matches becomes argument.
        self.mock_get_bmc_xnames.assert_called_once()
        self.mock_get_jack_port_ids.assert_called_once_with(
            {XName('x1000c12r13b14'), XName('x3000c0r0b0')}, 'ginger', 'Spice32')
        self.mock_get_report.assert_called_once()
        self.mock_print.assert_called_once()

    def test_with_xname_option_yaml(self):
        """Test Linkhealth: do_linkhealth() with xname option, yaml output"""
        self.parsed.xnames = ['x1000c12r13b14']
        self.parsed.format = 'yaml'
        sat.cli.linkhealth.main.do_linkhealth(self.parsed)
        self.mock_get_bmc_xnames.assert_called_once()
        # Set returned by get_matches becomes argument.
        self.mock_get_jack_port_ids.assert_called_once_with(
            {XName('x1000c12r13b14')}, 'ginger', 'Spice32')
        self.mock_get_report.assert_called_once()
        self.mock_print.assert_called_once()

    def test_get_bmc_xnames_exception(self):
        """Test Linkhealth: do_linkhealth() get_bmc_names exception"""
        self.mock_get_bmc_xnames.side_effect = APIError
        with self.assertRaises(APIError):
            sat.cli.linkhealth.main.do_linkhealth(self.parsed)

    def test_no_jack_port_ids(self):
        """Test Linkhealth: do_linkhealth() no jack port IDs"""
        self.mock_get_jack_port_ids.return_value = []
        with self.assertRaises(SystemExit):
            sat.cli.linkhealth.main.do_linkhealth(self.parsed)


if __name__ == '__main__':
    unittest.main()
