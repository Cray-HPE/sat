"""
Unit tests for sat.sat.cli.cablecheck.

Copyright 2020 Cray Inc. All Rights Reserved.
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
