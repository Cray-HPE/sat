"""
The parser for the linkhealth subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""

import sat.parsergroups


def add_linkhealth_subparser(subparsers):
    """Add the linkhealth subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.
    """
    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()
    redfish_options = sat.parsergroups.create_redfish_options()

    linkhealth_parser = subparsers.add_parser(
        'linkhealth',
        help='Report links that are unhealthy.',
        description='Generate a health report for the links in a system. '
                    'The default behavior of this command is to only '
                    'target configured nodes that are not "OK".',
        parents=[format_options, filter_options, redfish_options])

    linkhealth_parser.add_argument(
        '--all', action='store_true',
        help='Show all links in the report. This does not impact filtering '
             'on the desired xnames.')

    linkhealth_parser.add_argument(
        '--configured', action='store_true',
        help='Show all links determined to be "configured".')

    linkhealth_parser.add_argument(
        '--unhealthy', action='store_true',
        help='Show all unhealthy links - even ones which happen '
             'to be "unconfigured".')

    linkhealth_parser.add_argument(
        '-x', '--xname', dest='xnames', metavar='XNAME',
        action='append', default=[],
        help='Target only the desired xnames. '
             'Multiple xnames may be specified with this option.')
