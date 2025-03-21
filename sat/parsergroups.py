#
# MIT License
#
# (C) Copyright 2019-2022, 2024 Hewlett Packard Enterprise Development LP
#
# Permission is hereby granted, free of charge, to any person obtaining a
# copy of this software and associated documentation files (the "Software"),
# to deal in the Software without restriction, including without limitation
# the rights to use, copy, modify, merge, publish, distribute, sublicense,
# and/or sell copies of the Software, and to permit persons to whom the
# Software is furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included
# in all copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL
# THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
# OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
# ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
# OTHER DEALINGS IN THE SOFTWARE.
#
"""
Functions to create argument groups which are used by multiple subcommands.
"""

import argparse
import logging
from argparse import ArgumentParser

from sat.constants import EMPTY_VALUE, MISSING_VALUE
# If sat.util starts to import too much sat code, this will slow down tab completion
from sat.util import set_val_by_path

LOGGER = logging.getLogger(__name__)


def create_format_options(sort_by_default='0'):
    """Creates a parser containing options for formatting.

    sort_by_default: allows for the value of --sort_by to be set
        when calling the method. It is set to 0 or the
        first column of data being sorted.

    Returns: an ArgumentParser object configured with options and help
        text for formatting.
    """
    parser = ArgumentParser(add_help=False)

    group = parser.add_argument_group(
        'format options', 'Options to modify output formatting.')

    group.add_argument(
        '--format',
        help="Display information in the given format. Defaults to 'pretty'.",
        choices=['pretty', 'yaml', 'json'],
        default='pretty')

    group.add_argument(
        '--no-borders',
        help='Omit borders from tables.',
        default=None, action='store_true')

    group.add_argument(
        '--no-headings',
        help='Omit headings from tables.',
        default=None, action='store_true')

    group.add_argument(
        '--reverse',
        help='Sort the output in reverse order. Only applies for "pretty".',
        default=False, action='store_true')

    group.add_argument(
        '--sort-by', default=sort_by_default,
        type=lambda v: v.split(','),
        help=('Sort by the selected heading or comma-separated list of '
              'headings. Can also accept a 0-based column index or '
              'comma-separated list of 0-based column indexes.'
              'E.g. "--sort-by product_name,product_version" will sort '
              'results by product name and then by product version. Can accept a column '
              'name or a 0-based index. Enclose the column name in '
              'double quotes if it contains a space.'))

    group.add_argument(
        '--show-empty',
        help='Show values for columns even if every '
             'value is {}.'.format(EMPTY_VALUE),
        default=None,
        action='store_true'
    )

    group.add_argument(
        '--show-missing',
        help='Show values for columns even if every '
             'value is {}'.format(MISSING_VALUE),
        default=None,
        action='store_true'
    )

    group.add_argument(
        '--fields',
        type=lambda v: v.split(','),
        help="Display only the given comma-separated list of fields."
    )

    return parser


def create_filter_options():
    """Creates a parser containing options for filtering.

    Returns: an ArgumentParser object configured with options and help
        text for filtering.
    """
    parser = ArgumentParser(add_help=False)

    group = parser.add_argument_group(
        'filtering options', 'Options to filter output.')

    group.add_argument(
        '--filter', metavar='QUERY', dest='filter_strs',
        action='append', default=[],
        help='Filter rows of the output based on the query provided. '
             'Refer to the man page for this subcommand for more details '
             'regarding filter query syntax.')

    return parser


