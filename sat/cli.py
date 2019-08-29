"""
Entry point for the command-line interface.

Copyright 2019, Cray Inc. All Rights Reserved.
"""

import argparse

from sat import util
from sat import showrev


def parse_args():
    """Process command line arguments.

    Returns:
        argparse.ArgumentParser instance that contains options and flags set
        at the command line.
    """

    parser = argparse.ArgumentParser(description='SAT - The Shasta Admin Toolkit')
    subparsers = parser.add_subparsers(metavar='command', dest='command')

    showrev_parser = subparsers.add_parser('showrev', help='Show Shasta revision information')
    showrev_parser.add_argument('--all', help='Print everything.', action='store_true')
    showrev_parser.add_argument(
        '--system',
        help='Print general Shasta version information. This is the default',
        action='store_true')
    showrev_parser.add_argument('--docker', help='Print running docker image versions.', action='store_true')
    showrev_parser.add_argument('--packages', help='Print installed rpm versions.', action='store_true')
    showrev_parser.add_argument('-e', '--substr', help='Print lines that contain the substring', default='')

    return parser.parse_args()


def main():
    args = parse_args()

    if args.command == 'showrev':
        if args.all:
            args.system = True
            args.docker = True
            args.packages = True
        elif not args.system and not args.docker and not args.packages:
            args.system = True

        if args.system:
            sysvers = showrev.get_system_version(args.substr)
            if sysvers is None:
                print('ERROR: Could not print system version information.')
                exit(1)

            util.pretty_print_dict(sysvers)
        if args.docker:
            dockers = showrev.get_dockers(args.substr)
            if dockers is None:
                print('ERROR: Could not retrieve list of running docker containers.')
                exit(1)
            util.pretty_print_list(dockers)

        if args.packages:
            rpms = showrev.get_rpms(args.substr)
            if rpms is None:
                print('ERROR: Could not retrieve list of installed rpms.')
                exit(1)
            util.pretty_print_list(rpms)

    exit(0)


if __name__ == '__main__':
    main()
