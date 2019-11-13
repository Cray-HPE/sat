"""
The main entry point for the showrev subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import logging

from sat.config import get_config_value
from sat.report import Report
from sat.showrev import containers, rpm, system


LOGGER = logging.getLogger(__name__)


def showrev(args):
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
        args.docker = True
        args.packages = True
    elif not args.system and not args.docker and not args.packages:
        args.system = True

    if args.system:
        data = system.get_system_version(args.sitefile, args.substr)
        if data is None:
            LOGGER.error('Could not print system version information.')
            exit(1)

        title = 'System Revision Information'
        headings = ['component', 'data']
        reports.append(Report(
            headings, title, sort_by, reverse, no_headings, no_borders,
            filter_strs=args.filter_strs))
        reports[-1].add_rows(data)

    if args.docker:
        data = containers.get_dockers(args.substr)
        if data is None:
            LOGGER.error(
                'Could not retrieve list of installed docker containers.')
            exit(1)

        title = 'Installed Container Versions'
        headings = ['name', 'short-id', 'versions']
        reports.append(Report(
            headings, title, sort_by, reverse, no_headings, no_borders,
            filter_strs=args.filter_strs))
        reports[-1].add_rows(data)

    if args.packages:
        data = rpm.get_rpms(args.substr)
        if data is None:
            LOGGER.error('Could not retrieve list of installed rpms.')
            exit(1)

        title = 'Installed Package Versions'
        headings = ['name', 'version']
        reports.append(Report(
            headings, title, sort_by, reverse, no_headings, no_borders,
            filter_strs=args.filter_strs))
        reports[-1].add_rows(data)

    if args.format == 'yaml':
        for report in reports:
            print(report.get_yaml())
    else:
        for report in reports:
            print(report.get_pretty_table() + '\n\n')
