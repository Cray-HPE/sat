"""
Unit tests for sat.cli.k8s logic.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

Permission is hereby granted, free of charge, to any person obtaining a
copy of this software and associated documentation files (the "Software"),
to deal in the Software without restriction, including without limitation
the rights to use, copy, modify, merge, publish, distribute, sublicense,
and/or sell copies of the Software, and to permit persons to whom the
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included
in all copies or substantial portions of the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT.  IN NO EVENT SHALL
THE AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR
OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE,
ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR
OTHER DEALINGS IN THE SOFTWARE.
"""

import unittest
from unittest import mock

from kubernetes.config.config_exception import ConfigException
from kubernetes.client.rest import ApiException

import sat.cli.k8s.main
from sat.cli.k8s.replicaset import ReplicaSet


class TestK8s(unittest.TestCase):
    """Test cases for functions in sat k8s.
    """
    def tearDown(self):
        mock.patch.stopall()

    def test_get_co_located_replicas_api_exception_config(self):
        """It should re-raise the same exception as load_kube_config.
        """
        mock.patch(
            'sat.cli.k8s.main.ReplicaSet.get_all_replica_sets',
            side_effect=ConfigException).start()

        with self.assertRaises(ConfigException):
            sat.cli.k8s.main.get_co_located_replicas()

    def test_get_co_located_replicas_api_exception_list_replicas(self):
        """It should re-raise an ApiException.
        """
        mock.patch(
            'sat.cli.k8s.main.ReplicaSet.get_all_replica_sets',
            side_effect=ApiException).start()

        with self.assertRaises(ApiException):
            sat.cli.k8s.main.get_co_located_replicas()


if __name__ == '__main__':
    unittest.main()
