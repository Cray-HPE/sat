"""
The main entry point for the diag subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from collections import defaultdict
from datetime import date
import getpass
import logging
import re
import sys
import time

import inflect

from sat.cli.diag import redfish
from sat.config import get_config_value


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


def xnames_from_file(fstream):
    """Gets a list of xnames from a file-like object.

    If fstream can be read from, (i.e. non-iteractive) then generate a
    list of strings from that file, one xname per line. If fstream is
    interactive, e.g. stdin is a tty, then return an empty list.

    Args:
        fstream: a file object (e.g. a text file or stdin)
            which contains a list of xnames.

    Returns:
        a list of xnames from the file.
    """
    return [xname.strip() for xname in fstream.readlines() if xname.strip()] \
        if not fstream.isatty() else []


def pester(message, valid_answer=r"^(yes|no)?$", human_readable_valid="yes/[no]",
           parse_answer=lambda answer: answer.lower() == "yes"):
    """Queries user on stdin for some value until the user
    provides an input that matches `valid_answer`.

    By default, this asks for a yes or no answer.

    Args:
        message: a string with a prompt to be printed before asking
            the user.
        valid_answer: a regex string for which if message matches,
            return some value based on the input.
        human_readable_valid: a human-readable version of valid_answer.
            This is displayed at the prompt. If it is falsy (e.g., None or empty
            string), then the regex is displayed instead.
        parse_answer: a function taking one string argument which returns a
            value which is to be used in some higher-level conditional.

    Returns:
        For some first valid user input `answer`, return parse_answer(answer). If
        an input error occurs, return None.
    """
    try:
        while True:
            answer = input("{} ({}) ".format(message, human_readable_valid or valid_answer))
            if re.match(valid_answer, answer):
                return parse_answer(answer)
            else:
                print("Input must match '{}'. ".format(valid_answer), end="")
    except (KeyboardInterrupt, EOFError):
        print("\n", end="")
        return


def get_username_and_pass():
    """Gets the username and password for a user.

    This will lookup the username and password from the config
    file. If either is not supplied, then the user will be queried
    interactively for both.

    Returns: a pair (2-tuple) containing the username and password
        for use with the Redfish API.
    """
    username, password = (get_config_value('redfish.username'),
                          get_config_value('redfish.password'))
    if not (username and password):
        username = pester("Username: ", "^.*$",
                          human_readable_valid="Redfish",
                          parse_answer=(lambda x: x))
        password = getpass.getpass()

    return username, password


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
        running_diags = redfish.RunningDiagPool(xnames, diag_command, diag_args,
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

    try:
        file_xnames = []
        if args.xname_file is not None:
            with open(args.xname_file) as xname_file:
                file_xnames = xnames_from_file(xname_file)

        stdin_xnames = xnames_from_file(sys.stdin)
        xnames = file_xnames + stdin_xnames + args.xnames

    except IOError as ioerr:
        LOGGER.error("Could not open xnames file '%s'; %s.", args.xname_file, ioerr.strerror)
        sys.exit(1)

    if not xnames:
        LOGGER.error("No xnames were supplied. Use --xname-file/-f and/or "
                     "--xname/-x to specify xnames.")
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

    username, password = get_username_and_pass()
    if args.interactive:
        run_diags_from_prompt(xnames, args, username, password)
    else:
        run_diag_set(xnames, args.diag_command, args.diag_args,
                     args, username, password)
