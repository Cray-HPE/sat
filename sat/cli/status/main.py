"""
Entry point for the status subcommand.

(C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
import logging

from sat.cli.status.constants import COMPONENT_TYPES
from sat.cli.status.status_module import StatusModule
from sat.config import get_config_value
from sat.report import Report
from sat.session import SATSession
from sat.xname import XName


LOGGER = logging.getLogger(__name__)

# When possible, put Aliases right after xnames for ease of reading
DEFAULT_HEADING_ORDER = ['xname', 'Aliases']


class UsageError(Exception):
    pass


def group_dicts_by(key, dicts):
    """Group dicts by a particular key.

    To illustrate, consider the following group of dicts:

    ```
    dicts = [
        {
            "name": "Pepsi",
            "type": "cola"
        },
        {
            "name": "Coca-Cola",
            "type": "cola"
        },
        {
            "name": "Sprite",
            "type": "lemon-lime"
        }
    ]
    ```

    Then if grouped by `"type"`, the following is the result:

    ```
    group_dicts_by("type", dicts) == {
        "cola": [
            {
                "name": "Pepsi",
                "type": "cola"
            },
            {
                "name": "Coca-Cola",
                "type": "cola"
            }
        ],
        "lemon-lime": [
            {
                "name": "Sprite",
                "type": "lemon-lime"
            }
        ]
    }
    ```

    Args:
        key (str): The key in the dictionaries passed in `dicts` to group by.
        dicts ([dict]): A list of dicts to be grouped

    Raises:
        ValueError: if `key` is not present in all dictionaries in
            `dicts`

    Returns:
        dict: a mapping from each unique value of the key from `dicts` to a list of
        dicts with that value
    """
    try:
        unique_attr_vals = set(d[key] for d in dicts)
    except KeyError as err:
        raise ValueError(f'The key "{key}" is not present in every '
                         f'dictionary in the input') from err

    grouped = {}
    for unique_attr_val in unique_attr_vals:
        grouped[unique_attr_val] = [d for d in dicts if d[key] == unique_attr_val]
    return grouped


def do_status(args):
    """Displays node status.

    Results are sorted by the "sort_column" member of args, which defaults
    to xname. xnames are tokenized for the purposes of sorting, so that their
    numeric elements are sorted by their value, not lexicographically. Sort
    order is reversed if the "reverse" member of args is True.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    session = SATSession()

    types = COMPONENT_TYPES if 'all' in args.types else args.types
    multiple_reports = len(types) != 1
    report_strings = []

    components = StatusModule.get_populated_rows(
        primary_key='xname',
        primary_key_type=XName,
        session=session,
        component_types=types,
    )

    for component_type, components_by_type in group_dicts_by('Type', components).items():
        title = f'{component_type} Status' if multiple_reports else None
        headings = StatusModule.get_all_headings(
            primary_key='xname',
            component_type=component_type,
            initial_headings=DEFAULT_HEADING_ORDER
        )

        report = Report(
            list(headings), title,
            args.sort_by, args.reverse,
            get_config_value('format.no_headings'),
            get_config_value('format.no_borders'),
            filter_strs=args.filter_strs,
            display_headings=args.fields,
            print_format=args.format
        )

        report.add_rows(components_by_type)
        report_strings.append(str(report))

    print('\n\n'.join(report_strings))
