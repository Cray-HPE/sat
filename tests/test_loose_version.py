#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
Tests for the LooseVersion utility class.
"""

import unittest

from sat.loose_version import LooseVersion


class TestLooseVersion(unittest.TestCase):
    """Tests for the XName class"""

    def setUp(self):
        self.examples = [
            "1.0.0",
            "1.0.0",
            "1.0.2",
            "2.1.3",
            "20240129105721.3d243a4b5120",
            "1.9.16-20240522115029.beaa1ce7a544",
            "1.9.18-20240625143747.59e8b16343aa",
            "2.1.1-64-cos-3.0-aarch64",
            "23.10.30-20231027",
            "2.2.0-57-cos-3.0-x86-64"
        ]

    def test_version_str(self):
        """Test version_str property stores unmodified version string"""
        for version_str in self.examples:
            self.assertEqual(LooseVersion(version_str).version_str, version_str)

    def test_bad_version_str(self):
        """Test that bad version string evaluates to max value"""
        bad_version_str = "1"
        good_version_str = "2.0.0"
        self.assertLess(LooseVersion(good_version_str), LooseVersion(bad_version_str))

    def test_eq(self):
        """Test __eq__ for LooseVersion."""
        for version_str in self.examples:
            self.assertEqual(LooseVersion(version_str), LooseVersion(version_str))

    def test_lt(self):
        """Test __lt__ for LooseVersion."""
        self.assertLess(LooseVersion('1.0.0'), LooseVersion('1.0.1'))

    def test_le(self):
        """Test __le__ for LooseVersion."""
        self.assertLessEqual(LooseVersion('1.0.0'), LooseVersion('1.0.1'))
        self.assertLessEqual(LooseVersion('1.0.1'), LooseVersion('1.0.1'))

    def test_gt(self):
        """Test __gt__ for LooseVersion."""
        self.assertGreater(LooseVersion('1.0.1'), LooseVersion('1.0.0'))

    def test_ge(self):
        """Test __ge__ for LooseVersion."""
        self.assertGreaterEqual(LooseVersion('1.0.0'), LooseVersion('1.0.0'))
        self.assertGreaterEqual(LooseVersion('1.0.1'), LooseVersion('1.0.0'))

    def test_repr(self):
        """Test __repr__ for LooseVersion."""
        for version_str in self.examples:
            self.assertEqual(repr(LooseVersion(version_str)), "LooseVersion('{}')".format(version_str))

    def test_str(self):
        for version_str in self.examples:
            self.assertEqual(str(LooseVersion(version_str)), version_str)
