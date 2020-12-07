"""
The main entry point for the showrev subcommand.

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
import sys

from sat.config import get_config_value
from sat.report import Report
from sat.cli.showrev import containers, local, products, rpm, system


LOGGER = logging.getLogger(__name__)


def assign_default_args(args):
    """Set default options in 'args'

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None. Modifies args in place.
    """
    if args.all:
        args.system = True
        args.products = True
        args.docker = True
        args.local = True
        args.packages = True
        args.release_files = True
    elif not any((args.system, args.products, args.local, args.docker, args.packages, args.release_files)):
        args.local = True
        args.system = True
        args.products = True


def do_showrev(args):
    """Run the showrev command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    reports = []

    # report formatting
    sort_by = args.sort_by
    reverse = args.reverse
    no_headings = get_config_value('format.no_headings')
    no_borders = get_config_value('format.no_borders')

    def append_report(title, headings, data):
        """Create a new Report and add it to the list of reports.

        Args:
            title: The title of the new Report to create.
            headings: A list of strings describing the heading elements
                of the Report
            data: A list of tuples where each element is a row to add to
                the new Report

        Returns:
            None.  Modifies reports in place.
        """
        if not data:
            LOGGER.warning('Could not retrieve "%s"', title)
        else:
            reports.append(Report(
                headings, title, sort_by, reverse, no_headings, no_borders,
                filter_strs=args.filter_strs))
            reports[-1].add_rows(data)

    assign_default_args(args)

    if args.system:
        append_report(
            'System Revision Information',
            ['component', 'data'],
            system.get_system_version(args.sitefile)
        )

    if args.release_files:
        release_headings, release_data = products.get_release_file_versions()
        append_report(
            'Local Release Files',
            release_headings,
            release_data
        )

    if args.products:
        product_headings, product_data = products.get_product_versions()
        append_report(
            'Product Revision Information',
            product_headings,
            product_data
        )

    if args.local:
        append_report(
            'Local Host Operating System',
            ['component', 'version'],
            local.get_local_os_information()
        )

    if args.docker:
        append_report(
            'Installed Container Versions',
            ['name', 'short-id', 'versions'],
            containers.get_dockers()
        )

    if args.packages:
        append_report(
            'Installed Package Versions',
            ['name', 'version'],
            rpm.get_rpms()
        )

    if not reports:
        LOGGER.error('No data collected')
        sys.exit(1)

    if args.format == 'yaml':
        for report in reports:
            print(report.get_yaml())
    else:
        for report in reports:
            print(str(report) + '\n\n')
