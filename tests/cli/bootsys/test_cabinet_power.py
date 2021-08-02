"""
Unit tests for the sat.cli.bootsys.cabinet_power module.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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
from unittest.mock import patch

from sat.cli.bootsys.cabinet_power import do_cabinets_power_off

from tests.common import ExtendedTestCase


class TestCabinetsPowerOff(ExtendedTestCase):
    """Tests for the cabinet power off process."""
    def setUp(self):
        self.mock_liquid_cooled = patch('sat.cli.bootsys.cabinet_power.do_liquid_cooled_cabinets_power_off').start()
        self.mock_air_cooled = patch('sat.cli.bootsys.cabinet_power.do_air_cooled_cabinets_power_off').start()
        self.mock_cron_job = patch('sat.cli.bootsys.cabinet_power.HMSDiscoveryCronJob').start()
        self.mock_prompt = patch('sat.cli.bootsys.cabinet_power.prompt_continue').start()

        self.args = Namespace()
        self.args.disruptive = False

    def tearDown(self):
        patch.stopall()

    def test_do_cabinets_power_off(self):
        """Test do_cabinets_power_off() with default parameters."""
        do_cabinets_power_off(self.args)
        self.mock_prompt.assert_called_once()

        self.mock_cron_job.assert_called_once_with()
        self.mock_cron_job.return_value.set_suspend_status.assert_called_once_with(True)

        self.mock_liquid_cooled.assert_called_once_with(self.args)
        self.mock_air_cooled.assert_called_once_with(self.args)

    def test_do_cabinets_power_off_without_prompting(self):
        """Test do_cabinets_power_off() wihtout prompting to continue."""
        self.args.disruptive = True
        do_cabinets_power_off(self.args)
        self.mock_prompt.assert_not_called()

        self.mock_cron_job.assert_called_once_with()
        self.mock_cron_job.return_value.set_suspend_status.assert_called_once_with(True)

        self.mock_liquid_cooled.assert_called_once_with(self.args)
        self.mock_air_cooled.assert_called_once_with(self.args)
