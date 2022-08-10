#
# MIT License
#
# (C) Copyright 2020-2022 Hewlett Packard Enterprise Development LP
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

import itertools
import unittest
from unittest import mock
from argparse import Namespace

from sat.cli.swap.main import check_arguments, do_swap


def check_arguments_base():
    options = {
        'component_type': ['blade', 'switch', 'cable'],
        'action': ['enable', 'disable', None],
        'dry_run': [True, False],
        'disruptive': [True, False],
        'pester': [True, False]
    }
    methods = {}

    for product in itertools.product(*options.values()):
        annotated_product = dict(zip(options.keys(), product))
        method_name = '_'.join(f'{k}_{str(v).lower()}' for k, v in annotated_product.items())

        def inner_test_method(self):
            (component_type, action, dry_run, disruptive, pester_value) = product
            self.mock_pester.return_value = pester_value
            should_fail = (
                not dry_run and not action or
                dry_run and action or
                (not disruptive and not dry_run and not pester_value)
            )
            if should_fail:
                with self.assertRaises(SystemExit):
                    check_arguments(component_type, action, dry_run, disruptive)
            else:
                check_arguments(component_type, action, dry_run, disruptive)

        inner_test_method.__doc__ = \
            f"Test check_arguments for {', '.join(f'{k}={str(v).lower()}' for k, v in annotated_product.items())}"
        methods[method_name] = inner_test_method

    cls = type('CheckArgumentsBase', (unittest.TestCase,), methods)
    return cls


class TestCheckArguments(check_arguments_base()):
    def setUp(self):
        self.mock_pester = mock.patch('sat.cli.swap.main.pester', return_value=True).start()

    def tearDown(self):
        mock.patch.stopall()


class TestSwapMain(unittest.TestCase):

    def setUp(self):
        self.fake_swap_cable = mock.patch('sat.cli.swap.main.swap_cable').start()
        self.fake_swap_switch = mock.patch('sat.cli.swap.main.swap_switch').start()
        self.fake_args = Namespace(
            action='enable',
            dry_run=False,
            disruptive=True,
            target='cable',
        )

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
