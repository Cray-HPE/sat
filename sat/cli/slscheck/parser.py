#
# MIT License
#
# (C) Copyright 2021, 2025 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
The parser for the slscheck subcommand.
"""

import sat.parsergroups
from sat.constants import BMC_TYPES


TYPES = ['CabinetPDUController', 'CDUMgmtSwitch', 'Node'] + list(BMC_TYPES)
CHECKS = [
    'Class',
    'Component',
    'RFEndpoint',
    'Role'
]


def add_slscheck_subparser(subparsers):
    """Add the slscheck subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()

    slscheck_parser = subparsers.add_parser(
        'slscheck', help='Perform a cross-check between SLS and HSM.',
        description='Perform a cross-check between SLS and HSM.',
        parents=[format_options, filter_options]
    )

    slscheck_parser.add_argument('-c', '--checks',
                                 metavar='CHECK',
                                 nargs='+',
                                 choices=CHECKS,
                                 default=CHECKS,
                                 help=f'Limit the checks of SLS components to '
                                      f'the cross-checks listed. '
                                      f'The default is to perform all cross-checks: {CHECKS}.')

    slscheck_parser.add_argument('-t', '--types',
                                 metavar='TYPE',
                                 nargs='+',
                                 choices=TYPES,
                                 default=TYPES,
                                 help=f'Limit the checks of SLS components to '
                                      f'the types listed. '
                                      f'The default is to cross-check all types: {TYPES}.')

    slscheck_parser.add_argument('-i', '--include-consistent',
                                 dest='include_consistent',
                                 default=False,
                                 action='store_true',
                                 help='Include list of SLS components that are consistent '
                                      'with HSM components.')
