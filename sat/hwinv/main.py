"""
The main entry point for the hwinv subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging
import re
import sys

import inflect

from sat.apiclient import APIError, HSMClient
from sat.hwinv.system import System
from sat.session import SATSession

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

    return messages


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

    full_system = System(response_json, args)
    full_system.parse_all()
    print(full_system.get_all_output())

    for message in warning_messages:
        LOGGER.warning(message)
