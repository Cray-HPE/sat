"""
Entry point for the command-line interface.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import logging
import sys

from sat.parser import create_parent_parser
from sat.cablecheck.main import do_cablecheck
from sat.config import load_config
from sat.logging import bootstrap_logging, configure_logging
from sat.showrev.main import showrev
from sat.status.main import do_status


LOGGER = logging.getLogger(__name__)

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
    bootstrap_logging()

    parser = create_parent_parser()
    args = parser.parse_args()

    load_config()
    configure_logging(args)

    # Print help info if executed without a subcommand
    if args.command is None:
        parser.print_help()
        sys.exit(1)

    # parse_args will catch any invalid values of arg.command
    subcommand = SUBCOMMAND_FUNCS[args.command]

    subcommand(args)

    sys.exit(0)


if __name__ == '__main__':
    main()
