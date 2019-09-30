"""
Class to define a field on a component.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import re


class ComponentField:
    """A field of a component."""

    def __init__(self, pretty_name, listable=True, summarizable=False, property_name=None):
        """Creates a  new component field.

        Args:
            pretty_name (str): The human-readable name of the field.
            listable (bool): Whether the field can be included in a listing
                of the components.
            summarizable (bool): Whether the field can be used to summarize
                components based on the value of this field.
            property_name (str): The name of the property that gives the value
                for this field on the component. Defaults to a canonical version
                of the `pretty_name`, which is all lowercase and has spaces and
                hyphens replaced with underscores.
        """
        self.pretty_name = pretty_name
        self.listable = listable
        self.summarizable = summarizable
        self.canonical_name = self.canonicalize(pretty_name)
        self.property_name = property_name if property_name else self.canonical_name

    def matches(self, filter_str):
        """Returns whether this field matches the given filter string.

        For now, this just canonicalizes the given filter string and checks
        whether the given it's a substring of this field's canonical name.
        """
        return self.canonicalize(filter_str) in self.canonical_name

    @staticmethod
    def canonicalize(name):
        """Canonicalize the given name by converting to lowercase and replacing chars.

        Replaces '-' and ' ' with '_'. Removes parentheses.

        Returns:
            The canonical form of the given name.
        """
        return re.sub(r'[- ]', '_', re.sub(r'[()]', '', name.lower()))

    def __eq__(self, other):
        return (self.pretty_name, self.listable, self.summarizable, self.property_name) == \
               (other.pretty_name, other.listable, other.summarizable, other.property_name)

    def __ne__(self, other):
        return not self == other

    def __hash__(self):
        """Just return the hash of the xname tokens."""
        return hash((self.pretty_name, self.listable, self.summarizable, self.property_name))
