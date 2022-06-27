#
# MIT License
#
# (C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP
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
Class to define a field on a component.
"""
import re

from sat.filtering import is_subsequence


class ComponentField:
    """A field of a component."""

    def __init__(self, pretty_name, listable=True, summarizable=False, property_name=None):
        """Creates a new component field.

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

        This canonicalizes the given filter string and then checks whether it's a
        subsequence of this field's canonical name, unless the filter is double-
        quoted, and then the check is for an exact match of the canonicalized
        strings.
        """

        if len(filter_str) > 1 and filter_str[0] == filter_str[-1] == '"':
            return self.canonicalize(filter_str[1:-1]) == self.canonical_name
        else:
            return is_subsequence(self.canonicalize(filter_str),
                                  self.canonical_name)

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
