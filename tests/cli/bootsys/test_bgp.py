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
Unit tests for the sat.cli.bootsys.bgp module.
"""

from textwrap import dedent
import unittest
from unittest.mock import patch

from sat.cli.bootsys.bgp import BGPSpineStatusWaiter


class TestBGPSpineStatusWaiter(unittest.TestCase):
    """Tests for the spine BGP status waiting functionality."""

    # TODO: Once automation formerly provided by Ansible playbook is implemented,
    # update the format of this output to reflect the output of the new tooling.
    INCOMPLETE_OUTPUT = dedent("""\
    PLAY [spines_mtl]
    ****************************************************************************************************

    TASK [Check the BGP status on spine switches commands=['enable', 'show ip bgp summary']]
    ****************************
    Tuesday 14 April 2020  09:23:02 -0500 (0:00:00.056)       0:00:00.056 *********
    fatal: [sw-spine02-mtl]: FAILED! =>
      msg: '[Errno None] Unable to connect to port 22 on 10.1.0.3'
    ok: [sw-spine01-mtl]

    TASK [debug msg={{ result.stdout[1] }}]
    ******************************************************************************
    Tuesday 14 April 2020  09:23:07 -0500 (0:00:05.331)       0:00:05.387 *********
    ok: [sw-spine01-mtl] =>
      msg: |-
        VRF name                  : default
        BGP router identifier     : 10.252.0.1
        local AS number           : 65533
        BGP table version         : 7
        Main routing table version: 7
        IPV4 Prefixes             : 34
        IPV6 Prefixes             : 0
        L2VPN EVPN Prefixes       : 0
    ------------------------------------------------------------------------------------------------------------------
        Neighbor          V    AS           MsgRcvd   MsgSent   TblVer    InQ    OutQ   Up/Down       State/PfxRcd
    ------------------------------------------------------------------------------------------------------------------
        10.252.0.4        4    65533        3         2         7         0      0      Never         IDLE/0
        10.252.0.5        4    65533        14317     16436     7         0      0      4:23:08:24    ESTABLISHED/17
        10.252.0.6        4    65533        14317     16452     7         0      0      4:23:08:24    ESTABLISHED/17

    PLAY RECAP
    ************************************************************************************************************
    sw-spine01-mtl             : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
    sw-spine02-mtl             : ok=0    changed=0    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0

    Tuesday 14 April 2020  09:23:08 -0500 (0:00:00.480)       0:00:05.868 *********
    ===============================================================================
    Check the BGP status on spine switches ------------------------------------------------------------------- 5.33s
    debug ---------------------------------------------------------------------------------------------------- 0.48s
    Playbook run took 0 days, 0 hours, 0 minutes, 5 seconds
    """)

    # TODO: Once automation formerly provided by Ansible playbook is implemented,
    # update the format of this output to reflect the output of the new tooling.
    COMPLETE_OUTPUT = dedent("""\
    PLAY [spines_mtl]
    ****************************************************************************************************

    TASK [Check the BGP status on spine switches commands=['enable', 'show ip bgp summary']]
    ****************************
    Tuesday 14 April 2020  09:23:02 -0500 (0:00:00.056)       0:00:00.056 *********
    fatal: [sw-spine02-mtl]: FAILED! =>
      msg: '[Errno None] Unable to connect to port 22 on 10.1.0.3'
    ok: [sw-spine01-mtl]

    TASK [debug msg={{ result.stdout[1] }}]
    ******************************************************************************
    Tuesday 14 April 2020  09:23:07 -0500 (0:00:05.331)       0:00:05.387 *********
    ok: [sw-spine01-mtl] =>
      msg: |-
        VRF name                  : default
        BGP router identifier     : 10.252.0.1
        local AS number           : 65533
        BGP table version         : 7
        Main routing table version: 7
        IPV4 Prefixes             : 34
        IPV6 Prefixes             : 0
        L2VPN EVPN Prefixes       : 0
    ------------------------------------------------------------------------------------------------------------------
        Neighbor          V    AS           MsgRcvd   MsgSent   TblVer    InQ    OutQ   Up/Down       State/PfxRcd
    ------------------------------------------------------------------------------------------------------------------
        10.252.0.4        4    65533        14317     16436     7         0      0      4:23:08:24    ESTABLISHED/17
        10.252.0.5        4    65533        14317     16436     7         0      0      4:23:08:24    ESTABLISHED/17
        10.252.0.6        4    65533        14317     16452     7         0      0      4:23:08:24    ESTABLISHED/17

    PLAY RECAP
    ************************************************************************************************************
    sw-spine01-mtl             : ok=2    changed=0    unreachable=0    failed=0    skipped=0    rescued=0    ignored=0
    sw-spine02-mtl             : ok=0    changed=0    unreachable=0    failed=1    skipped=0    rescued=0    ignored=0

    Tuesday 14 April 2020  09:23:08 -0500 (0:00:00.480)       0:00:05.868 *********
    ===============================================================================
    Check the BGP status on spine switches ------------------------------------------------------------------- 5.33s
    debug ---------------------------------------------------------------------------------------------------- 0.48s
    Playbook run took 0 days, 0 hours, 0 minutes, 5 seconds
    """)

    def test_spine_bgp_established(self):
        """Test if established BGP peers are recognized."""
        self.assertTrue(BGPSpineStatusWaiter.all_established(self.COMPLETE_OUTPUT))

    def test_spine_bgp_idle(self):
        """Test if idle BGP peers are detected."""
        self.assertFalse(BGPSpineStatusWaiter.all_established(self.INCOMPLETE_OUTPUT))

    # TODO: Once new automation for getting spine status is implemented, update this test
    def test_get_spine_status(self):
        """Test the get_spine_status helper function."""
        with self.assertRaises(NotImplementedError):
            BGPSpineStatusWaiter.get_spine_status()

    @patch('sat.cli.bootsys.bgp.BGPSpineStatusWaiter.get_spine_status')
    def test_completion_successful(self, mock_spine_status):
        """Test the BGP waiter when the BGP peers have been established."""
        mock_spine_status.return_value = self.COMPLETE_OUTPUT
        self.assertTrue(BGPSpineStatusWaiter(10).has_completed())

    @patch('sat.cli.bootsys.bgp.BGPSpineStatusWaiter.get_spine_status')
    def test_waiting_for_bgp_completion(self, mock_spine_status):
        """Test waiting for successful BGP peering"""
        mock_spine_status.return_value = self.COMPLETE_OUTPUT
        spine_waiter = BGPSpineStatusWaiter(10)
        self.assertTrue(spine_waiter.wait_for_completion())
