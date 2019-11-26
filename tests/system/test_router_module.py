"""
Unit tests for sat.system.router_module.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import unittest

from sat.system.router_module import RouterModule
from tests.system.component_data import ROUTER_MODULE_XNAME, get_component_raw_data


class TestRouterModule(unittest.TestCase):
    """Test the RouterModule class."""

    def test_init(self):
        raw_data = get_component_raw_data(hsm_type='RouterModule', xname=ROUTER_MODULE_XNAME)
        router_module = RouterModule(raw_data)
        self.assertEqual(raw_data, router_module.raw_data)
        self.assertEqual(router_module.children_by_type, {})


if __name__ == '__main__':
    unittest.main()
