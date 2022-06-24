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
Tests for the XName utility class.
"""

import unittest

from sat.xname import XName, get_matches


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

    def test_drive_get_node_parent(self):
        """Test getting the parent node xname of a drive xname."""
        drive_xname_str = 'x1000c3s5b0n1g1k1'
        node_xname_str = drive_xname_str[:-4]
        self.assertEqual(XName(node_xname_str),
                         XName(drive_xname_str).get_parent_node())

    def test_processor_get_node_parent(self):
        """Test getting the parent node xname of a processor xname."""
        proc_xname_str = 'x1000c3s5b0n1p1'
        node_xname_str = proc_xname_str[:-2]
        self.assertEqual(XName(node_xname_str),
                         XName(proc_xname_str).get_parent_node())

    def test_node_get_node_parent(self):
        """Test getting the parent node xname of a node xname."""
        node_xname_str = 'x1000c3s5b0n1'
        # The parent node of a node should just be itself
        self.assertEqual(XName(node_xname_str),
                         XName(node_xname_str).get_parent_node())

    def test_chassis_get_node_parent(self):
        """Test getting the parent node xname of a drive xname."""
        chassis_xname_str = 'x1000c3'
        # A chassis should not find a parent node
        self.assertEqual(None, XName(chassis_xname_str).get_parent_node())


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


class TestXnameGetMatches(unittest.TestCase):

    def test_get_matches_chassis(self):
        """Test Xname get_matches() with chassis filter."""
        filters = [XName('x1000c1'), XName('x2000c2')]
        elems = [XName('x1000c1r1b1'), XName('x1000c2r2b2')]
        used, unused, matches, no_matches = get_matches(filters, elems)
        self.assertEqual({XName('x1000c1')}, used)
        self.assertEqual({XName('x2000c2')}, unused)
        self.assertEqual({XName('x1000c1r1b1')}, matches)
        self.assertEqual({XName('x1000c2r2b2')}, no_matches)

    def test_get_matches_bmc(self):
        """Test Xname get_matches() with BMC filter."""
        filters = [XName('x1000c1r1b1'), XName('x2000c2r2b2')]
        elems = [XName('x1000c1r1b1'), XName('x1000c2r2b2')]
        used, unused, matches, no_matches = get_matches(filters, elems)
        self.assertEqual({XName('x1000c1r1b1')}, used)
        self.assertEqual({XName('x2000c2r2b2')}, unused)
        self.assertEqual({XName('x1000c1r1b1')}, matches)
        self.assertEqual({XName('x1000c2r2b2')}, no_matches)

    def test_get_matches_empty_filters(self):
        """Test Xname get_matches() with empty filter."""
        filters = []
        elems = [XName('x1000c1r1b1'), XName('x1000c2r2b2')]
        used, unused, matches, no_matches = get_matches(filters, elems)
        self.assertEqual(set(), used)
        self.assertEqual(set(), unused)
        self.assertEqual(set(), matches)
        self.assertEqual(set(elems), no_matches)

    def test_get_matches_no_elems(self):
        """Test Xname get_matches() with no elements."""
        filters = [XName('x1000c1r1b1'), XName('x2000c2r2b2')]
        elems = []
        used, unused, matches, no_matches = get_matches(filters, elems)
        self.assertEqual(set(), used)
        self.assertEqual(set(filters), unused)
        self.assertEqual(set(), matches)
        self.assertEqual(set(), no_matches)
