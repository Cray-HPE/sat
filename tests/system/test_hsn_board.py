"""
Unit tests for sat.system.hsn_board.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest

from sat.system.hsn_board import HSNBoard
from tests.system.component_data import HSN_BOARD_XNAME, get_component_raw_data


class TestHSNBoard(unittest.TestCase):
    """Test the HSNBoard class."""

    def test_init(self):
        raw_data = get_component_raw_data(hsm_type='HSNBoard', xname=HSN_BOARD_XNAME)
        hsn_board = HSNBoard(raw_data)
        self.assertEqual(raw_data, hsn_board.raw_data)
        self.assertEqual(hsn_board.children_by_type, {})


if __name__ == '__main__':
    unittest.main()
