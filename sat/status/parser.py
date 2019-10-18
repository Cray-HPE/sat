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
    status_parser.add_argument('-x', '--xnames',
                               help='Filter list of nodes to show only those with xnames specified '
                                    'with this argument. A single xname may be given, or a comma-'
                                    'separated list (no spaces) of multiple xnames.')
    status_parser.add_argument('-n', '--nids',
                               help='Filter list of nodes to show only those with NIDs specified '
                                    'with this argument. A single NID may be given, or a comma-'
                                    'separated list (no spaces) of multiple NIDs.')
    status_parser.add_argument('--no-headings',
                               help='Remove headings from output.',
                               action='store_true',
                               default=False)
