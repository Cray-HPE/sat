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
    format_opts = sat.parsergroups.create_format_options()
    filter_opts = sat.parsergroups.create_filter_options()
    redfish_opts = sat.parsergroups.create_redfish_options()
    xname_opts = sat.parsergroups.create_xname_options()

    linkhealth_parser = subparsers.add_parser(
        'linkhealth',
        help='Report on link health and presence of cables.',
        description='Generates a report on link health based on the results '
                    'from Redfish queries to the Rosetta switches. Values '
                    'that read "MISSING" were unobtainable from Redfish.',
        parents=[xname_opts, format_opts, filter_opts, redfish_opts])
