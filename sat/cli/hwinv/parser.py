"""
The parser for the hwinv subcommand.
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
from argparse import ArgumentTypeError

import inflect

import sat.parsergroups


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
        help='Summarize the {0} by the given comma-separated list of fields. Enclose '
             'a field in double quotes for exact matching. The quotes may need to be '
             'escaped. Omit this option to summarize by all fields. {1}'.format(
            plural_component, effect_disclaimer),
        default=[]
    )

    # Note that defaults are actually specified in BaseComponent subclasses, so
    # we can see whether this option was actually specified by the user. It will
    # be None if not specified.
    option_group.add_argument(
        '--show-{}-xnames'.format(singular_component), nargs='?',
        const='on', type=on_off_str2bool,
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
        help="Display the given comma-separated list of fields for each {0}. Enclose "
             "a field in double quotes for exact matching. The quotes may need to be "
             "escaped. Omit this option to display all fields. This option only has "
             "an effect if {1} are being listed by the '--list-all' or '--list-{1}' "
             "option.".format(singular_component, plural_component),
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
    format_options = sat.parsergroups.create_format_options()
    filter_options = sat.parsergroups.create_filter_options()

    hwinv_parser = subparsers.add_parser(
        'hwinv', help='Show hardware inventory.',
        description='Show hardware inventory as lists and/or summaries.',
        parents=[format_options, filter_options])

    summarize_group = hwinv_parser.add_argument_group(
        'Summarize Options',
        'Options to summarize components by various fields.'
    )
    summarize_group.add_argument(
        '--summarize-all', action='store_true',
        help='Summarize all the components in the system. This is equivalent to specifying all '
             'the other --summarize-<component> options at once.'
    )

    # Note that summary_components and list_component_names are redundant with
    # info in the classes, but we don't import them here to reduce the time
    # required to create the parser to increase responsiveness of autocomplete
    # and reduce startup time when running a subcommand other than `hwinv`.

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
                            'router-module', 'node-enclosure', 'node-enclosure-power-supply',
                            'proc', 'node-accel','mem', 'drive', 'cmm-rectifier']
    for component in list_component_names:
        _add_list_option(list_group, component)
