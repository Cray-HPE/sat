"""
Contains structures and code that is generally useful across all of SAT.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

from prettytable import PrettyTable


def pretty_print_dict(d):
    """Pretty-print a simple dictionary.
    """

    for key in d:
        s = '{}:'.format(key)
        print('{:<20} {:<20}'.format(s, d[key]))


def pretty_print_list(lists, headings=None):
    """Pretty print a list of lists.

    Args:
        lists: List of lists.
        headings: List of headers. A PrettyTable will be used for output if
            this argument is not None.
    """

    if headings:
        pt = PrettyTable()

        pt.field_names = headings
        for l in lists:
            pt.add_row(l)

        print(pt)
    else:
        for l in lists:
            s = ''
            for i in l:
                s += '{:<40} '.format(str(i))

            print(s)
