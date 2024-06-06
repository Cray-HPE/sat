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
Entry point for the status subcommand.
"""
import logging

from csm_api_client.service.gateway import APIError
from csm_api_client.service.hsm import HSMClient

from sat.apiclient.bos import BOSClientCommon
from sat.cli.status.constants import COMPONENT_TYPES
import sat.cli.status.status_module
from sat.cli.status.status_module import StatusModule
from sat.config import get_config_value
from sat.filtering import CustomFilter
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


def get_bos_template_filter_fn(bos_template, session):
    """Get a function which filters nodes based on session template.

    The returned filter function will filter xnames based on whether they are
    listed directly in any of the session template's boot sets, or any node
    groups or roles in those boot sets.

    Args:
        bos_template (str): the name of the BOS session template
        session (SATSession): a SATSession object to connect to the API gateway

    Returns:
        A CustomFilter object which can filter rows based on nodes' belonging
        to a BOS session template boot set.
    """

    skip_filter = False
    hsm_client = HSMClient(session)
    bos_client = BOSClientCommon.get_bos_client(session)

    nodes = set()
    roles = set()

    try:
        session_template = bos_client.get_session_template(bos_template)
        for boot_set in session_template.get('boot_sets', {}).values():
            roles |= set(boot_set.get('node_roles_groups', []))
            nodes |= set(boot_set.get('node_list', []))
            for node_group in boot_set.get('node_groups', []):
                nodes |= set(hsm_client.get_component_xnames(params={
                    'group': node_group
                }))

    except APIError as err:
        LOGGER.warning('Could not get nodes from the given session template: %s', err)
        skip_filter = True

    def filter_fn(row):
        return skip_filter or \
            str(row.get('xname')) in nodes or \
            row.get('Role') in roles

    return CustomFilter(filter_fn, ['xname'])


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

    modules = args.status_module_names
    if modules is not None:
        modules = []
        seen_module_names = set()
        for module_name in args.status_module_names:
            if module_name in seen_module_names:
                continue

            module_cls = getattr(sat.cli.status.status_module, module_name)
            can_use, err_reason = module_cls.can_use()
            if not can_use:
                LOGGER.warning('Cannot retrieve status information from %s: %s',
                               module_cls.source_name, err_reason)
            else:
                modules.append(module_cls)
            seen_module_names.add(module_name)

    # Safeguard against `args.types` being None even though the default value is ["Node"]
    types = COMPONENT_TYPES if args.types is None or 'all' in args.types else args.types
    multiple_reports = len(types) != 1
    report_strings = []

    components = StatusModule.get_populated_rows(
        primary_key='xname',
        session=session,
        component_types=types,
        limit_modules=modules,
        primary_key_type=XName,
    )

    for component_type, components_by_type in group_dicts_by('Type', components).items():
        title = f'{component_type} Status' if multiple_reports else None
        headings = StatusModule.get_all_headings(
            primary_key='xname',
            limit_modules=modules,
            component_type=component_type,
            initial_headings=DEFAULT_HEADING_ORDER
        )
        if not headings:
            LOGGER.warning('None of the selected fields are relevant to component type %s; skipping.',
                           component_type)
            continue

        extra_filter_fns = []
        if args.bos_template:
            if component_type == 'Node':
                extra_filter_fns.append(
                    get_bos_template_filter_fn(args.bos_template, session)
                )
            else:
                LOGGER.warning('%s components cannot be filtered by BOS session template; '
                               'all components will be shown.',
                               component_type)

        report = Report(
            list(headings), title,
            args.sort_by, args.reverse,
            get_config_value('format.no_headings'),
            get_config_value('format.no_borders'),
            filter_strs=args.filter_strs,
            filter_fns=extra_filter_fns,
            display_headings=args.fields,
            print_format=args.format
        )

        report.add_rows(components_by_type)
        report_strings.append(str(report))

    print('\n\n'.join(report_strings))
