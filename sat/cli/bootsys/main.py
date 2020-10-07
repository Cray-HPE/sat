"""
Entry point for the bootsys subcommand.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
import sys

from sat.cli.bootsys.stages import STAGES_BY_ACTION, load_stage


LOGGER = logging.getLogger(__name__)


def do_bootsys(args):
    """Perform a single stage of a boot or shutdown operation on the system.

    A full system shutdown consists of the following stages:

        * Capturing state of Kubernetes pods and HSN links
        * Checking for service idleness
        * Shutting down all computes and UANs using BOS
        * Powering off liquid-cooled cabinets
        * Establish BGP peering sessions and wait for them to be established.
        * Shutting down management software on NCNs
        * Shutting down and powering off all NCNs

    A full system boot includes the following steps at a high level:

        * Powering on and booting all NCNs
        * Starting all management software on NCNs
        * Verifying health of management software services
        * Verifying health of Ceph storage
        * Establish BGP peering sessions and wait for them to be established
        * Powering on liquid-cooled cabinets
        * Bring up HSN and wait for it to be healthy
        * Booting the computes and UANs using BOS

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    # TODO: remove
    if args.ignore_failures:
        args.ignore_service_failures = True
        args.ignore_pod_failures = True
    if args.list_stages:
        try:
            for stage in STAGES_BY_ACTION[args.action].keys():
                print(stage)
        # Should not happen the way arguments are parsed
        except KeyError:
            LOGGER.error('Invalid action: %s', args.action)
            sys.exit(1)
        sys.exit(0)

    try:
        submodule, stage_func_name = STAGES_BY_ACTION[args.action][args.stage]
        stage = load_stage(submodule, stage_func_name)
        stage(args)
    except KeyError:
        LOGGER.error('Invalid stage received for %s action: %s', args.action, args.stage)
        sys.exit(1)
