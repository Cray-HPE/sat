"""""
Functions to create the subparser for the diag command.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from argparse import REMAINDER


def add_diag_subparser(subparsers):
    diag_parser = subparsers.add_parser('diag', help='Launch diagnostics for Rosetta switches.')

    xnames_group = diag_parser.add_argument_group('xnames', 'methods of specifying target xnames')
    xnames_group.add_argument('-f', '--xname-file', metavar='PATH',
                              help='Path to a newline-delimited file containing '
                              'xnames of all switches to be tested')
    xnames_group.add_argument('-x', '--xname', action='append', dest='xnames', metavar='XNAME',
                              default=[], help='An xname on which the diagnostic should be run. '
                              'Multiple xnames may be specified with this option')

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
