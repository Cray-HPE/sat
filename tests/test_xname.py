"""
Tests for the XName utility class.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import unittest

from sat.xname import XName

class TestXName(unittest.TestCase):
    """Tests for the XName class"""

    def setUp(self):
        # Tuples of the form:
        #    (given_xname, real_xname, tokens, parent)
        self.examples = [
            ('x3000c0s28b0n0', 'x3000c0s28b0n0',
             ('x', 3000, 'c', 0, 's', 28, 'b', 0, 'n', 0),
             'x3000c0s28b0'),
            ('x3000c0', 'x3000c0',
             ('x', 3000, 'c', 0),
             'x3000'),
            ('x5192c3r4b0', 'x5192c3r4b0',
             ('x', 5192, 'c', 3, 'r', 4, 'b', 0),
             'x5192c3r4'),
            ('X0005192C3R4B0', 'x5192c3r4b0',
             ('x', 5192, 'c', 3, 'r', 4, 'b', 0),
             'x5192c3r4')
        ]

    def test_tokenization(self):
        """Test tokenizing an xname."""
        for given_xname, _, toks, _ in self.examples:
            self.assertEqual(XName(given_xname).tokens, toks)

    def test_untokenize(self):
        """Test getting an XName from tokens."""
        for _, real_xname, toks, _ in self.examples:
            self.assertEqual(str(XName.get_xname_from_tokens(toks)), real_xname)

    def test_getting_parent(self):
        """Test getting the direct parents of XNames."""
        for given_xname, _, _, parent in self.examples:
            self.assertEqual(XName(given_xname).get_direct_parent(),
                             XName(parent))
