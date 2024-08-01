#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
Class to represent a MgmtSwitch object obtained from Hardware State Manager (HSM).
"""

from sat.system.component import BaseComponent
from sat.system.constants import MGMT_SWITCH_TYPE
from sat.system.field import ComponentField
from sat.cached_property import cached_property


class MgmtSwitch(BaseComponent):
    """A mgmt switch in the system."""

    hsm_type = MGMT_SWITCH_TYPE
    arg_name = 'mgmt_switch'
    pretty_name = 'mgmt switch'

    fields = BaseComponent.fields + [
        ComponentField('Chassis Type')
    ]

    @cached_property
    def chassis_type(self):
        """str: the type of Chassis"""
        return self.fru_info['ChassisType']
