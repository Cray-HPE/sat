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
Unit tests for sat.system.processor.
"""
import unittest

from sat.system.processor import Processor
from tests.system.component_data import PROCESSOR_XNAME, get_component_raw_data

TOTAL_CORES = 18
TOTAL_THREADS = 36
MAX_SPEED_MHZ = 4000


def get_processor_raw_data(xname=PROCESSOR_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='Processor', xname=xname, **kwargs)
    extra_fru_info = {
        'TotalCores': TOTAL_CORES,
        'TotalThreads': TOTAL_THREADS,
        'MaxSpeedMHz': MAX_SPEED_MHZ
    }
    component_data['PopulatedFRU']['ProcessorFRUInfo'].update(extra_fru_info)
    return component_data


class TestProcessor(unittest.TestCase):
    """Test the Processor class."""

    def setUp(self):
        """Create a Processor object to use in the tests."""
        self.raw_data = get_processor_raw_data()
        self.processor = Processor(self.raw_data)

    def test_init(self):
        """Test initialization of a Processor object."""
        self.assertEqual(self.raw_data, self.processor.raw_data)
        self.assertIsNone(self.processor.node)
        self.assertEqual(self.processor.children_by_type, {})

    def test_total_cores(self):
        """Test the total_cores property."""
        self.assertEqual(self.processor.total_cores, TOTAL_CORES)

    def test_total_threads(self):
        """Test the total_threads property."""
        self.assertEqual(self.processor.total_threads, TOTAL_THREADS)

    def test_max_speed_mhz(self):
        """Test the max_speed_mhz property."""
        self.assertEqual(self.processor.max_speed_mhz, MAX_SPEED_MHZ)


if __name__ == '__main__':
    unittest.main()