def create_xname_options():
    """Generate arg options for xname options.

    Returns: an ArgumentParser object configured with options and help
        text for xname options.
    """

    def deduplicate(l_):
        seen = set()
        deduplicated = []
        for item in l_:
            if item not in seen:
                deduplicated.append(item)
                seen.add(item)

        return deduplicated

    class XnameCsvParser(argparse.Action):
        def __init__(self, option_strings, dest, nargs=None, const=None,
                     default=None, type=None, choices=None, required=False,
                     help=None, metavar=None):
            if nargs is not None:
                raise ValueError('XnameCsvParser action does not support '
                                 'nargs set to a non-default value.')
            super().__init__(
                option_strings=option_strings, dest=dest, nargs=nargs,
                const=const, default=default, type=type, choices=choices,
                required=required, help=help, metavar=metavar)

        def __call__(self, parser, namespace, values, option_string=None):
            xnames = []
            if getattr(namespace, self.dest):
                xnames.extend(getattr(namespace, self.dest))

            xnames.extend([x.strip() for x in values.split(',') if x.strip()])
            setattr(namespace, self.dest, deduplicate(xnames))

    class XnameFileReader(argparse.Action):

        def __init__(self, option_strings, dest, nargs=None, const=None,
                     default=None, type=None, choices=None, required=False,
                     help=None, metavar=None):
            if nargs is not None:
                raise ValueError('XnameFileReader action does not support '
                                 'nargs set to a non-default value.')
            super().__init__(
                option_strings=option_strings, dest=dest, nargs=nargs,
                const=const, default=default, type=type, choices=choices,
                required=required, help=help, metavar=metavar)

        def __call__(self, parser, namespace, values, option_string=None):
            xnames = []
            if getattr(namespace, self.dest):
                xnames.extend(getattr(namespace, self.dest))

            try:
                with open(values) as f:
                    xnames.extend([x.strip() for x in f.readlines() if x.strip()])
            except FileNotFoundError:
                raise argparse.ArgumentError(
                    self, 'Xname file {} does not exist.'.format(values))

            except PermissionError:
                raise argparse.ArgumentError(
                    self,
                    'You do not have permission to access {}.'.format(values))

            setattr(namespace, self.dest, deduplicate(xnames))

    parser = ArgumentParser(add_help=False)

    group = parser.add_argument_group(
        'xnames', 'Options for specifying target xnames.')

    # Both of these are accessed via args.xnames.
    group.add_argument(
        '-f', '--xname-file', metavar='PATH',
        dest='xnames', action=XnameFileReader,
        help='Path to a newline-delimited file of xnames. '
             'In order to share the path between the host and container '
             'when sat is run in a container environment, '
             'the path should be either an absolute or relative path of a file '
             'in or below the home or current directory. '
             'Overrides value set in config file.')

    group.add_argument(
        '-x', '--xname', '--xnames', metavar='XNAME',
        dest='xnames', action=XnameCsvParser,
        help='Specify an xname on which to operate. Multiple xnames may be '
             'specified via comma-separated entries or by providing this '
             'option multiple times.')

    return parser


class StoreNestedVariable(argparse.Action):
    """An argparse Action to parse and store nested variables.

    For example, to define a '--vars' option using this action:

        parser.add_argument('--vars', action=StoreNestedVariable)

    If the user calls the program with these arguments:

        --vars host.first=bob --vars host.last=barker

    This will result in the following dict stored in the `vars` destination
    of the argparse.Namespace object:

        {
            'host': {
                'first': 'bob',
                'last': 'barker'
            }
        }
    """

    def __init__(self, option_strings, dest, nargs=None, const=None,
                 default=None, type=None, choices=None, required=False,
                 help=None, metavar=None):
        if nargs is not None:
            raise ValueError('StoreNestedVariable action does not support '
                             'nargs set to a non-default value.')
        super().__init__(
            option_strings=option_strings, dest=dest, nargs=nargs,
            const=const, default=default, type=type, choices=choices,
            required=required, help=help, metavar=metavar)

    def __call__(self, parser, namespace, values, option_string=None):
        # Split into variable name and value
        try:
            name, value = values.split('=', maxsplit=1)
        except ValueError:
            raise argparse.ArgumentError(self, f'Variable string "{values}" must contain "=".')

        # Modify existing vars if any have already been set
        current_vars = getattr(namespace, self.dest)
        # Otherwise, start from an empty dict
        if current_vars is None:
            current_vars = {}
            setattr(namespace, self.dest, current_vars)

        set_val_by_path(current_vars, name, value)
