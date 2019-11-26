"""
A helper subclass of TestCase that implements an additional assertion.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest


class ExtendedTestCase(unittest.TestCase):
    """A subclass that implements an additional helpful assertion."""

    def assert_in_element(self, element, container):
        """Assert the given element is in one of the elements in container.

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