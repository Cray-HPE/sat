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
        help='Report on link health and presence of cables.',
        description='Generates a report on link health based on the results '
                    'from Redfish queries to the Rosetta switches. Values that '
                    'read "MISSING" were unobtainable from Redfish.',
        parents=[format_options, filter_options, redfish_options])

    linkhealth_parser.add_argument(
        '-x', '--xnames', metavar='XNAME',
        action='append', default=[],
        help='Target only the desired xnames. '
             'Multiple xnames may be specified with this option.')
