"""
The parser for the setrev subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""


def add_setrev_subparser(subparsers):
    """Add the setrev subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    setrev_parser = subparsers.add_parser(
        'setrev',
        help='Set site-specific information.')

    setrev_parser.add_argument(
        '--sitefile',
        default='',
        help='Specify a custom site-file to populate.')
