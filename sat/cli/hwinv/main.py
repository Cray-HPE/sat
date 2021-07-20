"""
The main entry point for the hwinv subcommand.

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

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
import re
import sys

import inflect
from parsec import ParseError

from sat.apiclient import APIError, HSMClient
from sat.cli.hwinv.summary import ComponentSummary
from sat.config import get_config_value
from sat.filtering import parse_multiple_query_strings
from sat.report import Report
from sat.session import SATSession
from sat.system.system import System
from sat.util import yaml_dump, json_dump

LOGGER = logging.getLogger(__name__)


def get_arg_regex_matches(args, regex):
    """Gets a list of the matches from args for a given regex.

    Args:
        args (argparse.Namespace): The parsed args
        regex (re.Pattern): The regular expression to match

    Returns:
        An iterable of any re.Match objects from matching against args.
    """
    return filter(lambda x: x is not None, [regex.match(arg) for arg in vars(args)])


def set_default_args(args):
    """Defaults args to '--list-all' and '--summarize-all' if none specified.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None. Modifies `args` given as input.
    """
    # Extract all the arguments that start with the word 'list'
    list_args = {arg: val for arg, val in vars(args).items()
                 if arg.startswith('list')}
    no_list_args = not any(val for val in list_args.values())

    # Extract all the arguments that start with the word 'summarize'
    summarize_args = {arg: val for arg, val in vars(args).items()
                      if arg.startswith('summarize')}
    no_summarize_args = not any(val for val in summarize_args.values())

    # The default behavior of hwinv is to summarize and list all components
    if no_list_args and no_summarize_args:
        LOGGER.debug("No '--summarize' or '--list' options specified. Defaulting to "
                     "'--summarize-all' and '--list-all'.")
        args.list_all = True
        args.summarize_all = True


def report_unused_options(args):
    """Reports any unused options that have no effect.

    This checks for things like '--node-fields' being specified when nodes are
    not being listed by either '--list-nodes' or '--list-all'.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        A list of warning message strings that can be logged.
    """
    inflector = inflect.engine()

    # Maps from the operation to the subordinate args for that operation
    op_to_args = {
        'list': ['{component}_fields'],
        'summarize': ['{component}_summary_fields',
                      'show_{component}_xnames']
    }

    op_to_ignored_args = {
        'list': [],
        'summarize': ['sort_by', 'no_borders', 'no_headings',
                      'show_empty', 'show_missing']
    }

    messages = []
    message_template = (
        "The option '{option}' has no effect because it was specified without "
        "either '--{operation}-all' or '--{operation}-{component}'"
    )

    for operation, sub_args in op_to_args.items():
        option_regex = re.compile(r'{}_(?P<component>.*)'.format(operation))
        all_arg = '{}_all'.format(operation)
        arg_matches = get_arg_regex_matches(args, option_regex)

        for match in arg_matches:
            plural_component = match.group('component')

            # Ignore the <operation>_all argument because it isn't for a
            # specific component.
            is_all_component = plural_component == 'all'
            # If <operation> is being applied to this component type, then the
            # options for this component type will not be unused.
            component_is_relevant = (getattr(args, all_arg) or
                                     getattr(args, match.group(0)))

            if is_all_component or component_is_relevant:
                continue

            singular_component = inflector.singular_noun(plural_component)

            for sub_arg in sub_args:
                sub_arg_name = sub_arg.format(component=singular_component)
                # Check if the subordinate argument for the operation on the
                # component has been specified. We check against None or the
                # empty list because an argument can be specified with a value
                # of False, e.g. '--show-node-xnames off' results in a False
                # value, but it *has* been specified by the user.
                if getattr(args, sub_arg_name) not in (None, []):
                    messages.append(
                        message_template.format(
                            option='--{}'.format(sub_arg_name.replace('_', '-')),
                            operation=operation,
                            component=plural_component.replace('_', '-')
                        )
                    )

    for operation, ignored_args in op_to_ignored_args.items():
        op_requested = any([operation in arg and getattr(args, arg)]
                           for arg in vars(args))
        if op_requested:
            for ignored_arg in ignored_args:
                if getattr(args, ignored_arg):
                    messages.append(f"The option --{ignored_arg.replace('_', '-')} "
                                    f"is ignored for {operation} operations.")

    return messages


def get_display_fields(args, object_type, operation):
    """Gets a list of fields which should be displayed in the output.

    Determining which fields to display is done as follows. If present, the
    value of the --*-fields or --*-summary-fields option corresponding to a
    given list or summary is always used, where appropriate. If --fields is
    present, its value is used if the --*-fields or --*-summary-fields option
    is not present. If neither is present, all fields are used.

    Args:
        args (argparse.Namespace): the commandline arguments parsed by
            argparse
        object_type (BaseComponent): the component being listed or summarized
        operation (str): either 'list' or 'summarize'

    Returns:
        A list of ComponentField objects corresponding to the fields to be
        present in the displayed report.
    """

    inflector = inflect.engine()

    if operation != 'list':
        specific_fields_arg_name = f'{object_type.arg_name}_{operation}_fields'
        field_getter = getattr(object_type, f'get_{operation}_fields')
    else:
        specific_fields_arg_name = f'{object_type.arg_name}_fields'
        field_getter = object_type.get_listable_fields

    specific_fields = getattr(args, specific_fields_arg_name)

    if specific_fields:
        if args.fields:
            arg_name = f"--{specific_fields_arg_name.replace('_', '-')}"
            LOGGER.warning("Using the %s %s specified by "
                           "%s in '%s' %s.",
                           inflector.join([f"'{field}'" for field in specific_fields]),
                           inflector.plural_noun('field', len(specific_fields)),
                           arg_name,
                           object_type.pretty_name,
                           operation)
        return field_getter(specific_fields)
    else:
        return field_getter(args.fields)

def get_all_lists(system, args):
    """Gets a list containing Reports listing each type of component.

    Args:
        system (sat.system.system.System): The representation of the full
            system according to HSM.
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        A list of Reports of all components of each type.
    """
    inflector = inflect.engine()
    all_lists = []

    for object_type, comp_dict in system.components_by_type.items():
        list_arg_name = 'list_{}'.format(inflector.plural(object_type.arg_name))

        # Continue if list of this component type was not requested
        if not (args.list_all or getattr(args, list_arg_name)):
            continue

        display_fields = get_display_fields(args, object_type, 'list')
        all_fields = object_type.get_listable_fields()
        if set(display_fields) != set(all_fields):
            display_fields = [field.pretty_name for field in display_fields]
        else:
            display_fields = None

        field_key_attr = 'pretty_name' if args.format == 'pretty' else 'canonical_name'
        headings = [getattr(field, field_key_attr) for field in all_fields]
        list_title = object_type.get_list_title(args.format)

        component_dicts = [component.get_dict(all_fields, field_key_attr)
                           for component in comp_dict.values()]

        component_report = Report(
            headings=headings, title=list_title,
            sort_by=args.sort_by, reverse=args.reverse,
            no_headings=get_config_value('format.no_headings'),
            no_borders=get_config_value('format.no_borders'),
            filter_strs=args.filter_strs,
            show_empty=args.show_empty,
            show_missing=args.show_missing,
            display_headings=args.fields,
            print_format=args.format
        )
        component_report.add_rows(component_dicts)

        all_lists.append(component_report)

    return all_lists


def get_all_summaries(system, args):
    """Gets a list of all the summaries of components.

    Args:
        system (sat.system.system.System): The representation of the full
            system according to HSM.
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        A list of ComponentSummary objects that provide a summary of each
        type of component by the given fields as requested by `self.args`.
    """
    inflector = inflect.engine()
    all_summaries = []

    for object_type, comp_dict in system.components_by_type.items():
        summarize_arg_name = 'summarize_{}'.format(inflector.plural(object_type.arg_name))
        xnames_arg_name = 'show_{}_xnames'.format(object_type.arg_name)

        if not hasattr(args, summarize_arg_name):
            # Not a type of object that can be summarized
            continue

        if args.summarize_all or getattr(args, summarize_arg_name):
            display_fields = get_display_fields(args, object_type, 'summary')
            all_fields = object_type.get_summary_fields()
            try:
                filter_fn = (parse_multiple_query_strings(
                    args.filter_strs,
                    [field.canonical_name for field in all_fields]
                ) if args.filter_strs else None)
            except ParseError as err:
                LOGGER.error("The given filter has invalid syntax; returning no output. (%s)", err)
                sys.exit(1)

            include_xnames = getattr(args, xnames_arg_name)

            components = comp_dict.values()
            all_summaries.append(ComponentSummary(object_type, all_fields,
                                                  components, include_xnames,
                                                  filter_fn=filter_fn,
                                                  display_fields=display_fields,
                                                  reverse=args.reverse))

    return all_summaries


def get_pretty_output(summaries, lists):
    """Gets the complete output in pretty format.

    Args:
        summaries (Iterable): The `ComponentSummary` objects returned by
            `get_all_summaries`.
        lists (Iterable): The `Report` objects returned by `get_all_lists`.

    Returns:
        A pretty string containing the complete output requested by
        the args.
    """
    full_summary_string = ''
    for summary in summaries:
        full_summary_string += str(summary)

    full_list_string = ''
    for component_list in lists:
        full_list_string += str(component_list) + '\n\n'

    return full_summary_string + full_list_string


def get_formatted_output(summaries, lists, dump_format):
    """Gets the complete output formatted as JSON or YAML.

    Args:
        summaries (Iterable): The `ComponentSummary` objects returned by
            `get_all_summaries`.
        lists (Iterable): The `Report` objects returned by `get_all_lists`.
        dump_format (string): The format to output the report in, expected
        to be 'json' or 'yaml'

    Returns:
        A string containing the complete output requested by the args in
        JSON or YAML format.
    """
    # The way we are constructing a top-level dictionary by joining together
    # YAML representations of dictionaries is not optimal, but it works for now.
    # TODO: This creates valid YAML, but not JSON. See CRAYSAT-1046.
    summary_str = ''
    summary_dicts = OrderedDict()

    for summary in summaries:
        summary_dict = summary.as_dict()
        # There should only be one key here, but iterate for flexibility
        for key, val in summary_dict.items():
            summary_dicts[key] = val

    if dump_format == 'yaml':
        dump_fn = yaml_dump
    elif dump_format == 'json':
        dump_fn = json_dump
    else:
        raise ValueError('Unexpected dump format received.')

    summary_str += dump_fn(summary_dicts) if summary_dicts else ''

    return summary_str + ''.join(str(report) for report in lists)


def get_all_output(system, args):
    """Get the complete system inventory output according to `self.args`.

    Returns:
        A string of the full system inventory output.
    """
    summaries = get_all_summaries(system, args)
    lists = get_all_lists(system, args)

    if args.format == 'pretty':
        return get_pretty_output(summaries, lists)
    else:
        return get_formatted_output(summaries, lists, args.format)


def do_hwinv(args):
    """Executes the hwinv command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    LOGGER.debug('do_hwinv received the following args: %s', args)
    set_default_args(args)
    warning_messages = report_unused_options(args)

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
    print(get_all_output(full_system, args))

    for message in warning_messages:
        LOGGER.warning(message)
