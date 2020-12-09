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
from sat.cli.showrev import containers, products, rpm, system


LOGGER = logging.getLogger(__name__)


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

    if args.all:
        args.system = True
        args.products = True
        args.docker = True
        args.packages = True
        args.release_files = True
    elif not any((args.system, args.products, args.docker, args.packages, args.release_files)):
        args.system = True
        args.products = True

    if args.system:
        data = system.get_system_version(args.sitefile)
        if not data:
            LOGGER.warning('Could not retrieve system version information.')

        else:
            title = 'System Revision Information'
            headings = ['component', 'data']
            reports.append(Report(
                headings, title, sort_by, reverse, no_headings, no_borders,
                filter_strs=args.filter_strs))
            reports[-1].add_rows(data)

    if args.release_files:
        headings, data = products.get_release_file_versions()
        if not data:
            LOGGER.warning('Could not retrieve release file versions.')

        else:
            title = 'Local Release Files'
            reports.append(Report(
                headings, title, sort_by, reverse, no_headings, no_borders,
                filter_strs=args.filter_strs))
            reports[-1].add_rows(data)

    if args.products:
        headings, data = products.get_product_versions()
        if not data:
            LOGGER.warning('Could not retrieve product versions.')

        else:
            title = 'Product Revision Information'
            reports.append(Report(
                headings, title, sort_by, reverse, no_headings, no_borders,
                filter_strs=args.filter_strs))
            reports[-1].add_rows(data)

    if args.docker:
        data = containers.get_dockers()
        if not data:
            LOGGER.warning(
                'Could not retrieve list of installed docker containers.')

        else:
            title = 'Installed Container Versions'
            headings = ['name', 'short-id', 'versions']
            reports.append(Report(
                headings, title, sort_by, reverse, no_headings, no_borders,
                filter_strs=args.filter_strs))
            reports[-1].add_rows(data)

    if args.packages:
        data = rpm.get_rpms()
        if not data:
            LOGGER.warning('Could not retrieve list of installed rpms.')

        else:
            title = 'Installed Package Versions'
            headings = ['name', 'version']
            reports.append(Report(
                headings, title, sort_by, reverse, no_headings, no_borders,
                filter_strs=args.filter_strs))
            reports[-1].add_rows(data)

    if not reports:
        LOGGER.error('No data collected')
        sys.exit(1)

    if args.format == 'yaml':
        for report in reports:
            print(report.get_yaml())
    else:
        for report in reports:
            print(str(report) + '\n\n')
