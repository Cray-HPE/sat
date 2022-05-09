"""
The main entry point for the swap command.

(C) Copyright 2020-2022 Hewlett Packard Enterprise Development LP.

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

import logging

from sat.cli.swap.blade import swap_blade
from sat.cli.swap.cable import swap_cable
from sat.cli.swap.errors import ERR_INVALID_OPTIONS
from sat.cli.swap.switch import swap_switch
from sat.util import pester


LOGGER = logging.getLogger(__name__)


def check_arguments(component_type, action, dry_run, disruptive):
    """Check that given options are valid for a swap.

    Args:
        component_type (str): 'blade', 'switch', or 'cable'
        action (str): 'enable' or 'disable'
        dry_run (bool): if True, skip applying configuration to ports
        disruptive (bool): if True, do not confirm disable/enable

    Raises:
        SystemExit(1): if invalid options
    """
    if not dry_run and not action:
        LOGGER.error('The action option is required if not a dry run, exiting.')
        raise SystemExit(ERR_INVALID_OPTIONS)

    if dry_run and action:
        LOGGER.error('The action option is not valid with the dry run option.')
        raise SystemExit(ERR_INVALID_OPTIONS)

    if not (disruptive or dry_run or
            pester(f'Enable/disable of {component_type} can impact system. Continue?')):
        raise SystemExit(ERR_INVALID_OPTIONS)


def do_swap(args):
    """Perform the specified swap action

    Args:
        args: an argparse Namespace object

    Returns:
        None
    """
    action = getattr(args, 'action', None)
    check_arguments(args.target, action, args.dry_run, args.disruptive)

    if args.target == 'cable':
        swap_cable(args)
    elif args.target == 'switch':
        swap_switch(args)
    elif args.target == 'blade':
        swap_blade(args)
