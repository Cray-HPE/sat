"""
Contains structures and code that is generally useful across all of SAT.

Copyright 2019-2020 Cray Inc. All Rights Reserved.
"""
from collections import OrderedDict
from functools import partial
import logging
import math
import os
import os.path
import re

# Logic borrowed from imps to get the most efficient YAML available
try:
    from yaml import CSafeDumper as SafeDumper
except ImportError:
    from yaml import SafeDumper
from yaml.resolver import BaseResolver
from yaml import dump
from prettytable import PrettyTable

from sat.xname import XName

LOGGER = logging.getLogger(__name__)


def pester(message,
           valid_answer=r"^(yes|no)?$",
           human_readable_valid="yes/[no]",
           parse_answer=lambda answer: answer.lower() == "yes"):
    """Pester until given a valid input over stdin.

    Queries user on stdin for some value until the user provides an input
    that matches `valid_answer`.

    By default, this asks for a yes or no answer.

    Args:
        message: a string with a prompt to be printed before asking the user.
        valid_answer: a regex string for which if message matches,
            return some value based on the input.
        human_readable_valid: a human-readable version of valid_answer.
            This is displayed at the prompt. If it is falsy
            (e.g., None or empty string), then the regex is displayed instead.
            If it is "N/A" then only the message part of the prompt is displayed.
        parse_answer: a function taking one string argument which returns a
            value which is to be used in some higher-level conditional.

    Returns:
        For some first valid user input `answer`, return
        parse_answer(answer). If an input error occurs, return None.
    """
    try:
        while True:
            valid = ""
            if human_readable_valid != "N/A":
                valid = "({}) ".format(human_readable_valid or valid_answer)
            answer = input("{} {}".format(message, valid))
            if re.match(valid_answer, answer):
                return parse_answer(answer)
            else:
                print("Input must match '{}'. ".format(valid_answer), end="")
    except EOFError:
        print("\n", end="")
        return


def get_pretty_printed_dict(d, min_len=0):
    """Get the pretty-printed string representation of a dict.

    Args:
        d (dict): The dictionary to pretty-print
        min_len (int): The minimum length of the keys column to enforce.

    Returns:
        A nicely formatted string representation of a dict.
    """
    # Add 1 to length of keys for the colon
    key_field_width = max(max(len(str(k)) for k in d) + 1, min_len)
    return '\n'.join('{:<{width}} {}'.format('{}:'.format(key), value,
                                             width=key_field_width)
                     for key, value in d.items())


def pretty_print_dict(d, min_len=0):
    """Pretty-print a simple dictionary.

    Args:
        See `get_pretty_printed_dict`.
    """
    print(get_pretty_printed_dict(d, min_len))


def get_pretty_table(rows, headings=None, sort_by=None):
    """Gets a PrettyTable instance with the given rows and headings.

    Args:
        rows: List of lists, where each element in the list represents one row
            in the table.
        headings: List of headers for the table. If omitted, no heading row is
            included.
        sort_by: The column index by which the table should be sorted. If
            omitted, no sorting is performed.

    Returns:
        A PrettyTable instance with the given rows and headings.
    """
    pt = PrettyTable()
    pt.border = False
    pt.left_padding_width = 0

    if headings:
        pt.field_names = headings
    else:
        pt.header = False

        # field_names needs to be populated for the alignment to work
        if len(rows[0]) > 0:
            pt.field_names = rows[0]

    if sort_by is not None:
        try:
            pt.sortby = pt.field_names[sort_by]
        except IndexError:
            LOGGER.warning("Invalid sort index (%s) passed to get_pretty_table. "
                           "Valid values are between 0 and %s. Defaulting to no "
                           "sorting.", sort_by, len(pt.field_names))

    # align left
    for x in pt.align:
        pt.align[x] = 'l'

    for l in rows:
        pt.add_row(l)

    return pt


def get_pretty_printed_list(rows, headings=None, sort_by=None):
    """Gets the pretty-printed table representation of a list of lists.

    Args: See `get_pretty_table`.

    Returns:
        A string containing a pretty-printed table.
    """
    return str(get_pretty_table(rows, headings, sort_by))


def pretty_print_list(rows, headings=None, sort_by=None):
    """Pretty prints a list of lists.

    Args: See `get_pretty_table`.
    """
    print(get_pretty_printed_list(rows, headings, sort_by))


