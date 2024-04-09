#
# MIT License
#
# (C) Copyright 2020, 2024 Hewlett Packard Enterprise Development LP
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
Unit tests for sat.cli.switch
"""

import logging
import unittest
from unittest import mock

from sat.cli.switch.main import do_switch


class TestDoSwitch(unittest.TestCase):
    """Unit test for Switch do_switch()."""

    def setUp(self):
        self.mock_args = mock.Mock()
        self.mock_swap_switch = mock.patch('sat.cli.switch.main.swap_switch').start()
        self.mock_pester_choices = mock.patch('sat.util.pester_choices').start()
        self.mock_pester_choices.return_value = 'yes'

    def test_do_switch(self):
        """do_switch should call swap_switch with a deprecation warning and prompt"""
        with self.assertLogs(level=logging.WARNING) as logs_cm:
            do_switch(self.mock_args)

        self.mock_swap_switch.assert_called_with(self.mock_args)
        self.assertEqual(1, len(logs_cm.records))
        self.assertRegex(logs_cm.records[0].message,
                         'The "sat switch" command has been deprecated')

    def test_do_switch_abort(self):
        """do_switch should abort when user answers 'no' to prompt"""
        self.mock_pester_choices.return_value = 'no'

        with self.assertRaises(SystemExit) as raises_cm:
            with self.assertLogs(level=logging.WARNING) as logs_cm:
                do_switch(self.mock_args)

        self.mock_swap_switch.assert_not_called()
        self.assertEqual(1, len(logs_cm.records))
        self.assertRegex(logs_cm.records[0].message,
                         'The "sat switch" command has been deprecated')
        self.assertEqual(1, raises_cm.exception.code)


if __name__ == '__main__':
    unittest.main()
