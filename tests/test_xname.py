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


class TestXNameContainsComponent(unittest.TestCase):
    """Tests for whether xname for a component contains another."""

    def test_cabinet_contains_node(self):
        """Test that a cabinet contains a node and not vice versa."""
        cabinet = XName('x1000')
        node = XName('x1000c0s5b0n0')
        # Cabinet should contain node
        self.assertTrue(cabinet.contains_component(node))
        # Node should not contain cabinet
        self.assertFalse(node.contains_component(cabinet))

    def test_chassis_does_not_contain_node(self):
        """Test that a chassis does not contain a node."""
        chassis = XName('x1000c4')
        node = XName('x1000c3s1b0n0')
        self.assertFalse(chassis.contains_component(node))

    def test_component_contains_itself(self):
        """Test that a chassis contains itself."""
        xname_str = 'x1000c0'
        # Make two XNames that use the same xname string
        xname = XName(xname_str)
        same_xname = XName(xname_str)

        # Test with the same exact object
        self.assertTrue(xname.contains_component(xname))
        # Test with two different, but equal objects, both directions
        self.assertTrue(xname.contains_component(same_xname))
        self.assertTrue(same_xname.contains_component(xname))

    def test_prefix_slot_does_not_contain_node(self):
        """Test that a slot does not contain a different node in a different slot.

        The slot in this example has an xname that is a substring of a node in
        a different slot, but the slot is different and should not say it
        contains the node.
        """
        slot_1 = XName('x3000c0s1')
        node_in_slot_19 = XName('x3000c0s19b0n0')
        self.assertFalse(slot_1.contains_component(node_in_slot_19))
