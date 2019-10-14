"""
The main entry point for the diag subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from collections import defaultdict
from datetime import date
from itertools import chain
import logging
import sys
import textwrap
import time

import inflect

from sat import diag as sat_diag


inf = inflect.engine()
LOGGER = logging.getLogger(__name__)


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


def pester_yes_or_no(message):
    """Queries user on stdin for a yes or no answer until the user
    provides one of those two options. Yes and no are
    case-insensitive.

    Args:
        message: a string with a prompt to be printed before asking
        the user.

    Returns:
        True if 'yes' is typed, and False otherwise.
    """
    try:
        while True:
            answer = input(message + " (yes/[no]) ")
            if answer and answer.lower() not in ("yes", "no"):
                print("Please answer \"yes\" or \"no\". ", end="")
            else:
                return answer.lower() == "yes"
    except KeyboardInterrupt:
        print("\n", end="")
        return False


def report(finished_diags, timestamp, split):
    """Composes a report of the results of completed diagnostics.

    Args:
        finished_diags: a RunningDiagPool object containing the
            diags which have completed.
        split: a bool, which if is True, then the content of stdout
            from each diagnostic will be written to its own file.
            Otherwise, all output is written to stdout.

    Returns:
        a dict mapping result of the diagnostics (based on their
        Severity attribute from Redfish) to a list of xnames with
        that result.
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
                LOGGER.info("Wrote output from %s to %s", diag.xname, output_filename)

            else:
                print(diag_output)

    for diag in finished_diags.not_completed:
        print("{} did not complete diag {}. Status: {}"
              .format(diag.xname, diag.name, diag.taskstate))

    return completion_stats


def do_diag(args):
    """Runs the diag command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the arguments passed to
        the `diag` subcommand.

    Returns:
        None.
    """
    xnames = None
    print_report = True

    try:
        file_xnames = []
        if args.xname_file is not None:
            with open(args.xname_file) as xname_file:
                file_xnames = xnames_from_file(xname_file)

        stdin_xnames = xnames_from_file(sys.stdin)
        args_xnames = args.xnames
        if any((file_xnames, stdin_xnames, args_xnames)):
            xnames = chain(file_xnames, stdin_xnames, args_xnames)

    except IOError as ioerr:
        LOGGER.error("Could not open xnames file '%s'; %s.", args.xname_file, ioerr.strerror)
        sys.exit(1)

    if xnames is None:
        LOGGER.error("No xnames were supplied. Use --xname-file/-f and/or "
                     "--xname/-x to specify xnames.")
        sys.exit(1)

    really_run = args.disruptive \
        or pester_yes_or_no("L1 Rosetta diagnostics can degrade or disrupt "
                            "a running system. Really proceed?")
    if not really_run:
        sys.exit(0)

    try:
        # Initialize all diags
        running_diags = sat_diag.RunningDiagPool(xnames, args.diag_command, args.diag_args,
                                                 args.interval, args.timeout)

        # Continually poll until all diags are complete.
        while not running_diags.complete:
            running_diags.poll_diag_statuses()
            time.sleep(0.1)

    except KeyboardInterrupt:
        LOGGER.info("Received keyboard interrupt. Attempting to cancel diagnostics...")
        for diag in running_diags:
            diag.cancel()
        print_report = False

    finally:
        running_diags.cleanup()

        if print_report:
            # Output a report on what happened
            completion_stats = \
                report(running_diags,
                       date.fromtimestamp(running_diags.starttime).strftime("%Y%m%d-%H%M%S"),
                       args.split)

            for sev, switches in completion_stats.items():
                if sev != 'OK':
                    print("{}: {}"
                          .format(sev, inf.join(switches)))
            # Summary line
            print(inf.join(["{} {} {}"
                            .format(len(xnames), inf.plural('switch', len(xnames)), severity)
                            for severity, xnames in completion_stats.items()]))
