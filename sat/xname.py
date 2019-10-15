"""
Class for representing an xname in an EX-1 system.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import re

from sat.cached_property import cached_property


class XName:
    """An xname representing a component in an EX-1 system."""

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

    def get_direct_parent(self):
        """Get the direct parent of this xname.

        E.g., the direct parent of the xname 'x3000c0s0b0n0p0' would be
        'x3000c0s0b0n0'.

        Returns:
            An XName object that is the parent of this object.
        """
        return XName.get_xname_from_tokens(self.tokens[:-2])

    def __lt__(self, other):
        return self.tokens < other.tokens

    def __le__(self, other):
        return self.tokens <= other.tokens

    def __eq__(self, other):
        return self.tokens == other.tokens

    def __ne__(self, other):
        return self.tokens != other.tokens

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
