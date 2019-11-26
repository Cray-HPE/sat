"""
Unit tests for sat.system.processor.

Copyright 2019 Cray Inc. All Rights Reserved.
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
