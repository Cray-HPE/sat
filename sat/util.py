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

    pt = PrettyTable()
    pt.border = False

    if headings:
        pt.field_names = headings
    else:
        pt.header = False

        # field_names needs to be populated for the alignment to work
        if len(lists[0]) > 0:
            pt.field_names = lists[0]

    # align left
    for x in pt.align:
        pt.align[x] = 'l'

    for l in lists:
        pt.add_row(l)

    print(pt)
