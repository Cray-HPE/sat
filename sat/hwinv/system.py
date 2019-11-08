"""
Class to define the entire system hardware inventory.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from collections import defaultdict, OrderedDict
import logging

import inflect

from sat.config import get_config_value
from sat.hwinv.constants import EMPTY_STATUS, STATUS_KEY, TYPE_KEY
from sat.hwinv.chassis import Chassis
from sat.hwinv.compute_module import ComputeModule
from sat.hwinv.hsn_board import HSNBoard
from sat.hwinv.memory_module import MemoryModule
from sat.hwinv.node import Node
from sat.hwinv.node_enclosure import NodeEnclosure
from sat.hwinv.processor import Processor
from sat.hwinv.router_module import RouterModule
from sat.hwinv.summary import ComponentSummary
from sat.report import Report
from sat.util import yaml_dump
from sat.xname import XName

LOGGER = logging.getLogger(__name__)


class System:
    """The full hardware inventory as returned by the HSM API."""

    def __init__(self, complete_raw_data, args):
        """Creates a new object representing the full system's hardware inventory.

        Args:
            complete_raw_data (list): The list of dictionaries returned as JSON
                by the HSM API.
            args: The argparse.Namespace object containing the parsed arguments
                passed to the hwinv subcommand.
        """
        self.complete_raw_data = complete_raw_data
        self.args = args
        self.raw_data_by_type = defaultdict(list)

        self.components_by_type = {
            Node: {},
            Processor: {},
            MemoryModule: {},
            Chassis: {},
            ComputeModule: {},
            NodeEnclosure: {},
            HSNBoard: {},
            RouterModule: {}
        }

        for component in self.complete_raw_data:
            try:
                comp_type = component[TYPE_KEY]
                comp_status = component[STATUS_KEY]
            except KeyError:
                LOGGER.warning("Missing '%s' key in hardware inventory component. "
                               "The following keys are present: {}", TYPE_KEY,
                               ', '.join(component.keys()))
                continue

            if comp_status == EMPTY_STATUS:
                LOGGER.debug("Skipping empty object of type '%s'.", comp_type)
                continue

            self.raw_data_by_type[comp_type].append(component)

        LOGGER.debug("Found components of the following types: %s",
                     ','.join(self.raw_data_by_type.keys()))

    def parse_all(self):
        """Parse and interrelate objects from raw data."""
        self.parse_raw_data()
        self.relate_node_children()
        self.relate_node_parents()

    def parse_raw_data(self):
        """Creates and stores objects from raw data."""
        for object_type, storage_dict in self.components_by_type.items():
            try:
                raw_comp_data = self.raw_data_by_type[object_type.hsm_type]
            except KeyError:
                LOGGER.warning("No components of type '%s' found in HSM data.",
                               object_type.hsm_type)
                continue

            for raw_comp in raw_comp_data:
                comp = object_type(raw_comp)
                storage_dict[comp.xname] = comp

    def relate_node_children(self):
        """Creates links between nodes and their processors and memory modules."""
        node_children_dicts = [
            self.components_by_type[MemoryModule],
            self.components_by_type[Processor]
        ]
        nodes = self.components_by_type[Node]

        for children_by_xname in node_children_dicts:
            for child_xname, child_object in children_by_xname.items():
                node_xname = child_xname.get_direct_parent()
                try:
                    node_object = nodes[node_xname]
                except KeyError:
                    LOGGER.warning("Unable to find parent node xname '%s' of child "
                                   "xname '%s' in hardware inventory.",
                                   node_xname, child_xname)
                    continue

                node_object.add_child_object(child_object)
                child_object.node = node_object

    def relate_node_parents(self):
        """Creates links between nodes and their parent chassis."""
        for node_xname, node_object in self.components_by_type[Node].items():
            chassis_xname = XName.get_xname_from_tokens(node_xname.tokens[:4])
            try:
                chassis_object = self.components_by_type[Chassis][chassis_xname]
            except KeyError:
                LOGGER.debug("No chassis object found for node '%s'.", node_xname)
                continue

            LOGGER.debug("Found chassis object '%s' for node '%s'", chassis_object, node_object)
            node_object.chassis = chassis_object
            chassis_object.add_child_object(node_object)

    @staticmethod
    def get_components_as_dicts(components, fields):
        """Gets the given components as a list of dicts with keys given by fields.

        Args:
            components (Iterable): An iterable of objects of type BaseComponent
                to get as lists for printing in a table format.
            fields (Iterable): An iterable of ComponentField objects to get from
                each component.

        Returns:
            A list of dicts, each representing one of the components and each
            with the canonical names of the fields as keys.
        """
        return [component.get_dict(fields) for component in components]

    @staticmethod
    def get_components_as_lists(components, fields):
        """Get the given attribute as a list of value lists.

        Args:
            components (Iterable): An iterable of objects of type BaseComponent
                to get as lists for printing in a table format.
            fields (Iterable): An iterable of fields to get from each component.

        Returns:
            A list of lists, each representing one of the components and each
            with the values of the fields in the same order as `fields`.
            The first row of the list is the list of field_names.
        """
        return [[field.pretty_name for field in fields]] + [component.get_table_row(fields)
                                                            for component in components]

    def get_all_lists(self):
        """Gets a dict containing all the lists of components as values.

        Returns:
            A dictionary mapping from the list name to the list of components
            of that type. Each list of components will either be a list of
            dictionaries (if format is 'yaml'), or a list of lists (if format
            is 'pretty'). For 'pretty' format, each list of lists will contain
            the headers as the first element.
        """
        inflector = inflect.engine()
        all_lists = OrderedDict()

        for object_type, comp_dict in self.components_by_type.items():
            list_arg_name = 'list_{}'.format(
                inflector.plural(object_type.arg_name))
            fields_arg_name = '{}_fields'.format(object_type.arg_name)

            if not(self.args.list_all or getattr(self.args, list_arg_name)):
                continue

            filters = getattr(self.args, fields_arg_name)
            fields = object_type.get_listable_fields(filters)

            if self.args.format == 'pretty':
                list_key = 'Listing of all {} in the system'.format(
                    object_type.plural_pretty_name()
                )
                all_lists[list_key] = self.get_components_as_lists(
                    comp_dict.values(), fields)
            else:
                list_key = '{}_list'.format(object_type.arg_name)
                all_lists[list_key] = self.get_components_as_dicts(
                    comp_dict.values(), fields)

        return all_lists

    def get_all_summaries(self):
        """Gets a dict containing all the summaries of components as values.

        Returns:
            A list of ComponentSummary objects that provide a summary of each
            type of component by the given fields as requested by `self.args`.
        """
        inflector = inflect.engine()
        all_summaries = []

        for object_type, comp_dict in self.components_by_type.items():
            summarize_arg_name = 'summarize_{}'.format(inflector.plural(object_type.arg_name))
            fields_arg_name = '{}_summary_fields'.format(object_type.arg_name)
            xnames_arg_name = 'show_{}_xnames'.format(object_type.arg_name)

            if not hasattr(self.args, summarize_arg_name):
                # Not a type of object that can be summarized
                continue

            if self.args.summarize_all or getattr(self.args, summarize_arg_name):

                filters = getattr(self.args, fields_arg_name)
                fields = object_type.get_summary_fields(filters)

                include_xnames = getattr(self.args, xnames_arg_name)

                components = comp_dict.values()
                all_summaries.append(ComponentSummary(object_type, fields,
                                                      components, include_xnames))

        return all_summaries

    def get_pretty_output(self, summaries, lists):
        """Gets the complete output in pretty format.

        Args:
            summaries (Iterable): The list of ComponentSummary objects.
            lists (dict): The dict returned by the `get_all_lists` method.

        Returns:
            A pretty string containing the complete output requested by
            the args.
        """
        full_summary_string = ''
        for summary in summaries:
            full_summary_string += str(summary)

        full_list_string = ''

        for component, component_list in lists.items():
            report = Report(component_list[0], component,
                            self.args.sort_by, self.args.reverse,
                            get_config_value('format.no_headings'),
                            get_config_value('format.no_borders'))
            report.add_rows(component_list[1:])

            full_list_string += str(report.get_pretty_table()) + '\n\n'

        return full_summary_string + full_list_string

    @staticmethod
    def get_yaml_output(summaries, lists):
        """Gets the complete output formatted as YAML.

        Args:
            summaries (Iterable): The list of ComponentSummary objects.
            lists (dict): The dict returned by the `get_all_lists` method.

        Returns:
            A string containing the complete output requested by the args in
            YAML format.
        """
        summary_dicts = OrderedDict()

        for summary in summaries:
            summary_dict = summary.as_dict()
            # There should only be one key here, but iterate for flexibility
            for key, val in summary_dict.items():
                summary_dicts[key] = val

        return ''.join(yaml_dump(obj) for obj in [summary_dicts, lists] if obj)

    def get_all_output(self):
        """Get the complete system inventory output according to `self.args`.

        Returns:
            A string of the full system inventory output.
        """
        summaries = self.get_all_summaries()
        lists = self.get_all_lists()

        if self.args.format == 'yaml':
            return self.get_yaml_output(summaries, lists)
        elif self.args.format == 'pretty':
            return self.get_pretty_output(summaries, lists)
