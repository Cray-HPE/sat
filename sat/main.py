"""
Entry point for the command-line interface.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import logging
import sys

from sat.parser import create_parent_parser
from sat.cablecheck.main import do_cablecheck
from sat.showrev.main import showrev
from sat.status.main import do_status


SUBCOMMAND_FUNCS = {
    'cablecheck': do_cablecheck,
    'showrev': showrev,
    'status':  do_status,
}


def main():
    """SAT Main.

    Returns:
        None. Calls sys.exit().
    """
    parser = create_parent_parser()
    args = parser.parse_args()

    # Print help info if executed without a subcommand
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # parse_args will catch any invalid values of arg.command
    subcommand = SUBCOMMAND_FUNCS[args.command]

    # Initialize logging for sat
    logging.basicConfig(
        filename=args.logfile,
        level=args.loglevel.upper(),
        format='%(levelname)s %(asctime)s %(message)s')

    logformatter = logging.Formatter('%(levelname)s %(asctime)s %(message)s')
    rootlogger = logging.getLogger()

    consolehandler = logging.StreamHandler(sys.stderr)
    consolehandler.setFormatter(logformatter)
    rootlogger.addHandler(consolehandler)

    subcommand(args)

    sys.exit(0)


if __name__ == '__main__':
    main()
