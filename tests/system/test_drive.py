#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.system.drive.
"""
import unittest

from sat.system.drive import Drive
from tests.system.component_data import DRIVE_XNAME, get_component_raw_data

PERCENT_LIFE_LEFT = 80
CAPACITY_BYTES = 503424483328
MEDIA_TYPE = 'HDD'


def get_drive_raw_data(xname=DRIVE_XNAME, capacity_bytes=None, **kwargs):
    component_data = get_component_raw_data(hsm_type='Drive', xname=xname, **kwargs)
    extra_fru_info = {
        'MediaType': MEDIA_TYPE,
        'PredictedMediaLifeLeftPercent': PERCENT_LIFE_LEFT,
        'CapacityBytes': capacity_bytes or CAPACITY_BYTES
    }
    component_data['PopulatedFRU']['DriveFRUInfo'].update(extra_fru_info)
    return component_data


class TestDrive(unittest.TestCase):
    """Test the Drive class."""

    def setUp(self):
        """Create a Drive object to use in the tests."""
        self.raw_data = get_drive_raw_data()
        self.drive = Drive(self.raw_data)

    def test_init(self):
        """Test initialization of a Drive object."""
        self.assertEqual(self.raw_data, self.drive.raw_data)
        self.assertIsNone(self.drive.node)
        self.assertEqual(self.drive.children_by_type, {})

    def test_media_type(self):
        """Test the media_type property."""
        self.assertEqual(self.drive.media_type, MEDIA_TYPE)

    def test_capacity_bytes(self):
        """Test the capacity_bytes property."""
        self.assertEqual(self.drive.capacity_bytes, CAPACITY_BYTES)

    def test_capacity_gib(self):
        """Test the capacity_gib property."""
        self.assertEqual(self.drive.capacity_gib,
                         round(CAPACITY_BYTES / 2**30, 2))

    def test_capacity_gib_non_numeric(self):
        """Test capacity_gib w/ non-numeric data for capacity_bytes"""
        not_a_number = 'not a number'
        drive = Drive(get_drive_raw_data(capacity_bytes=not_a_number))
        self.assertEqual(drive.capacity_gib, not_a_number)

    def test_percent_life_left(self):
        """Test the percent_life_left property."""
        self.assertEqual(self.drive.percent_life_left, PERCENT_LIFE_LEFT)


if __name__ == '__main__':
    unittest.main()
