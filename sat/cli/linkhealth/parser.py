"""
The parser for the linkhealth subcommand.
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
