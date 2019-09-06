"""
The main entry point for the showrev subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from sat import util
from sat.showrev import containers, rpm, system


def showrev(args):
    """Run the showrev comand with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """

    if args.all:
        args.system = True
        args.docker = True
        args.packages = True
    elif not args.system and not args.docker and not args.packages:
        args.system = True

    if args.system:
        sysvers = system.get_system_version(args.substr)
        if sysvers is None:
            print('ERROR: Could not print system version information.')
            exit(1)

        util.pretty_print_dict(sysvers)
    if args.docker:
        dockers = containers.get_dockers(args.substr)
        if dockers is None:
            print('ERROR: Could not retrieve list of running docker containers.')
            exit(1)
        util.pretty_print_list(dockers)

    if args.packages:
        rpms = rpm.get_rpms(args.substr)
        if rpms is None:
            print('ERROR: Could not retrieve list of installed rpms.')
            exit(1)
        util.pretty_print_list(rpms)
