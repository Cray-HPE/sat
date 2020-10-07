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
from collections import namedtuple

import sat.parsergroups
from sat.cli.bootsys.defaults import DEFAULT_UAN_BOS_TEMPLATE
from sat.cli.bootsys.stages import STAGES_BY_ACTION


TimeoutSpec = namedtuple('TimeoutSpec', ['option_prefix', 'applicable_actions',
                                         'default', 'condition'])

TIMEOUT_SPECS = [
    TimeoutSpec('capmc', ['shutdown'], 120,
                'components reach powered off state after they are shutdown with CAPMC.'),
    TimeoutSpec('discovery', ['boot'], 600,
                'node controllers (NodeBMCs) reach the powered on state '
                'after the HMS Discovery cronjob is resumed.'),
    TimeoutSpec('ipmi', ['boot', 'shutdown'], 60,
                'management NCNs reach the desired power state after IPMI '
                'power commands are issued.'),
    TimeoutSpec('ncn-boot', ['boot'], 300,
                'management nodes are reachable via SSH after boot.'),
    TimeoutSpec('k8s', ['boot'], 600,
                'Kubernetes pods have returned to their pre-shutdown state.'),
    TimeoutSpec('ceph', ['boot'], 600,
                'ceph has returned to a healthy state.'),
    TimeoutSpec('bgp', ['boot', 'shutdown'], 600,
                'BGP routes report that they are established on management switches.'),
    TimeoutSpec('hsn', ['boot'], 300,
                'the high-speed network (HSN) has returned to its pre-shutdown state.'),
    TimeoutSpec('bos-shutdown', ['shutdown'], 600,
                'compute and application nodes have completed their BOS shutdown.'),
    TimeoutSpec('bos-boot', ['boot'], 900,
                'compute and application nodes have completed their BOS boot.'),
    TimeoutSpec('ncn-shutdown', ['shutdown'], 300,
                'management NCNs have completed a graceful shutdown and have reached'
                'the powered off state according to IMPI.'),
]


def _add_timeout_options(subparser, action):
    """Add the timeouts that apply to an action to the subparser for the action.

    Args:
        subparser: The argparse.ArgumentParser object for the action
        action: The name of the action.

    Returns:
        None.
    """
    for timeout in TIMEOUT_SPECS:
        if action in timeout.applicable_actions:

            help_text = (
                f'Timeout, in seconds, to wait until {timeout.condition}.'
                f'Defaults to {timeout.default}. Overrides the option '
                f'bootsys.{timeout.option_prefix.replace("-", "_")}_timeout '
                f'in the config file.'
            )

            subparser.add_argument(
                f'--{timeout.option_prefix}-timeout', type=int,
                help=help_text
            )


def _add_stage_options(subparser, action):
    """Add the --stage and --list-stages options appropriate to action.

    Args:
        subparser: The argparse.ArgumentParser object for the action
        action (str): the action to which the stages apply.

    Returns:
        None
    """
    stage_group = subparser.add_mutually_exclusive_group(required=True)

    # TODO: choices are not categorized by boot/shutdown
    stage_group.add_argument(
        '--stage', help=f'Specify the stage of the {action} to run.',
        choices=STAGES_BY_ACTION[action]
    )

    stage_group.add_argument(
        '--list-stages', action='store_true',
        help='List the stages of bootsys that can be run for the given action.'
    )


def _add_bootsys_shutdown_subparser(subparsers):
    """Add the shutdown subparser to the parent bootsys parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    shutdown_parser = subparsers.add_parser(
        'shutdown', help='Perform a shutdown operation',
        description='Performs a portion of the shutdown operation on the system.'
    )
    _add_stage_options(shutdown_parser, 'shutdown')
    _add_timeout_options(shutdown_parser, 'shutdown')


def _add_bootsys_boot_subparser(subparsers):
    """Add the boot subparser to the parent bootsys parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    boot_parser = subparsers.add_parser(
        'boot', help='Perform a boot operation',
        description='Performs a portion of the boot operation on the system.'
    )
    _add_stage_options(boot_parser, 'boot')
    _add_timeout_options(boot_parser, 'boot')


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

    actions_subparsers = bootsys_parser.add_subparsers(
        metavar='action', dest='action', help='The action to perform.'
    )

    _add_bootsys_shutdown_subparser(actions_subparsers)
    _add_bootsys_boot_subparser(actions_subparsers)

    # TODO: Remove the ignore* options
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

    # TODO: Remove the state-check-fail-action option
    bootsys_parser.add_argument(
        '--state-check-fail-action',
        choices=['abort', 'skip', 'prompt', 'force'],
        help='Action to take if a failure occurs when checking whether a BOS '
             'session template needs an operation applied based on current node '
             'state in HSM. Defaults to "abort".'
    )

    # TODO: Move into the _add_bootsys_ACTION_subparsers so the options are
    # under the action subparser.
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