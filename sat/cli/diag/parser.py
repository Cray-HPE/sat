#
# MIT License
#
# (C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP
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
Functions to create the subparser for the diag command.
"""

from argparse import REMAINDER

import sat.parsergroups


def add_diag_subparser(subparsers):

    xname_opts = sat.parsergroups.create_xname_options()

    diag_parser = subparsers.add_parser(
        'diag', help='Launch diagnostics for hardware controllers.',
        description='Launch diagnostics for hardware controllers.',
        parents=[xname_opts])

    diag_parser.add_argument('-t', '--timeout', default=300, metavar='SECONDS', type=int,
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
