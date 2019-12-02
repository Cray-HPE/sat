"""
Unit tests for sat.system.chassis.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest

from sat.system.chassis import Chassis
from sat.system.node import Node
from tests.system.component_data import CHASSIS_XNAME, get_component_raw_data


class TestChassis(unittest.TestCase):
    """Test the Chassis class."""

    def test_init(self):
        raw_data = get_component_raw_data(hsm_type='Chassis', xname=CHASSIS_XNAME)
        chassis = Chassis(raw_data)
        self.assertEqual(raw_data, chassis.raw_data)
        self.assertEqual({}, chassis.nodes)
        self.assertIn(Node, chassis.children_by_type)


if __name__ == '__main__':
    unittest.main()
