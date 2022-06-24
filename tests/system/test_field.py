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
Unit tests for sat.hwinv.field.
"""

import unittest

from sat.system.field import ComponentField


class TestComponentField(unittest.TestCase):
    """Tests ComponentField class"""

    def test_init(self):
        """Tests creating a new field."""
        # Use characters that should get replaced in the field name
        pretty_name = 'Field-Name (Unit)'
        expected_canonical = 'field_name_unit'
        field = ComponentField(pretty_name)
        self.assertEqual(field.pretty_name, pretty_name)
        self.assertTrue(field.listable)
        self.assertFalse(field.summarizable)
        self.assertEqual(field.canonical_name, expected_canonical)
        self.assertEqual(field.property_name, expected_canonical)

    def test_init_alternate_values(self):
        """Tests creating a new field with non-default values for kwargs."""
        field_name = 'yadayada'
        property_name = 'elaine'
        field = ComponentField(field_name, listable=False, summarizable=True,
                               property_name=property_name)
        self.assertEqual(field.pretty_name, field_name)
        self.assertFalse(field.listable)
        self.assertTrue(field.summarizable)
        self.assertEqual(field.property_name, property_name)

    def test_equality_unequal_names(self):
        """Tests that two fields with unequal names are not equal."""
        cf1 = ComponentField('thing1')
        cf2 = ComponentField('thing2')
        self.assertNotEqual(cf1, cf2)

    def test_equality_unequal_bools(self):
        """Tests that two fields with unequal boolean fields are not equal."""
        cf1 = ComponentField('carl', listable=False, summarizable=True)
        cf2 = ComponentField('carl', listable=True, summarizable=True)
        self.assertNotEqual(cf1, cf2)

    def test_equality_equal(self):
        """Tests that two identical fields are equal."""
        cf1 = ComponentField('power')
        cf2 = ComponentField('power')
        self.assertEqual(cf1, cf2)

    def test_hashable(self):
        """Tests that ComponentField objects can be added to a dict."""
        key_val_pairs = [
            (ComponentField('what'), 'power',),
            (ComponentField('the power of'), 'voodoo')
        ]
        d = dict(key_val_pairs)
        self.assertEqual(len(d), 2)
        for key, val in key_val_pairs:
            self.assertEqual(d[key], val)


class TestComponentFieldMatches(unittest.TestCase):
    """Test matches method of ComponentField"""

    def setUp(self):
        """Creates a ComponentField to work with in test methods."""
        self.cf = ComponentField('Serial Number')

    def test_matches_verbatim_name(self):
        """Tests verbatim match."""
        self.assertTrue(self.cf.matches('"Serial Number"'))
        self.assertFalse(self.cf.matches('"Number"'))

        self.assertTrue(self.cf.matches(''))
        self.assertFalse(self.cf.matches('"'))
        self.assertFalse(self.cf.matches('""'))

    def test_matches_exact_name(self):
        """Tests that the exact pretty name matches."""
        self.assertTrue(self.cf.matches('Serial Number'))

    def test_matches_different_capitalization(self):
        """Tests that a strangely capitalized name matches."""
        self.assertTrue(self.cf.matches('SeRiAl NuMbEr'))

    def test_matches_canonical(self):
        """Tests that a canonicalized name matches."""
        self.assertTrue(self.cf.matches('serial_number'))

    def test_matches_substring(self):
        """Tests that a substring of the canonicalized name matches."""
        self.assertTrue(self.cf.matches('serial_num'))

    def test_matches_subsequence(self):
        """Tests that a subsequence of the canonicalized name matches."""
        self.assertTrue(self.cf.matches('snum'))

    def test_matches_leading_whitespace(self):
        """Tests that a name with leading whitespace matches."""
        self.assertTrue(self.cf.matches('   Serial Number'))

    def test_matches_trailing_whitespace(self):
        """Tests that a name with leading whitespace matches."""
        self.assertTrue(self.cf.matches('Serial Number   '))

    def test_does_not_match(self):
        """Tests value that should not match."""
        self.assertFalse(self.cf.matches('not a match'))


class TestCanonicalize(unittest.TestCase):
    """Tests the canonicalize static method."""

    def test_already_canonical(self):
        """Tests canonicalizing a name that already is canonical"""
        canonical_name = 'bow_wow'
        self.assertEqual(canonical_name,
                         ComponentField.canonicalize(canonical_name))

    def test_spaces_and_capitals(self):
        """Tests canonicalizing a name with spaces and capital letters."""
        name = 'Sister Rosetta'
        canonical_name = 'sister_rosetta'
        self.assertEqual(canonical_name,
                         ComponentField.canonicalize(name))

    def test_parentheses(self):
        """Tests canonicalizing a name with parentheses"""
        name = 'wait up (boots of danger)'
        canonical_name = 'wait_up_boots_of_danger'
        self.assertEqual(canonical_name,
                         ComponentField.canonicalize(name))

    def test_numbers(self):
        """Tests canonicalizing a name with numbers in it."""
        name = '22 a million'
        canonical_name = '22_a_million'
        self.assertEqual(canonical_name,
                         ComponentField.canonicalize(name))

    def test_hyphens(self):
        """Tests canonicalizing a name with hyphens in it."""
        name = 'half-baked'
        canonical_name = 'half_baked'
        self.assertEqual(canonical_name,
                         ComponentField.canonicalize(name))

    def test_all_the_things(self):
        name = '25 or 6 to 4 (OVER-SOON)'
        canonical_name = '25_or_6_to_4_over_soon'
        self.assertEqual(canonical_name,
                         ComponentField.canonicalize(name))


if __name__ == '__main__':
    unittest.main()
