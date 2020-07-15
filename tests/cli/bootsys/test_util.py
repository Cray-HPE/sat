"""
Tests for common bootsys code.

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

import itertools
import unittest
from unittest.mock import Mock, patch

from sat.cli.bootsys.util import get_ncns, wait_for_nodes_powerstate


class TestGetNcns(unittest.TestCase):
    def test_get_groups_with_no_exclude(self):
        """Test getting NCNs without excludes"""
        all_ncns = {'foo', 'bar', 'baz'}
        with patch('sat.cli.bootsys.util.get_groups', side_effect=[all_ncns, set()]):
            self.assertEqual(sorted(all_ncns), get_ncns([]))

    def test_get_groups_with_exclude(self):
        """Test getting NCNs with exclusions"""
        all_ncns = {'foo', 'bar', 'baz'}
        exclusions = {'foo'}
        with patch('sat.cli.bootsys.util.get_groups', side_effect=[all_ncns, exclusions]):
            result = get_ncns([])
            self.assertEqual(result, sorted(['bar', 'baz']))


class TestWaitForNodes(unittest.TestCase):
    def setUp(self):
        self.mock_monotonic = patch('sat.cli.bootsys.util.time.monotonic',
                                    return_value=0).start()
        mock_ipmi_on = Mock()
        mock_ipmi_on.get_power.return_value = {'powerstate': 'on'}

        self.mock_ipmi_cmds = list(zip(['foo', 'bar', 'baz'],
                                       itertools.repeat(mock_ipmi_on)))

    def tearDown(self):
        patch.stopall()

    def test_wait_for_nodes_successful(self):
        remaining = wait_for_nodes_powerstate(self.mock_ipmi_cmds, 'on', 1)
        self.assertEqual(len(remaining), 0)

    def test_wait_for_nodes_with_failures(self):
        mock_ipmi_off = Mock()
        mock_ipmi_off.get_power.return_value = {'powerstate': 'off'}
        self.mock_ipmi_cmds[0] = ('foo', mock_ipmi_off)

        self.mock_monotonic.side_effect = itertools.count(0, 10)

        remaining = wait_for_nodes_powerstate(self.mock_ipmi_cmds, 'on', 1)
        self.assertEqual(len(remaining), 1)
        self.assertIn('foo', remaining)
