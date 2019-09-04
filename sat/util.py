"""
Contains structures and code that is generally useful across all of SAT.

Copyright 2019, Cray Inc. All Rights Reserved.
"""


def pretty_print_dict(d):
    """Pretty-print a simple dictionary.
    """

    for key in d:
        s = '{}:'.format(key)
        print('{:<20} {:<20}'.format(s, d[key]))


def pretty_print_list(lists):
    """Pretty print a list of lists.
    """

    for l in lists:
        s = ''
        for i in l:
            s += '{:<40} '.format(str(i))

        print(s)
