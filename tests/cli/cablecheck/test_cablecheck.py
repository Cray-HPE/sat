"""
Unit tests for sat.sat.cli.cablecheck.

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


from argparse import Namespace
from unittest import mock
import unittest

import sat.cli.cablecheck.main


class MockRunner:
    def __init__(self):
        self.args = None

    def run(self, args):
        self.args = ' '.join(args[2:])


class TestArgumentPassing(unittest.TestCase):
    runner = MockRunner()

    @mock.patch('sat.cli.cablecheck.main.subprocess', runner)
    def test_no_extra_arguments(self):
        """Test with no extra arguments"""
        args = Namespace(p2p_file='foo.p2p', link_levels=None, nic_prefix=None, quiet=False)

        sat.cli.cablecheck.main.do_cablecheck(args=args)
        self.assertEqual(self.runner.args, 'foo.p2p')

    @mock.patch('sat.cli.cablecheck.main.subprocess', runner)
    def test_with_prefix(self):
        """Test with a NIC prefix"""
        args = Namespace(p2p_file='foo.p2p', link_levels=None, nic_prefix='bar', quiet=False)

        sat.cli.cablecheck.main.do_cablecheck(args=args)
        self.assertEqual(self.runner.args, 'foo.p2p -n bar')

    @mock.patch('sat.cli.cablecheck.main.subprocess', runner)
    def test_with_quiet(self):
        """Test with less verbosity"""
        args = Namespace(p2p_file='foo.p2p', link_levels=None, nic_prefix=None, quiet=True)

        sat.cli.cablecheck.main.do_cablecheck(args=args)
        self.assertEqual(self.runner.args, 'foo.p2p -q')

    @mock.patch('sat.cli.cablecheck.main.subprocess', runner)
    def test_with_link_levels(self):
        """Test with explcit link levels"""

        # One link level
        #
        args = Namespace(p2p_file='foo.p2p', link_levels=['2'], nic_prefix=None, quiet=False)

        sat.cli.cablecheck.main.do_cablecheck(args=args)
        self.assertEqual(self.runner.args, 'foo.p2p -l 2')

        # Two link levels
        #
        args = Namespace(p2p_file='foo.p2p', link_levels=['2', '1'], nic_prefix=None, quiet=False)

        sat.cli.cablecheck.main.do_cablecheck(args=args)
        self.assertEqual(self.runner.args, 'foo.p2p -l 2 1')

        # Three link levels
        #
        args = Namespace(p2p_file='foo.p2p', link_levels=['2', '1', '0'], nic_prefix=None, quiet=False)

        sat.cli.cablecheck.main.do_cablecheck(args=args)
        self.assertEqual(self.runner.args, 'foo.p2p -l 2 1 0')
