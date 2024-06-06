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
Unit tests for sat.system.cabinet_pdu.
"""
import unittest

from sat.constants import EMPTY_VALUE
from sat.system.cabinet_pdu import CabinetPDU
from tests.system.component_data import CABINET_PDU_XNAME, get_component_raw_data

EQUIPMENT_TYPE = ''
FIRMWARE_VERSION = '1.2.3'


def get_cabinet_pdu_raw_data(xname=CABINET_PDU_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='PDU', xname=xname, **kwargs)
    extra_fru_info = {
        'EquipmentType': EQUIPMENT_TYPE,
        'FirmwareVersion': FIRMWARE_VERSION,
    }
    component_data['PopulatedFRU']['PDUFRUInfo'].update(extra_fru_info)
    return component_data


class TestCabinetPDU(unittest.TestCase):
    """Test the CabinetPDU class."""

    def setUp(self):
        """Create a CabinetPDU object to use in the tests."""
        self.raw_data = get_cabinet_pdu_raw_data()
        self.cabinet_pdu = CabinetPDU(self.raw_data)

    def test_init(self):
        """Test initialization of a CabinetPDU object."""
        self.assertEqual(self.raw_data, self.cabinet_pdu.raw_data)

    def test_equipment_type(self):
        """Test the equipment_type property."""
        self.assertEqual(self.cabinet_pdu.equipment_type, EMPTY_VALUE)

    def test_firmware_version(self):
        """Test the firmware_version property."""
        self.assertEqual(self.cabinet_pdu.firmware_version, FIRMWARE_VERSION)


if __name__ == '__main__':
    unittest.main()
