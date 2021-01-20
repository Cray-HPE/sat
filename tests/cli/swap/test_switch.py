"""
Unit tests for sat.cli.swap.switch

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
from argparse import Namespace
from sat.cli.swap.switch import swap_switch


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.xname = 'x1000c6r7'
    namespace.action = None
    namespace.disruptive = True
    namespace.dry_run = True
    namespace.save_ports = False


class TestSwapSwitch(unittest.TestCase):
    """Unit tests for swap_switch"""

    def setUp(self):
        """Mock functions called."""
        self.fake_swap = mock.patch('sat.cli.swap.switch.SwitchSwapper').start().return_value
        self.fake_swap_component = self.fake_swap.swap_component
        self.fake_swap_component.return_value = None
        self.fake_args = Namespace()
        set_options(self.fake_args)

    def test_swap_switch(self):
        """Swapping a switch should call the switch swap function"""
        swap_switch(self.fake_args)
        self.fake_swap_component.assert_called_once_with(self.fake_args.action,
                                                         self.fake_args.xname,
                                                         self.fake_args.disruptive,
                                                         self.fake_args.dry_run,
                                                         self.fake_args.save_ports)


if __name__ == '__main__':
    unittest.main()
