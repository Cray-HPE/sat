"""
The parser for the hwinv subcommand.
Copyright 2019 Cray Inc. All Rights Reserved.
"""
from argparse import ArgumentTypeError

import inflect


def on_off_str2bool(value):
    """Converts 'on' or 'off' to a boolean.

    Args:
        value (str): The value, which should be one of 'on' or 'off'.
            Also accepts any variation on that case, e.g. 'On' or 'OFF'.

    Returns:
        The converted bool value.

    Raises:
        argparse.ArgumentTypeError: if the value is invalid.
    """
    if value.lower() not in ('on', 'off'):
        raise ArgumentTypeError("Expected 'on' or 'off'.")
    else:
        return value.lower() == 'on'


def _add_summarize_option(option_group, singular_component, default_xnames):
    """Adds a '--summarize' option for the given component.

    Args:
        option_group (argparse._ArgumentGroup): The object returned by the
            add_argument_group method of the argparse.ArgumentParser.
        singular_component (str): The name of the component in singular form.
        default_xnames (str): The default value to use for the option of the
            form --show-<component>-xnames. This controls whether xnames should
            be displayed by default when summarizing this component.

    Returns:
        None. Adds to the given `option_group`.
    """
    engine = inflect.engine()
    plural_component = engine.plural(singular_component)

    option_group.add_argument(
        '--summarize-{}'.format(plural_component), action='store_true',
        help='Summarize the {} in the system by values of given fields.'.format(plural_component)
    )

    effect_disclaimer = ("This only has an effect if {0} are being summarized by the "
                         "'--summarize-{0}' or '--summarize-all' options.").format(plural_component)

    option_group.add_argument(
        '--{}-summary-fields'.format(singular_component),
        type=lambda v: v.split(','),
        help='Summarize the {} by the given comma-separated list of fields. '
             'Omit this option to summarize by all fields. {}'.format(plural_component,
                                                                      effect_disclaimer),
        default=[]
    )


    option_group.add_argument(
        '--show-{}-xnames'.format(singular_component), nargs='?', const='on',
        default=default_xnames, type=on_off_str2bool,
        help="Specify 'on' or 'off' to show or hide all {0} xnames in {0} summaries. {1} "
             "Defaults to '{2}'.".format(singular_component, effect_disclaimer, default_xnames)
    )


def _add_list_option(option_group, singular_component):
    """Adds a '--list' option for the given component

    Args:
        option_group (argparse._ArgumentGroup) : The object returned by the
            add_argument_group method of the argparse.ArgumentParser.
        singular_component (str): The name of the component in singular form.

    Returns:
        None. Adds to the given `option_group`.
    """
    engine = inflect.engine()
    plural_component = engine.plural(singular_component)

    option_group.add_argument(
        '--list-{}'.format(plural_component), action='store_true',
        help='List all the {} in the system.'.format(plural_component)
    )
    option_group.add_argument(
        '--{}-fields'.format(singular_component),
        type=lambda v: v.split(','),
        help="Display the given comma-separated list of fields for each {0}. Omit this "
             "option to display all fields. This option only has an effect if {1} are being "
             "listed by the '--list-all' or '--list-{1}' option.".format(singular_component,
                                                                         plural_component),
        default=[]
    )


def add_hwinv_subparser(subparsers):
    """Add the hwinv subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    hwinv_parser = subparsers.add_parser('hwinv', help='Show hardware inventory')

    hwinv_parser.add_argument(
        '--format', '-f',
        help="Display information in the given format. Defaults to 'pretty'.",
        choices=['pretty', 'yaml'],
        default='pretty'
    )

    summarize_group = hwinv_parser.add_argument_group(
        'Summarize Options',
        'Options to summarize components by various fields.'
    )
    summarize_group.add_argument(
        '--summarize-all', action='store_true',
        help='Summarize all the components in the system. This is equivalent to specifying all '
             'the other --summarize-<component> options at once.'
    )

    # A list of tuples of the form (component_name, default_xname) where default_xname
    # is 'on' if xnames should be listed by default and 'off' if they should be suppressed.
    summary_components = [('node', 'on'), ('proc', 'off'), ('mem', 'off')]
    for component, default_xnames in summary_components:
        _add_summarize_option(summarize_group, component, default_xnames)

    list_group = hwinv_parser.add_argument_group(
        'List Options',
        'Options to list components of certain types.'
    )
    list_group.add_argument(
        '--list-all', action='store_true',
        help='List all the components in the system. This is equivalent to specifying all the '
             'other --list-<component> options at once'
    )

    list_component_names = ['node', 'chassis', 'hsn-board', 'compute-module',
                            'router-module', 'node-enclosure', 'proc', 'mem']
    for component in list_component_names:
        _add_list_option(list_group, component)
