"""
Classes to define summaries of components by various fields.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from collections import defaultdict

from sat.util import format_as_dense_list, get_rst_header, get_pretty_printed_list


class ComponentSummary:

    def __init__(self, comp_type, fields, components, include_xnames):
        """Creates a new ComponentSummary object.

        This represents a summary of one component type by multiple fields.

        Args:
            comp_type: The type of component being summarized, subclass of
                BaseComponent.
            fields (Iterable): An Iterable of ComponentField objects to
                use to summarize the components.
            components (Iterable): An Iterable of BaseComponent objects to
                summarize.
            include_xnames (bool): Whether to include xnames in summaries or
                just counts.
        """
        self.comp_type = comp_type
        self.fields = fields
        self.components = components
        self.include_xnames = include_xnames
        self.field_summaries = []
        self.summary_dict = {}

        for field in self.fields:
            field_summary = FieldSummary(self.comp_type, field,
                                         self.components, self.include_xnames)
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

    def __init__(self, comp_type, field, components, include_xnames):
        """Creates a new FieldSummary object.

        This represents a summary of one component type by one field.

        Args:
            comp_type: The type of component being summarized, subclass of
                BaseComponent.
            field (sat.hwinv.field.ComponentField): The field to summarize the
                components by.
            components (Iterable): An Iterable of BaseComponent objects to
                summarize.
            include_xnames (bool): Whether to include xnames in summaries or
                just counts.
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

    def get_counts_string(self):
        """Gets a string representation of the counts in this summary.

        Returns:
            A string representation of the counts in this summary.
        """

        table_heading = [self.field.pretty_name, 'Count']
        table_rows = [[attr_value, val_members['count']]
                      for attr_value, val_members in sorted(self.summary_dict.items())]
        return get_pretty_printed_list(table_rows, table_heading) + '\n'

    def get_listings_string(self):
        """Gets a string representation of the elements in this summary.

        Returns:
            A string representation of the listings in this summary.
        """
        result = ''
        for field_value, val_members in sorted(self.summary_dict.items()):
            result += get_rst_header(
                '{} {} with {}: {}'.format(val_members['count'],
                                           self.comp_type.plural_pretty_name(),
                                           self.field.pretty_name, field_value),
                header_level=3
            )
            result += format_as_dense_list(sorted(val_members['elements'])) + '\n'
        return result
