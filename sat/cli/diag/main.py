#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
The main entry point for the diag subcommand.
"""

from collections import defaultdict
from datetime import date
import logging
import sys

import inflect

from sat.apiclient import APIError, HSMClient
from sat.cli.diag.fox import RunningDiagPool
from sat.session import SATSession
from sat.util import pester


inf = inflect.engine()
LOGGER = logging.getLogger(__name__)

_PROMPT_USAGE = """\
Usage:
    'help': prints this help message
    'exit': exits the diagnostic shell
    'quit': alias for exit
    <command> <arg1> <arg2> ... <argN>: run a diagnostic command with
        N arguments on the switch
"""


def report(finished_diags, timestamp, split):
    """Composes a report of the results of completed diagnostics.

    This will print all outputs from diags returned by Fox, followed
    by a summary of the completion status of all xnames running diagnostics.

    Args:
        finished_diags: a RunningDiagPool object containing the
            diags which have completed.
        timestamp (str): The time at which the diagnostics started,
            used for writing output to a file.
        split (bool): if True, then the content of stdout from
            each diagnostic will be written to its own file.
            Otherwise, all output is written to stdout.
    """
    completion_stats = defaultdict(list)
    for diag in finished_diags.completed:
        LOGGER.info("{} finished diag {} with status '{}'."
                    .format(diag.xname, diag.name, diag.taskstate))
        if hasattr(diag, 'messages'):
            message = diag.messages[0]  # Treat list as single element
            diag_output = message['Message'].replace('\\n', '\n')
            severity = message['Severity']
            completion_stats[severity].append(diag.xname)

            if split:
                output_filename = '{}-{}-{}.out'.format(diag.xname, diag.name, timestamp)
                with open(output_filename, 'w') as output_file:
                    output_file.write(diag_output)
                LOGGER.info('Wrote output from %s to %s', diag.xname, output_filename)

            else:
                print(diag_output)

    for diag in finished_diags.not_completed:
        LOGGER.info('{} did not complete diag {}. Status: {}'
                    .format(diag.xname, diag.name, diag.taskstate))

    for sev, controllers in completion_stats.items():
        if sev != 'OK':
            print('{}: {}'
                  .format(sev, inf.join(controllers)))
    # Summary line
    print(inf.join(['{} {} {}'
                    .format(len(xnames), inf.plural('controller', len(xnames)), severity)
                    for severity, xnames in completion_stats.items()]))


def run_diag_set(xnames, diag_command, diag_args, cli_args):
    """Runs a diagnostic on some set of xnames.

    Args:
        xnames ([str]): xnames on which diags should be run.
        diag_command (str): the command to run on the xnames.
        diag_args ([str]): args to pass to diag_command.
        cli_args (Namespace): contains CLI arguments determining
            behavior of the diagnostics.
    """
    running_diags = None
    try:
        # Initialize all diags
        running_diags = RunningDiagPool(
            xnames, diag_command, diag_args,
            cli_args.interval, cli_args.timeout)

        # Continually poll until all diags have launched,
        # then poll until all have completed.
        running_diags.poll_until_launched()
        running_diags.poll_until_complete()

        report(running_diags,
               date.fromtimestamp(running_diags.starttime).strftime("%Y%m%d-%H%M%S"),
               cli_args.split)

    except APIError as err:
        LOGGER.error(err)
    finally:
        if running_diags is not None:
            running_diags.cleanup()


def run_diags_from_prompt(xnames, cli_args):
    """Prompts the user for diags to run.

    The user is prompted on stdin until Ctrl-C or Ctrl-D is pressed,
    or the string 'quit' or 'exit' is typed.

    Args:
        - xnames ([str]): xnames to run diags on.
        - cli_args (argparse.Namespace): arguments from the command line.

    """
    while True:
        try:
            cmd_string = input("diag> ")
        except EOFError:
            break

        if cmd_string in ('quit', 'exit'):
            break
        elif cmd_string == 'help':
            print(_PROMPT_USAGE)
            continue

        cmd_tokens = cmd_string.strip().split(' ')
        diag_command, diag_args = cmd_tokens[0], cmd_tokens[1:]
        if not diag_command:
            print(_PROMPT_USAGE)
            continue

        run_diag_set(xnames, diag_command, diag_args, cli_args)


def get_rosetta_switches():
    """Get a set containing xnames of all compoments of type RouterBMC.

    Returns:
        A set of xnames for all Rosetta switches on the system.
    """

    api_client = HSMClient(SATSession())
    try:
        return set(bmc['ID'] for bmc in api_client.get_bmcs_by_type(bmc_type='RouterBMC'))
    except APIError as err:
        LOGGER.error("Could not get RouterBMC components from HSM: %s", err)
        sys.exit(1)


def do_diag(args):
    """Runs the diag command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the arguments passed to
            the `diag` subcommand.

    Returns:
        None.
    """
    if not args.xnames:
        LOGGER.error("No xnames were supplied.")
        sys.exit(1)

    if bool(args.interactive) == bool(args.diag_command):
        LOGGER.error("Exactly one of `--interactive` or a command may be given; "
                     "they must not be used together, but one must be specified.")
        sys.exit(1)

    if not args.no_hsm_check:
        available_rosetta_switches = get_rosetta_switches()
        non_rosetta_targets = set(args.xnames) - available_rosetta_switches
        if non_rosetta_targets:
            LOGGER.error("sat diag may only be used with Rosetta switches. "
                         "The following targets are not Rosetta switches: %s",
                         inf.join(list(non_rosetta_targets)))
            LOGGER.info("Available Rosetta switches: %s", inf.join(list(available_rosetta_switches)))
            sys.exit(1)

    really_run = args.disruptive \
        or pester("Controller diagnostics can degrade or disrupt "
                  "a running system. Really proceed?")
    if not really_run:
        sys.exit(0)

    if args.interactive:
        run_diags_from_prompt(args.xnames, args)
    else:
        run_diag_set(args.xnames, args.diag_command, args.diag_args, args)
