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
Unit tests for sat.system.hsn_board.
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
