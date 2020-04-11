"""
The main entry point for the showrev subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import logging
import sys

from sat.config import get_config_value
from sat.report import Report
from sat.cli.showrev import containers, products, rpm, system


LOGGER = logging.getLogger(__name__)


def do_showrev(args):
    """Run the showrev comand with the given arguments.

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
    elif not any((args.system, args.products, args.docker, args.packages)):
        args.system = True
        args.products = True

    if args.system:
        data = system.get_system_version(args.sitefile, args.substr)
        if not data:
            LOGGER.warning('Could not retrieve system version information.')

        else:
            title = 'System Revision Information'
            headings = ['component', 'data']
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
        data = containers.get_dockers(args.substr)
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
        data = rpm.get_rpms(args.substr)
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
