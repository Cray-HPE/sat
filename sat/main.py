"""
Entry point for the command-line interface.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import importlib
import logging
import sys

import argcomplete

from sat.config import load_config
from sat.logging import bootstrap_logging, configure_logging
from sat.parser import create_parent_parser

LOGGER = logging.getLogger(__name__)


def main():
    """SAT Main.

    Returns:
        None. Calls sys.exit().
    """
    try:
        parser = create_parent_parser()
        argcomplete.autocomplete(parser)
        args = parser.parse_args()

        bootstrap_logging()

        load_config(args)
        configure_logging()

        # Dynamically importing here affords the following
        # advantages:
        # 1. If Ctrl-C is pressed while imports are occuring, we
        #    can handle it gracefully.
        # 2. We can import only the subcommand code relevant to the
        #    desired subcommand, which gives a small performance benefit,
        #    about a 100ms speedup for the import step.
        subcommand_module = importlib.import_module(
            'sat.cli.{}.main'.format(args.command))

        try:
            subcommand = getattr(subcommand_module, 'do_{}'.format(args.command))
        except AttributeError:
            # Subcommand main-routines need to follow a naming convention
            # of do_<subcommand>.
            LOGGER.error("Couldn't find function 'sat.%s.main.do_%s'. "
                         "Is it named correctly?",
                         args.command, args.command)
            sys.exit(1)

        subcommand(args)

    except KeyboardInterrupt:
        LOGGER.info("Received keyboard interrupt; quitting.")

    sys.exit(0)


if __name__ == '__main__':
    main()
