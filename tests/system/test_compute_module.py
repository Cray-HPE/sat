"""
Unit tests for sat.system.compute_module.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest

from sat.system.compute_module import ComputeModule
from tests.system.component_data import COMPUTE_MODULE_XNAME, get_component_raw_data


class TestComputeModule(unittest.TestCase):
    """Test the ComputeModule class."""

    def test_init(self):
        raw_data = get_component_raw_data(hsm_type='ComputeModule', xname=COMPUTE_MODULE_XNAME)
        compute_module = ComputeModule(raw_data)
        self.assertEqual(raw_data, compute_module.raw_data)
        self.assertEqual(compute_module.children_by_type, {})


if __name__ == '__main__':
    unittest.main()
