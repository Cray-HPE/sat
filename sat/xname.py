#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Class for representing an xname.
"""
import re
from collections import OrderedDict

from sat.cached_property import cached_property


class XName:
    """An xname representing a component in the system."""

    XNAME_REGEX_BY_TYPE = OrderedDict([
        ('NODE', re.compile(r'x\d+c\d+s\d+b\d+n\d+')),
        ('BMC', re.compile(r'x\d+c\d+s\d+b\d+$')),
        ('SLOT', re.compile(r'x\d+c\d+s\d+$')),
        ('CHASSIS', re.compile(r'x\d+c\d+$')),
        ('CABINET', re.compile(r'x\d+$'))
    ])

    def __init__(self, xname_str):
        """Creates a new xname object from the given xname string.

        Args:
            xname_str (str): The string representation of the xname.
        """
        self.xname_str = xname_str

    @cached_property
    def tokens(self):
        """tuple: The tokenized form of the xname.

        Numeric elements are converted to integers which strips leading zeros.

        The tokens are a sequence with the alternating string and integer
        elements of the xname. For example, the tokens for the xname
        "x3000c0s28b0n0" would be:

            ('x', 3000, 'c', 0, 's', 28, 'b', 0, 'n', 0).
        """
        # the last element will always be an empty string, since the input string
        # ends with a match.
        toks = re.split(r'(\d+)', self.xname_str)[:-1]

        for i, tok in enumerate(toks):
            if i % 2 == 1:
                toks[i] = int(toks[i])
            else:
                toks[i] = toks[i].lower()

        return tuple(toks)

    @classmethod
    def get_xname_from_tokens(cls, tokens):
        """Gets an XName instance from the given tokens.

        Note that creating a new XName from its tokens can result in an XName
        with a different string representation, but they are still considered
        equal because they will have the same tokens.

        xname = XName('x0001c0')
        new_xname = XName.get_xname_from_tokens(xname.tokens)
        print(xname)
        -> x0001c0
        print(new_xname)
        -> x1c0
        xname == new_xname
        -> True

        Args:
            tokens (Iterable): An iterable of tokens for the xname.
        """
        xname_str = ''.join(str(t) for t in tokens)
        return cls(xname_str)

    def get_type(self):
        """Get the type of the xname using the str representation and regular expression.

        Returns:
            A str from XNAME_TYPES.
        """
        for xname_type, xname_regex in self.XNAME_REGEX_BY_TYPE.items():
            if xname_regex.fullmatch(self.xname_str):
                return xname_type

        return 'UNKNOWN'

    def get_ancestor(self, levels):
        """Get the ancestor of this xname by stripping off levels.

        Args:
            levels (int): the number of levels to strip off this xname to get
                the ancestor. Specifying 1 is equivalent to get_direct_parent.

        Returns:
            An XName object that is the ancestor the given number of levels up
            the hierarchy.
        """
        reverse_index = 2 * levels
        if reverse_index >= len(self.tokens):
            raise ValueError('No ancestor exists {} levels '
                             'up from {}'.format(levels, self))

        return XName.get_xname_from_tokens(self.tokens[:-reverse_index])

    def get_direct_parent(self):
        """Get the direct parent of this xname.

        E.g., the direct parent of the xname 'x3000c0s0b0n0p0' would be
        'x3000c0s0b0n0'.

        Returns:
            An XName object that is the parent of this object.
        """
        return self.get_ancestor(1)

    def get_parent_node(self):
        """Get the xname of the parent node of this xname, if possible.

        Returns:
            The parent node XName of this XName, or None if this XName is not
            the child of a node XName.
        """
        match = self.XNAME_REGEX_BY_TYPE['NODE'].match(str(self))
        if match:
            return XName(match.group(0))

        return None

    def get_cabinet(self):
        """Get the cabinet of this xname.

        Returns:
            An XName object that is the cabinet.
        """
        return XName.get_xname_from_tokens(self.tokens[:2])

    def get_chassis(self):
        """Get the chassis of this xname.

        Returns:
            An XName object that is the cabinet.
        """
        return XName.get_xname_from_tokens(self.tokens[:4])

    def __lt__(self, other):
        return self.tokens < other.tokens

    def __le__(self, other):
        return self.tokens <= other.tokens

    def __eq__(self, other):
        return (isinstance(self, type(other)) and
                self.tokens == other.tokens)

    def __gt__(self, other):
        return self.tokens > other.tokens

    def __ge__(self, other):
        return self.tokens >= other.tokens

    def __hash__(self):
        return hash(self.tokens)

    def __str__(self):
        return self.xname_str

    def __repr__(self):
        return self.xname_str

    def contains_component(self, other):
        """Returns whether this component contains another.

        Tests whether the component represented by this xname contains the
        component represented by the `other` xname. Also returns true when
        this xname is the same as the other.

        E.g., the xname 'x1000c0' represents chassis 0 in cabinet 1000, and
        the xname 'x1000c0s5b0n0' represents a node in that chassis, so
        XName('x1000c0').contains_component(XName('x1000c0s5b0n0')) would be
        true.

        Returns:
            True if this xname contains the other or is the same as the other.
        """
        if not isinstance(self, type(other)):
            return False

        if len(self.tokens) > len(other.tokens):
            return False

        for idx, token in enumerate(self.tokens):
            if other.tokens[idx] != token:
                return False
        return True


def get_matches(filters, elems):
    """Separate a list into matching and unmatched members.

    Args:
        filters: List of xnames having the type XName. If an elem in
            elems is contained by an xname in this list, meaning it is
            above the element xname in the hierarchy of xname components,
            then it will be considered a match.
        elems: List of xnames to filter.

    Returns:
        used: Set of filters that generated a match.
        unused: Set of filters that did not generate a match.
        matches: Set of elements that matched one or more filters.
        no_matches: Set of elements that did not match anything.
    """
    used = set()
    unused = set(filters)
    matches = set()
    no_matches = set(elems)

    for elem in elems:
        for filter_ in filters:
            if filter_.contains_component(elem):
                used.add(filter_)
                unused.discard(filter_)
                matches.add(elem)
                no_matches.discard(elem)

    return used, unused, matches, no_matches
