"""
Entry point for the command-line interface.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import sys

from sat.parser import create_parent_parser
from sat.showrev.main import showrev

SUBCOMMAND_FUNCS = {
    'showrev': showrev
}


def main():
    parser = create_parent_parser()
    args = parser.parse_args()

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
