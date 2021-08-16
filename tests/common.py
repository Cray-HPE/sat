"""
A helper subclass of TestCase that implements additional assertions.

(C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""
import re
import unittest


class ExtendedTestCase(unittest.TestCase):
    """A subclass that implements additional helpful assertions."""

    def assert_in_element(self, element, container):
        """Assert the given element is in one of the elements in container.

        Args:
            element: The element to search for
            container (Iterable): The iterable in which to search for an item
                that contains element.
        Returns:
            None.

        Raises:
            AssertionError: if the assertion fails.
        """
        for item in container:
            if element in item:
                return
        self.fail("Element '{}' is not in any of the elements in "
                  "the given container.".format(element))

    def assert_not_in_element(self, element, container):
        """Assert the given element is not in one of the elements in container.

        Args:
            element: The element to search for
            container (Iterable): The iterable in which to search for an item
                that contains element.
        Returns:
            None.

        Raises:
            AssertionError: if the assertion fails.
        """
        for item in container:
            if element in item:
                self.fail("Element '{}' is in one of the elements in "
                          "the given container.".format(element))

    def assert_regex_matches_element(self, regex_str, container):
        """Assert the given regex matches one of the elements in container.

        Args:
            regex_str (str): The regular expression string to match
            container (Iterable of str): The iterable in which to search for a
                match for the regex_str

        Returns:
            None.

        Raises:
            AssertionError: if the assertion fails.
        """
        regex = re.compile(regex_str)

        for item in container:
            if regex.match(item):
                return
        self.fail("Regex '{}' does not match any of the elements in "
                  "the given container.".format(regex_str))