def get_rst_header(header, header_level=1, min_len=80):
    """Gets a string for the given header at the given level.

    Args:
        header (str): The text to include in the header.
        header_level (int): The level of the header. Max is 5.
        min_len (int): The minimum length of the header overline and underline.
            The length of the under/overline will be longer than this if the
            `header` text is longer.

    Returns:
        A string representing the header at the given level.

    Raises:
        ValueError: if given an invalid header level.
    """
    header_len = max(len(header), min_len)
    # Dict mapping from level to (header_char, has_overline)
    header_chars = {
        1: ('#', True),
        2: ('=', False),
        3: ('-', False),
        4: ('^', False),
        5: ('"', False)
    }
    try:
        header_char, has_overline = header_chars[header_level]
    except KeyError:
        raise ValueError("Invalid header level ({}). Valid levels: {}".format(
            header_level, map(str(header_chars.keys()))
        ))
    header_chars = header_char * header_len
    if has_overline:
        return '\n'.join([header_chars, header, header_chars]) + '\n'
    else:
        return '\n'.join([header, header_chars]) + '\n'


def format_as_dense_list(items, margin_width=0, spacing=4, max_width=80):
    """Formats items into a densely packed list.

    E.g.:

        words = ['a', 'bark', 'cat', 'dog', 'elephant', 'french',
                 'girl', 'house', 'inn', 'jelly', 'kit', 'lawn']
        print(format_as_dense_list(words, max_width=40))
        a           bark        cat
        dog         elephant    french
        girl        house       inn
        jelly       kit         lawn

    Args:
        items (Iterable): An iterable of items to be formatted as a densely
            packed list.
        margin_width (int): The size of the margins on the left and right.
        spacing (int): The number of space characters to require between items.
        max_width (int): The maximum width of the space the items must fit into.
            If any single item is longer than the max_width minus the margins, a
            warning will be logged, and items will be displayed one per line.

    Returns:
        The string of output items all densely packed together.
    """
    max_item_len = max(len(str(item)) for item in items)
    max_usable_width = max_width - margin_width * 2
    if max_item_len > max_usable_width:
        LOGGER.warning('Cannot format item of length %s into max width %s',
                       max_item_len, max_width)
        items_per_row = 1
    else:
        items_per_row = 1 + math.floor((max_usable_width - max_item_len) /
                                       (max_item_len + spacing))
    spacer = ' ' * spacing
    margin = ' ' * margin_width
    return '\n'.join([margin + spacer.join(['{!s:<{width}}'.format(item, width=max_item_len)
                                            for item in items[i:i + items_per_row]])
                      for i in range(0, len(items), items_per_row)]) + '\n'


# Define standard methods for writing JSON/YAML file formats throughout API
YAML_FORMAT_PARAMS = {'width': 80, 'indent': 4, 'default_flow_style': False}


class SATDumper(SafeDumper):
    """A YAML Dumper that will properly format ordered dicts and xnames."""
    # We don't want to output with aliases
    def ignore_aliases(self, *args, **kwargs):
        super().ignore_aliases(*args, **kwargs)
        return True


def _ordered_dict_representer(dumper, data):
    return dumper.represent_mapping(
        BaseResolver.DEFAULT_MAPPING_TAG, data.items()
    )


def _xname_representer(dumper, xname):
    return dumper.represent_scalar(
        BaseResolver.DEFAULT_SCALAR_TAG, str(xname)
    )


SATDumper.add_representer(OrderedDict, _ordered_dict_representer)
SATDumper.add_representer(XName, _xname_representer)


# A function to dump YAML to be used by all SAT code.
yaml_dump = partial(dump, Dumper=SATDumper, **YAML_FORMAT_PARAMS)


def get_resource_filename(name, section='.'):
    """Get the pathname to a resource file.

    Args:
        name (str): The filename of the resource
        section (str): An optional subdirectory under the resource directory

    Returns:
        Full pathname to the resource file.
    """

    resource_path = os.path.join(os.environ['HOME'], '.config', 'sat', section)

    try:
        os.makedirs(resource_path, exist_ok=True)
    except OSError as err:
        LOGGER.error("Unable to create resource directory '%s': %s", resource_path, err)
        raise SystemExit(1)

    return os.path.join(resource_path, name)


def bytes_to_gib(bytes_val, ndigits=2):
    """Convert the given bytes value to GiB.

    Args:
        bytes_val (int or float): The bytes value to convert.
        ndigits (int): The number of digits to round to.

    Returns:
        The rounded GiB value.
    """
    return round(bytes_val / 2**30, ndigits)
