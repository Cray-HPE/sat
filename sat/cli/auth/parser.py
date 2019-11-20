"""
The parser for the auth subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""


def add_auth_subparser(subparsers):
    """Add the auth subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    auth_parser = subparsers.add_parser('auth', help='Acquire authentication tokens and save for reuse')
