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
Class to represent a CabinetPDU object obtained from Hardware State Manager (HSM).
"""

from sat.system.component import BaseComponent
from sat.system.constants import CABINET_PDU_TYPE
from sat.system.field import ComponentField
from sat.cached_property import cached_property


class CabinetPDU(BaseComponent):
    """A Cabinet PDU in the system."""

    hsm_type = CABINET_PDU_TYPE
    arg_name = 'cabinet_pdu'
    pretty_name = 'cabinet pdu'

    fields = BaseComponent.fields + [
        ComponentField('Equipment Type'),
        ComponentField('Firmware Version')
    ]

    @cached_property
    def equipment_type(self):
        """str: the Equipment type of Cabinet PDU"""
        return self.fru_info['EquipmentType']

    @cached_property
    def firmware_version(self):
        """str: the firmware version"""
        return self.fru_info['FirmwareVersion']
