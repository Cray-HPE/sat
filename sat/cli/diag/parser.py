"""""
Functions to create the subparser for the diag command.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from argparse import REMAINDER

import sat.parsergroups


def add_diag_subparser(subparsers):

    xname_opts = sat.parsergroups.create_xname_options()

    diag_parser = subparsers.add_parser(
        'diag', help='Launch diagnostics for Rosetta switches.',
        description='Launch diagnostics for Rosetta switches.',
        parents=[xname_opts])

    diag_parser.add_argument('-t', '--timeout', default=300, metavar='SECONDS',
                             help='Timeout for a diagnostic run on a switch')
    diag_parser.add_argument('-i', '--interval', default=10, metavar='SECONDS', type=int,
                             help='Interval at which to poll the switch running the diagnostic')
    diag_parser.add_argument('--disruptive', action='store_true',
                             help='Some diagnostics may be disruptive to a running system. '
                             'Passing --disruptive confirms that the user really intends to do '
                             'potentially dangerous actions')
    diag_parser.add_argument('--split', action='store_true',
                             help='Write a split report, writing output from each switch '
                             'to its own file rather than stdout.')

    diag_parser.add_argument('--interactive', action='store_true',
                             help='launch an interactive shell for running diagnostics.')
    diag_parser.add_argument('diag_command', metavar='command', nargs='?',
                             help='diagnostic command to run on the switch')
    diag_parser.add_argument('diag_args', metavar='args', nargs=REMAINDER,
                             help='arguments to pass to the diagnostic command')
