"""
The parser for the bootsys subcommand.

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

import sat.parsergroups
from sat.cli.bootsys.defaults import DEFAULT_UAN_BOS_TEMPLATE
from sat.cli.bootsys.stages import STAGES_BY_ACTION


def add_bootsys_subparser(subparsers):
    """Add the bootsys subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    redfish_opts = sat.parsergroups.create_redfish_options()

    bootsys_parser = subparsers.add_parser(
        'bootsys', help='Boot or shut down the system.',
        description='Boot or shut down the entire system, including the '
                    'compute nodes, user access nodes, and non-compute '
                    'nodes running the management software.',
        parents=[redfish_opts]
    )

    bootsys_parser.add_argument(
        'action', help='Specify whether to boot or shut down.',
        choices=['boot', 'shutdown']
    )

    stage_group = bootsys_parser.add_mutually_exclusive_group(required=True)

    # TODO: choices are not categorized by boot/shutdown
    stage_group.add_argument(
        '--stage', help='Specify the stage of bootsys to run.',
        choices=set(STAGES_BY_ACTION['boot'] + STAGES_BY_ACTION['shutdown'])
    )

    stage_group.add_argument(
        '--list-stages',
        help='List the stages of bootsys that can be run for the given action.'
    )

    bootsys_parser.add_argument(
        '-i', '--ignore-failures', action='store_true',
        help='Proceed with the shutdown regardless of failed steps.'
    )

    bootsys_parser.add_argument(
        '--ignore-service-failures', action='store_true',
        help='If specified, do not fail to shutdown if querying services '
             'for active sessions fails.',
    )

    bootsys_parser.add_argument(
        '--ignore-pod-failures', action='store_true',
        help='Disregard any failures associated with storing pod state '
             'while shutting down.',
    )

    bootsys_parser.add_argument(
        '--state-check-fail-action',
        choices=['abort', 'skip', 'prompt', 'force'],
        help='Action to take if a failure occurs when checking whether a BOS '
             'session template needs an operation applied based on current node '
             'state in HSM. Defaults to "abort".'
    )

    bootsys_parser.add_argument(
        '--cle-bos-template',
        help='The name of the BOS session template for shutdown/boot of CLE '
             'compute nodes. Defaults to template matching "cle-X.Y.Z".'
    )

    bootsys_parser.add_argument(
        '--uan-bos-template',
        help='The name of the BOS session template for shutdown/boot of User '
             'Access Nodes (UANs). '
             'Defaults to "{}"'.format(DEFAULT_UAN_BOS_TEMPLATE)
        # Note that we don't want to specify the default with the `default`
        # kwarg here because then the value from the config file could never
        # take precedence over the command-line default.
    )

    bootsys_parser.add_argument(
        '--capmc-timeout', default=120, type=int,
        help='Timeout, in seconds, for components to reach desired power state '
             'after a CAPMC operation.'
    )

    bootsys_parser.add_argument(
        '--discovery-timeout', default=600, type=int,
        help='Timeout, in seconds, for node controllers and BMCs to reach the '
             'powered on state after the HMS discovery job is resumed.'
    )

    bootsys_parser.add_argument(
        '--ipmi-timeout', default=300, type=int,
        help='Timeout, in seconds, for nodes to reach desired power state after '
             'IPMI power commands are issued.'
    )

    bootsys_parser.add_argument(
        '--ssh-timeout', default=600, type=int,
        help='Timeout waiting for SSH availability on nodes.'
    )

    bootsys_parser.add_argument(
        '--k8s-timeout', default=1800, type=int,
        help='Timeout waiting for Kubernetes pods to return to '
             'pre-shutdown state.'
    )

    bootsys_parser.add_argument(
        '--ceph-timeout', default=600, type=int,
        help='Timeout waiting for Ceph to come up.'
    )

    bootsys_parser.add_argument(
        '--bgp-timeout', default=600, type=int,
        help='Timeout waiting for BGP routes to become established.'
    )

    bootsys_parser.add_argument(
        '--hsn-timeout', default=600, type=int,
        help='Timeout waiting for HSN bringup.'
    )
