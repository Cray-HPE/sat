"""
Entry point for the command-line interface.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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

import importlib
import logging
import sys

import argcomplete

from sat.config import generate_default_config, load_config
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

        # Automatically create config file if it does not exist, except
        # in `sat init` where the subcommand will create it.  With
        # `sat init`, don't bother loading configuration or configuring
        # logging either.
        if args.command != 'init':
            generate_default_config(username=args.username)
            load_config(args)
            configure_logging()

        # Dynamically importing here affords the following
        # advantages:
        # 1. If Ctrl-C is pressed while imports are occurring, we
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
        LOGGER.info("Received keyboard interrupt; quitting.", exc_info=True)

    sys.exit(0)


if __name__ == '__main__':
    main()
