#
# MIT License
#
# (C) Copyright 2023 Hewlett Packard Enterprise Development LP
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
Tests for SAT session handling
"""

import unittest

from sat.config import load_config
from sat.session import TENANT_HEADER_NAME, SATSession
from tests.common import config


class TestSessionTenantHandling(unittest.TestCase):
    def setUp(self):
        load_config()

    def test_cray_tenant_name_is_set_properly(self):
        """Test that the Cray-Tenant-Name header is set from the config"""
        tenant_name = 'some_tenant_name'
        with config({'api_gateway': {'tenant_name': tenant_name}}):
            s = SATSession()
            self.assertEqual(s.session.headers[TENANT_HEADER_NAME], tenant_name)

    def test_cray_tenant_name_not_set(self):
        """Test that the Cray-Tenant-Name header is not set when not configured"""
        with config({'api_gateway': {'tenant_name': ''}}):
            s = SATSession()
            self.assertIsNone(s.session.headers.get(TENANT_HEADER_NAME))
