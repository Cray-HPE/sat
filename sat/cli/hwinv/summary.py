"""
Classes to define summaries of components by various fields.

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
from collections import defaultdict
import logging

from sat.util import format_as_dense_list, get_rst_header, get_pretty_printed_list

LOGGER = logging.getLogger(__name__)


class ComponentSummary:

    def __init__(self, comp_type, fields, components, include_xnames,
                 filter_fn=None, display_fields=None, reverse=False):
        """Creates a new ComponentSummary object.

        This represents a summary of one component type by multiple fields.

        Args:
            comp_type: The type of component being summarized, subclass of
                BaseComponent.
            fields (Iterable): An Iterable of ComponentField objects to
                use to summarize the components.
            components (Iterable): An Iterable of BaseComponent objects to
                summarize.
            include_xnames (bool or NoneType): Whether to include xnames in
                summaries or just counts.
            filter_fn (dict -> bool): a FilterFunction which is called on
                each component in the summary to check if it should be
                included in the summary.
            display_fields ([str]): the fields which should be summarized
                in the output.
            reverse (bool): If True, then the individual summaries will be
                printed in reverse order (descending.)
        """
        self.comp_type = comp_type
        self.fields = display_fields or fields
        self.include_xnames = (include_xnames if include_xnames is not None
                               else comp_type.default_show_xnames)

        if filter_fn:
            try:
                self.components = [component for component in components
                                   if filter_fn(component.get_dict(fields, 'canonical_name'))]

            except KeyError as err:
                LOGGER.warning("Filter key %s does not exist in %s summary. All components will be summarized.",
                               err, self.comp_type.pretty_name)
                self.components = components
        else:
            self.components = components

        self.field_summaries = []
        self.summary_dict = {}

        for field in self.fields:
            field_summary = FieldSummary(self.comp_type, field,
                                         self.components, self.include_xnames,
                                         reverse=reverse)
            self.field_summaries.append(field_summary)

    def as_dict(self):
        """Gets a dict representation of this summary.

        Returns:
            A dict with a top-level key indicating the type of component being
            summarized. The value of that key is another dict with the different
            fields used to summarize the component as keys. The values of those
            dicts the results of `as_dict` on the `FieldSummary` objects for
            those fields.
        """
        component_summary = {'by_{}'.format(field_summary.field.canonical_name): field_summary.as_dict()
                             for field_summary in self.field_summaries}
        return {'{}_summary'.format(self.comp_type.arg_name): component_summary}

    def __str__(self):
        """Gets a string representation of this summary.

        Format is similar to the return value of `as_dict`, but the nested keys
        are replaced by nested section headings. Counts are displayed as tables,
        and listings are displayed as densely formatted lists.

        Returns:
            The string representation of this summary.
        """
        result = get_rst_header('Summary of all {} in the '
                                'system'.format(self.comp_type.plural_pretty_name()),
                                header_level=1) + '\n'
        result += self.get_counts_str()
        if self.include_xnames:
            result += self.get_listings_string()
        return result

    def get_counts_str(self):
        """Gets the counts portion of the string representation of this summary.

        Returns:
            A string representing the counts in this summary.
        """
        result = ''
        for field_summary in self.field_summaries:
            result += get_rst_header(
                'Counts of {} by {}'.format(self.comp_type.plural_pretty_name(),
                                            field_summary.field.pretty_name),
                header_level=2
            )
            result += field_summary.get_counts_string() + '\n'
        return result

    def get_listings_string(self):
        """Gets the listings portion of the string representation of this summary.

        Returns:
            A string representing the listings in this summary.
        """
        result = ''
        for field_summary in self.field_summaries:
            result += get_rst_header(
                'Listings of {} by {}'.format(self.comp_type.plural_pretty_name(),
                                              field_summary.field.pretty_name),
                header_level=2
            ) + '\n'
            result += field_summary.get_listings_string() + '\n'
        return result


class FieldSummary:

    def __init__(self, comp_type, field, components, include_xnames, reverse=False):
        """Creates a new FieldSummary object.

        This represents a summary of one component type by one field.

        Args:
            comp_type: The type of component being summarized, subclass of
                BaseComponent.
            field (sat.cli.hwinv.field.ComponentField): The field to summarize the
                components by.
            components (Iterable): An Iterable of BaseComponent objects to
                summarize.
            include_xnames (bool): Whether to include xnames in summaries or
                just counts.
            reverse (bool): If True, then the rows will be printed in descending order
                of the first column when pretty-printed. If False, then they will be
                printed in ascending order.
        """
        self.comp_type = comp_type
        self.field = field
        self.components = components
        self.include_xnames = include_xnames
        self.summary_dict = {}

        if self.include_xnames:
            def category_constructor():
                return dict(elements=[], count=0)
        else:
            def category_constructor():
                return dict(count=0)

        summary = defaultdict(category_constructor)
        for component in self.components:
            attr_value = getattr(component, self.field.property_name)

            if self.include_xnames:
                summary[attr_value]['elements'].append(component.xname)
            summary[attr_value]['count'] += 1

        # Turn it into a normal dict for ease of dumping with YAML
        self.summary_dict = dict(summary)
        self.reverse = reverse

    def as_dict(self):
        """Gets a dict representation of this field summary.

        Returns:
            A dict mapping from field values to a dict that contains keys:
                counts: An integer value representing the count of components
                    with the given value for the field.
                elements: A list of the components with the given value for the
                    field. Only present if `self.include_xnames` is True.
        """
        return self.summary_dict

    def prepare_summary(self):
        """Sorts and possibly reverses the summary contents for printing.

        This is a simple helper function for get_counts_string and
        get_listings_string.

        Returns:
            A sequence containing the sorted summary, and if this object's
            `reverse` attribute is True, then the sorted summary is reversed
            as well.
        """
        summary_items = sorted(self.summary_dict.items())
        if self.reverse:
            return reversed(summary_items)
        return summary_items

    def get_counts_string(self):
        """Gets a string representation of the counts in this summary.

        Returns:
            A string representation of the counts in this summary.
        """

        table_heading = [self.field.pretty_name, 'Count']
        table_rows = [[attr_value, val_members['count']]
                      for attr_value, val_members in self.prepare_summary()]
        return get_pretty_printed_list(table_rows, table_heading) + '\n'

    def get_listings_string(self):
        """Gets a string representation of the elements in this summary.

        Returns:
            A string representation of the listings in this summary.
        """
        result = ''
        for field_value, val_members in self.prepare_summary():
            result += get_rst_header(
                '{} {} with {}: {}'.format(val_members['count'],
                                           self.comp_type.plural_pretty_name(),
                                           self.field.pretty_name, field_value),
                header_level=3
            )
            result += format_as_dense_list(sorted(val_members['elements'])) + '\n'
        return result
