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
from collections import OrderedDict
import logging

from sat.apiclient import APIError, HSMClient, SLSClient
from sat.config import get_config_value
from sat.constants import MISSING_VALUE
from sat.report import Report
from sat.session import SATSession
from sat.xname import XName


# Fields common to all components
COMMON_API_KEYS_TO_HEADERS = OrderedDict([
    ('ID', 'xname'),
    ('State', 'State'),
    ('Flag', 'Flag'),
    ('Enabled', 'Enabled'),
    ('Arch', 'Arch'),
    ('Class', 'Class'),
    ('NetType', 'Net Type'),
])


# A superset of the previous fields, with additional fields specific to Nodes.
NODE_API_KEYS_TO_HEADERS = OrderedDict([
    ('ID', 'xname'),
    ('Aliases', 'Aliases'),
    ('NID', 'NID'),
    ('State', 'State'),
    ('Flag', 'Flag'),
    ('Enabled', 'Enabled'),
    ('Arch', 'Arch'),
    ('Class', 'Class'),
    ('Role', 'Role'),
    ('SubRole', 'Subrole'),
    ('NetType', 'Net Type'),
])


LOGGER = logging.getLogger(__name__)


class UsageError(Exception):
    pass


def make_raw_table(components, heading_mapping):
    """Obtains node status from a list of components.

    Args:
        components (list): A list of dictionaries representing the components
            in the system along with information about their state.
        heading_mapping (dict): A dictionary mapping API keys from CSM services
            to desired table headings.

    Returns:
        A list-of-lists table of strings, each row representing
        the status of a node.
    """
    def get_component_value(component, api_key):
        value = component.get(api_key, MISSING_VALUE)
        if api_key == 'ID' and value != MISSING_VALUE:
            value = XName(value)
        elif all([api_key == 'SubRole', value == MISSING_VALUE, component.get('Role') == 'Compute']):
            # For SubRole, some types of nodes (specifically Compute nodes) are expected to
            # not have a SubRole, so 'None' looks a little more appropriate.
            value = 'None'
        return value

    return [[get_component_value(component, api_key) for api_key in heading_mapping]
            for component in components]


def get_component_aliases(sls_component_dicts):
    """Extract component aliases from an SLS response payload.

    Args:
        - sls_component_dicts ([dict]): a response payload
             from SLS; essentially a list of dictionaries which
             should at the minimum contain keys 'Xname' and
             'ExtraProperties', and 'ExtraProperties' should be a
             dict containing key 'Aliases'

    Returns:
        A dictionary mapping xnames to a list of aliases (i.e. hostnames).
    """
    xname_aliases = {}
    for component in sls_component_dicts:
        if {'Xname', 'ExtraProperties'}.issubset(set(component.keys())):
            if 'Aliases' in component.get('ExtraProperties'):
                xname_aliases[component['Xname']] = component.get('ExtraProperties').get('Aliases')
    return xname_aliases


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

    Raises:
        UsageError: if an argument is invalid
    """
    session = SATSession()
    hsm_client = HSMClient(session)
    if 'all' in args.types:
        args.types = []

    try:
        response = hsm_client.get('State', 'Components', params={'type': args.types})
    except APIError as err:
        LOGGER.error('Request to HSM API failed: %s', err)
        raise SystemExit(1)

    try:
        response_json = response.json()
    except ValueError as err:
        LOGGER.error('Failed to parse JSON from component state response: %s', err)
        raise SystemExit(1)

    try:
        components = response_json['Components']
    except KeyError as err:
        LOGGER.error("Key '%s' not present in API response JSON.", err)
        raise SystemExit(1)

    sls_client = SLSClient(session)
    sls_component_aliases = {}
    try:
        sls_reponse = sls_client.get('hardware')
        sls_component_aliases = get_component_aliases(sls_reponse.json())
    except APIError as err:
        LOGGER.error('Request to SLS API failed: %s', err)
    except ValueError as err:
        LOGGER.error('Failed to parse JSON from SLS: %s', err)

    for component in components:
        if component.get('ID') in sls_component_aliases:
            component['Aliases'] = ', '.join(sls_component_aliases.get(component['ID']))
        else:
            component['Aliases'] = MISSING_VALUE

    multiple_reports = len(args.types) != 1
    report_strings = []

    for component_type, components_by_type in group_dicts_by('Type', components).items():
        title = f'{component_type} Status' if multiple_reports else None
        heading_mapping = (COMMON_API_KEYS_TO_HEADERS, NODE_API_KEYS_TO_HEADERS)[component_type == 'Node']

        component_table_by_type = make_raw_table(components_by_type, heading_mapping)
        report = Report(
            list(heading_mapping.values()), title,
            args.sort_by, args.reverse,
            get_config_value('format.no_headings'),
            get_config_value('format.no_borders'),
            filter_strs=args.filter_strs,
            display_headings=args.fields,
            print_format=args.format
        )

        report.add_rows(component_table_by_type)
        report_strings.append(str(report))

    print('\n\n'.join(report_strings))
