"""
The main entry point for the hwmatch subcommand.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
from collections import Counter, defaultdict
import logging
import sys

from sat.apiclient import APIError, HSMClient
from sat.config import get_config_value
from sat.session import SATSession
from sat.system.field import ComponentField
from sat.system.memory_module import MemoryModule
from sat.system.node import Node
from sat.system.processor import Processor
from sat.report import Report
from sat.system.system import System

LOGGER = logging.getLogger(__name__)

PROC_MATCH_FIELDS = [
    ComponentField('Model'),
    ComponentField('Total Cores'),
    ComponentField('Max Speed (MHz)')
]

MEM_MATCH_FIELDS = [
    ComponentField('Memory Type'),
    ComponentField('Device Type'),
    ComponentField('Capacity (MiB)')
]

NODE_MEM_MATCH_FIELDS = [
    ComponentField('Manufacturer')
]

NODE_MATCH_FIELDS = [
    ComponentField('Memory Module Count')
]

MATCH_FIELDS_BY_LEVEL = {
    'slot': {
        Node: NODE_MATCH_FIELDS,
        MemoryModule: MEM_MATCH_FIELDS,
        Processor: PROC_MATCH_FIELDS
    },
    'card': {
        Node: NODE_MATCH_FIELDS,
        MemoryModule: MEM_MATCH_FIELDS,
        Processor: PROC_MATCH_FIELDS
    },
    'node': {
        Node: NODE_MATCH_FIELDS,
        MemoryModule: MEM_MATCH_FIELDS + NODE_MEM_MATCH_FIELDS,
        Processor: PROC_MATCH_FIELDS
    },
}

XNAME_PROPERTY_BY_LEVEL = {
    'card': 'card_xname',
    'node': 'xname',
    'slot': 'slot_xname'
}

TABLE_HEADINGS = ('xname', 'Level', 'Category', 'Field', 'Values')


def do_hwmatch(args):
    """Executes the hwmatch command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    LOGGER.debug('do_hwmatch received the following args: %s', args)

    # Obtain hardware inventory.
    client = HSMClient(SATSession())
    try:
        response = client.get('Inventory', 'Hardware')
    except APIError as err:
        LOGGER.error('Failed to get hardware inventory from HSM: %s', err)
        sys.exit(1)
    try:
        response_json = response.json()
    except ValueError as err:
        LOGGER.error('Failed to parse JSON from hardware inventory response: %s', err)
        sys.exit(1)
    full_system = System(response_json)
    full_system.parse_all()

    records_by_level = {}

    # A default list does not work well via argparse, so:
    if not args.levels:
        args.levels = ['card']

    for level, type_to_fields in MATCH_FIELDS_BY_LEVEL.items():
        if level not in args.levels:
            continue

        records_by_level[level] = {
            child_type: {field: defaultdict(Counter)
                         for field in fields}
            for child_type, fields in type_to_fields.items()
        }

        for child_type, fields in type_to_fields.items():
            for field in fields:
                for node in full_system.components_by_type[Node].values():
                    if child_type is Node:
                        field_vals = [getattr(node, field.property_name)]
                    else:
                        field_vals = node.get_child_vals(child_type, field.property_name)
                    xname = getattr(node, XNAME_PROPERTY_BY_LEVEL[level])
                    counter = records_by_level[level][child_type][field][xname]
                    counter.update(field_vals)

    rows = []
    for level, type_to_fields in records_by_level.items():
        for child_type, field_to_vals in type_to_fields.items():
            for field, xname_to_vals in field_to_vals.items():
                for xname, val_counts in xname_to_vals.items():
                    if len(val_counts) > 1 or args.show_matches:
                        val_str = ', '.join('{} ({})'.format(val, count)
                                            for val, count in val_counts.items())
                        if val_str == '':
                            val_str = 'EMPTY'
                        rows.append(dict(zip(TABLE_HEADINGS,
                                             [xname, level, child_type.pretty_name,
                                              field.pretty_name, val_str])))

    report = Report(
        TABLE_HEADINGS, sort_by=args.sort_by, reverse=args.reverse,
        no_headings=get_config_value('format.no_headings'),
        no_borders=get_config_value('format.no_borders'),
        filter_strs=args.filter_strs, display_headings=args.fields
    )
    report.add_rows(rows)
    if not rows and args.format == 'pretty':
        print('No mismatches found')
    else:
        if args.format == 'yaml':
            print(report.get_yaml())
        elif args.format == 'json':
            print(report.get_json())
        else:
            print(report)
