"""
The parser for the swap subcommand.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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


def _add_common_arguments(parser, component):
    """Add arguments that are common to swap commands.

    Args:
        parser: an argparse ArgumentParser.
        component (str): what component is being swapped, to fill in help text.

    Returns:
        None
    """

    parser.add_argument(
        '--action', '-a', choices=['disable', 'enable'],
        help=f'Perform action to disable/enable the {component}. Required if not a dry run.')

    parser.add_argument(
        '--save-ports', '-s', action='store_true',
        help=f'Save {component} ports JSON as <xname>-ports.json file in current directory.')

    parser.add_argument(
        '--disruptive', action='store_true',
        help='Do not ask whether to continue.')

    parser.add_argument(
        '--dry-run', action='store_true',
        help=f'Perform a dry run without enable/disable of the {component}.')


def _add_swap_cable_subparser(subparsers):
    """Add the swap cable subparser to the parent (swap) parser.

    Args:
        subpparsers: an argparse ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    swap_cable_parser = subparsers.add_parser(
        'cable', help='Enable or disable ports to which a cable is connected.',
        description='Prepare cable for replacement, and bring cable into service.')
    swap_cable_parser.add_argument('xnames', nargs='+', help='The xname of the cable.')
    swap_cable_parser.add_argument('--force', '-f', action='store_true',
                                   help='Do not verify jack xnames are connected by a cable.')
    _add_common_arguments(swap_cable_parser, 'cable')


def _add_swap_switch_subparser(subparsers):
    """Add the swap switch subparser to the parent (swap) parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    switch_parser = subparsers.add_parser(
        'switch', help='Enable or disable ports on a switch.',
        description='Prepare switch for replacement, and bring switch into service.')

    switch_parser.add_argument('xname', help='The xname of the switch.')
    _add_common_arguments(switch_parser, 'switch')


def add_swap_subparser(subparsers):
    """Add the swap subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    swap_parser = subparsers.add_parser('swap', help='Disable/enable a component before/after replacement.')

    target_subparsers = swap_parser.add_subparsers(metavar='target', dest='target', help='The component to swap.')

    _add_swap_switch_subparser(target_subparsers)
    _add_swap_cable_subparser(target_subparsers)
