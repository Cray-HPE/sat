#
# MIT License
#
# (C) Copyright 2019-2022, 2024 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.apiclient.bos
"""
import unittest
from unittest.mock import MagicMock, patch

from sat.apiclient.bos import (
    BOSClientCommon,
    BOSV1Client,
    BOSV2Client,
)


class BOSClientTestCase(unittest.TestCase):
    """Base test case for BOS client tests"""

    def setUp(self):
        self.mock_get_config = patch('sat.apiclient.bos.get_config_value').start()

    def tearDown(self):
        patch.stopall()


class TestBOSClientCommon(BOSClientTestCase):
    """Tests for the BOSClientCommon base class"""

    def test_get_bos_version_v1(self):
        """Test retrieving a BOSV1Client"""
        self.mock_get_config.return_value = 'v1'
        self.assertIsInstance(BOSClientCommon.get_bos_client(MagicMock()),
                              BOSV1Client)

    def test_get_bos_version_v2(self):
        """Test retrieving a BOSV2Client"""
        self.mock_get_config.return_value = 'v2'
        self.assertIsInstance(BOSClientCommon.get_bos_client(MagicMock()),
                              BOSV2Client)

    def test_get_invalid_bos_client(self):
        """Test retrieving an invalid BOS client version throws an error"""
        for invalid_bos_version in ['v3', 'foo', 'v0', '']:
            self.mock_get_config.return_value = invalid_bos_version
            with self.assertRaises(ValueError):
                BOSClientCommon.get_bos_client(MagicMock())

    def test_get_bos_client_version_kwarg(self):
        """Test getting a BOSVxClient using the version keyword argument"""
        for version, client_cls in [('v1', BOSV1Client), ('v2', BOSV2Client)]:
            with self.subTest(version=version):
                self.assertIsInstance(
                    BOSClientCommon.get_bos_client(MagicMock(), version=version),
                    client_cls
                )

    def test_get_bos_client_version_kwarg_is_none(self):
        """Test that the client version is read from config file when version kwarg is None"""
        for version, client_cls in [('v1', BOSV1Client), ('v2', BOSV2Client)]:
            self.mock_get_config.return_value = version
            with self.subTest(version=version):
                self.assertIsInstance(
                    BOSClientCommon.get_bos_client(MagicMock(), version=None),
                    client_cls
                )
