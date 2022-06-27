#
# MIT License
#
# (C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.cli.swap.main
"""

import unittest
from unittest import mock
from argparse import Namespace

from sat.cli.swap.main import do_swap


def set_options(namespace):
    namespace.target = 'cable'


class TestSwapMain(unittest.TestCase):

    def setUp(self):
        self.fake_swap_cable = mock.patch('sat.cli.swap.main.swap_cable').start()
        self.fake_swap_switch = mock.patch('sat.cli.swap.main.swap_switch').start()
        self.fake_args = Namespace()
        set_options(self.fake_args)

    def tearDown(self):
        mock.patch.stopall()

    def test_swap_cable(self):
        """Running swap cable calls the swap cable function"""
        do_swap(self.fake_args)
        self.fake_swap_cable.assert_called_with(self.fake_args)

    def test_swap_switch(self):
        """Running swap switch calls the swap switch function"""
        self.fake_args.target = 'switch'
        do_swap(self.fake_args)
        self.fake_swap_switch.assert_called_with(self.fake_args)
