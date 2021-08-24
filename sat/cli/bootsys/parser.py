"""
The parser for the bootsys subcommand.

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
from collections import namedtuple

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
    TimeoutSpec('ceph', ['boot'], 60,
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
                'management NCNs have completed a graceful shutdown and have reached '
                'the powered off state according to IPMI.'),
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
                f'Timeout, in seconds, to wait until {timeout.condition} '
                f'Defaults to {timeout.default}. Overrides the option '
                f'bootsys.{timeout.option_prefix.replace("-", "_")}_timeout '
                f'in the config file.'
            )

            subparser.add_argument(
                f'--{timeout.option_prefix}-timeout', type=int,
                help=help_text
            )


def _add_bos_template_options(subparser, action):
    """Add the --cle-bos-template and --uan-bos-template options for the action.

    Args:
        subparser: The argparse.ArgumentParser object for the action
        action (str): the action to which the template options apply.

    Returns:
        None
    """
    subparser.add_argument(
        '--bos-templates',
        type=lambda x: x.split(','),
        help=f'A comma-separated list of BOS session templates for {action} '
             f'of compute and UAN nodes. If not specified, the values of '
             f'deprecated options --cle-bos-template and --uan-bos-template '
             f'will be used.'
    )

    subparser.add_argument(
        '--cle-bos-template',
        help=f'The name of the BOS session template for {action} of COS '
             f'compute nodes. If not specified, no COS template will be used. '
             f'This option is deprecated in favor of --bos-templates. It will '
             f'be ignored if --bos-templates or its configuration-file '
             f'equivalent bos_templates is specified.'
    )

    subparser.add_argument(
        '--uan-bos-template',
        help=f'The name of the BOS session template for {action} of User '
             f'Access Nodes (UANs). If not specified, no UAN template will be '
             f'used. This option is deprecated in favor of --bos-templates. It '
             f'will be ignored if --bos-templates or its configuration-file '
             f'equivalent bos_templates is specified.'
    )


def _add_stage_options(subparser, action):
    """Add the --stage and --list-stages options appropriate to action.

    Args:
        subparser: The argparse.ArgumentParser object for the action
        action (str): the action to which the stages apply.

    Returns:
        None
    """
    # Preserve backwards compatibility where `sat bootsys shutdown` would just
    # run service checks.
    stage_required = action != 'shutdown'
    stage_group = subparser.add_mutually_exclusive_group(required=stage_required)

    stage_group.add_argument(
        '--stage', help=f'Specify the stage of the {action} to run.',
        choices=STAGES_BY_ACTION[action]
    )

    stage_group.add_argument(
        '--list-stages', action='store_true',
        help='List the stages of bootsys that can be run for the given action.'
    )


def _add_excluded_ncns_option(subparser):
    """Add the --excluded-ncns option to the subparser.

    Args:
        subparser: The argparse.ArgumentParser object for the bootsys action

    Returns:
        None
    """
    subparser.add_argument(
        '--excluded-ncns',
        help='Comma-separated list of NCN hostnames to exclude from ncn-power '
             'and platform-services stages. Only use this option to exclude '
             'inaccessible NCNs that are already outside of the Kubernetes '
             'cluster.',
        type=lambda x: {item.strip() for item in x.split(',')},
        default=set()
    )


def _add_bootsys_action_subparser(subparsers, action):
    """Add the shutdown subparser to the parent bootsys parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.
        action (str): The action to add the parser for.

    Returns:
        None
    """
    action_parser = subparsers.add_parser(
        action, help=f'Perform a {action} operation',
        description=f'Performs a portion of the {action} operation on the system.'
    )
    action_parser.add_argument('--disruptive', action='store_true',
                               help='Do not prompt for confirmation before performing '
                                    'disruptive actions.')

    _add_stage_options(action_parser, action)
    _add_bos_template_options(action_parser, action)
    _add_timeout_options(action_parser, action)
    _add_excluded_ncns_option(action_parser)


def _add_bootsys_shutdown_subparser(subparsers):
    """Add the shutdown subparser to the parent bootsys parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    _add_bootsys_action_subparser(subparsers, 'shutdown')


def _add_bootsys_boot_subparser(subparsers):
    """Add the boot subparser to the parent bootsys parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    _add_bootsys_action_subparser(subparsers, 'boot')


def add_bootsys_subparser(subparsers):
    """Add the bootsys subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    bootsys_parser = subparsers.add_parser(
        'bootsys', help='Boot or shut down the system.',
        description='Boot or shut down the entire system, including the '
                    'compute nodes, user access nodes, and non-compute '
                    'nodes running the management software.',
    )

    actions_subparsers = bootsys_parser.add_subparsers(
        metavar='action', dest='action', help='The action to perform.'
    )

    _add_bootsys_shutdown_subparser(actions_subparsers)
    _add_bootsys_boot_subparser(actions_subparsers)
