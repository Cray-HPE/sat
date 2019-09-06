"""
Unit tests for the sat.showrev.system

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import unittest


class TestSystem(unittest.TestCase):

    def test_get_sles_version(self):
        """
        Test get_sles_version happy path.
        """
        # TODO: Bo to fill this in with an actual test of the happy path
        self.assertEqual(True, True)

    def test_get_sles_version_sad(self):
        """
        Test get_sles_version sad path.
        """
        # TODO: Bo to fill this in with an actual test of the sad path
        # There are probably more error cases to test, so additional
        # test methods will be necessary.
        self.assertEqual(True, True)


if __name__ == '__main__':
    unittest.main()
