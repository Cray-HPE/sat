"""
Unit tests for sat.system.node_enclosure.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest

from sat.system.node_enclosure import NodeEnclosure
from tests.system.component_data import NODE_ENCLOSURE_XNAME, get_component_raw_data


class TestNodeEnclosure(unittest.TestCase):
    """Test the NodeEnclosure class."""

    def test_init(self):
        raw_data = get_component_raw_data(hsm_type='NodeEnclosure', xname=NODE_ENCLOSURE_XNAME)
        node_enclosure = NodeEnclosure(raw_data)
        self.assertEqual(raw_data, node_enclosure.raw_data)
        self.assertEqual(node_enclosure.children_by_type, {})


if __name__ == '__main__':
    unittest.main()
