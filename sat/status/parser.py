"""
The parser for the status subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""


def add_status_subparser(subparsers):
    """Add the status subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """

    status_parser = subparsers.add_parser('status', help='Report node status')
    status_parser.add_argument('-r', '--reverse', help='Reverse order of nodes',
                               action='store_true')
    status_parser.add_argument('-s', '--sort-column', default='xname',
                               help='Sort by the selected column. The default is to sort by xname. '
                                    'May be specified by the (case insensitive) column, or by index '
                                    '(starting at 1). The column can be abbreviated if unambiguous.')
