"""
Unit tests for the sat.cli.showrev.containers .

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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

import logging
import unittest
from unittest import mock

from docker.errors import DockerException

import sat.cli.showrev


class FakeDockerImage:
    def __init__(self, id, short_id, tags):
        self.id = id
        self.short_id = short_id
        self.tags = tags


# Output grabbed from docker.from_env().images.list() .
fakeimagelist = [
    FakeDockerImage(
        'sha256:304735eab4e4df55b236f9835104cb1058bc50cb5ff7f4ee7d719cb56d2a718b',
        'sha256:304735eab4',
        [
            'sms.local:5000/kf033/prom/statsd-exporter:latest',
            'sms.local:5000/kf033/prom/statsd-exporter:v0.6.0']),
    FakeDockerImage(
        'sha256:56d414270ae3ca3b4bd09b8ec7971895360427bb71047c04e9c6313cb22cfcff',
        'sha256:56d414270a',
        ['cache/zookeeper:latest']),
    FakeDockerImage(
        'sha256:c2ce1ffb51ed60c54057f53b8756231f5b4b792ce04113c6755339a1beb25943',
        'sha256:c2ce1ffb51',
        [
            'cache/k8s-dns-dnsmasq-nanny-amd64:1.14.8',
            'sms.local:5000/cache/k8s-dns-dnsmasq-nanny-amd64:1.14.8',
            'sms.local:5000/cache/k8s-dns-dnsmasq-nanny-amd64:latest']),
    FakeDockerImage(
        'sha256:6f7f2dc7fab5d7e7f99dc4ac176683a981a9ff911d643b9f29ffa146838deda3',
        'sha256:6f7f2dc7fa',
        [
            'cache/k8s-dns-sidecar-amd64:1.14.8',
            'sms.local:5000/cache/k8s-dns-sidecar-amd64:1.14.8',
            'sms.local:5000/cache/k8s-dns-sidecar-amd64:latest']),
    FakeDockerImage(
        'sha256:80cc5ea4b547abe174d7550b82825ace40769e977cde90495df3427b3a0f4e75',
        'sha256:80cc5ea4b5',
        [
            'cache/k8s-dns-kube-dns-amd64:1.14.8',
            'sms.local:5000/cache/k8s-dns-kube-dns-amd64:1.14.8',
            'sms.local:5000/cache/k8s-dns-kube-dns-amd64:latest']),
    FakeDockerImage(
        'sha256:da86e6ba6ca197bf6bc5e9d900febd906b133eaa4750e6bed647b0fbe50ed43e',
        'sha256:da86e6ba6c',
        [
            'cache/pause-amd64:3.1',
            'k8s.gcr.io/pause-amd64:3.1',
            'sms.local:5000/cache/pause-amd64:3.1',
            'sms.local:5000/cache/pause-amd64:latest',
            'sms.local:5000/cache/pause:3.1',
            'sms.local:5000/cache/pause:latest']),
]


# used to mock docker.from_env().images.list .
class FakeLister:
    def list(self):
        return fakeimagelist


# used to mock return from docker.from_env as used in showrev.containers.
class FakeDockerEnv:
    def __init__(self):
        self.images = FakeLister()


class TestContainers(unittest.TestCase):

    @mock.patch('sat.cli.showrev.containers.docker.from_env', FakeDockerEnv)
    def test_get_dockers(self):
        """Positive test case for get_dockers. Verifies a sorted list of returns.
        """
        result = sat.cli.showrev.containers.get_dockers()
        self.assertEqual(result, sorted(result))
        self.assertGreater(len(result), 0)

    def test_get_dockers_error(self):
        """Test an error is logged when docker.from_env() returns an error."""
        with mock.patch('sat.cli.showrev.containers.docker.from_env', side_effect=DockerException):
            with self.assertLogs(level=logging.ERROR):
                self.assertEqual(sat.cli.showrev.containers.get_dockers(), [])


if __name__ == '__main__':
    unittest.main()
