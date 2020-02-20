"""
The main entry point for the diag subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from collections import defaultdict
from datetime import date
import logging
import sys
import time

import inflect

from sat import redfish as sat_redfish
from sat.cli.diag import redfish as diag_redfish
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

    This will print all outputs from diags returned by Redfish,
    followed by a summary of the completion status of all xnames
    running diagnostics.

    Args:
        finished_diags: a RunningDiagPool object containing the
            diags which have completed.
        split (bool): if True, then the content of stdout from
            each diagnostic will be written to its own file.
            Otherwise, all output is written to stdout.
    """
    completion_stats = defaultdict(list)
    for diag in finished_diags.completed:
        print("{} finished diag {} with status '{}'."
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
        print('{} did not complete diag {}. Status: {}'
              .format(diag.xname, diag.name, diag.taskstate))

    for sev, switches in completion_stats.items():
        if sev != 'OK':
            print('{}: {}'
                  .format(sev, inf.join(switches)))
    # Summary line
    print(inf.join(['{} {} {}'
                    .format(len(xnames), inf.plural('switch', len(xnames)), severity)
                    for severity, xnames in completion_stats.items()]))


def run_diag_set(xnames, diag_command, diag_args,
                 cli_args, username, password):
    """Runs a diagnostic on some set of xnames.

    Args:
        xnames ([str]): xnames on which diags should be run.
        diag_command (str): the command to run on the xnames.
        diag_args ([str]): args to pass to diag_command.
        cli_args (Namespace): contains CLI arguments determining
            behavior of the diagnostics.
        username (str): username to authenticate against the
            Rosetta Redfish endpoint.
        password (str): password to authenticate against the
            Rosetta Redfish endpoint.
    """
    print_report = True
    running_diags = None
    try:
        # Initialize all diags
        running_diags = diag_redfish.RunningDiagPool(
            xnames, diag_command, diag_args,
            cli_args.interval, cli_args.timeout,
            username, password)

        # Continually poll until all diags are complete.
        while not running_diags.complete:
            running_diags.poll_diag_statuses()
            time.sleep(0.1)

    except KeyboardInterrupt:
        print_report = False
        LOGGER.info("Received keyboard interrupt. Attempting to cancel diagnostics...")
        if running_diags is not None:
            for diag in running_diags:
                diag.cancel()

        raise

    finally:
        if print_report and running_diags is not None:
            running_diags.cleanup()
            report(running_diags,
                   date.fromtimestamp(running_diags.starttime).strftime("%Y%m%d-%H%M%S"),
                   cli_args.split)


def run_diags_from_prompt(xnames, cli_args, username, password):
    """Prompts the user for diags to run.

    The user is prompted on stdin until Ctrl-C or Ctrl-D is pressed,
    or the string 'quit' or 'exit' is typed.

    Args:
        - xnames ([str]): xnames to run diags on.
        - cli_args (argparse.Namespace): arguments from the command line.
        - username (str): Redfish username on the switch
        - password (str): Redfish password on the switch

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

        run_diag_set(xnames, diag_command, diag_args, cli_args,
                     username, password)


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

    really_run = args.disruptive \
        or pester("L1 Rosetta diagnostics can degrade or disrupt "
                  "a running system. Really proceed?")
    if not really_run:
        sys.exit(0)

    username, password = sat_redfish.get_username_and_pass()
    if args.interactive:
        run_diags_from_prompt(args.xnames, args, username, password)
    else:
        run_diag_set(args.xnames, args.diag_command, args.diag_args,
                     args, username, password)
