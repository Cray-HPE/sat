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
Unit tests for sat.system.cabinet_pdu_power_connector.
"""
import unittest

from sat.constants import EMPTY_VALUE
from sat.system.cabinet_pdu_power_connector import CabinetPDUPowerConnector
from tests.system.component_data import CABINET_PDU_POWER_CONNECTOR_XNAME, get_component_raw_data

NOMINAL_VOLTAGE = 'AC200V'
OUTLET_TYPE = ''
PHASE_WIRING_TYPE = 'ThreePhase4Wire'
POWER_ENABLED = 'true'
RATED_CURRENT_AMPS = 10
VOLTAGE_TYPE = 'AC'


def get_cabinet_pdu_power_connector_raw_data(xname=CABINET_PDU_POWER_CONNECTOR_XNAME, **kwargs):
    component_data = get_component_raw_data(hsm_type='Outlet', xname=xname, **kwargs)
    extra_fru_info = {
        'NominalVoltage': NOMINAL_VOLTAGE,
        'OutletType': OUTLET_TYPE,
        'PhaseWiringType': PHASE_WIRING_TYPE,
        'PowerEnabled': POWER_ENABLED,
        'RatedCurrentAmps': RATED_CURRENT_AMPS,
        'VoltageType': VOLTAGE_TYPE,
    }
    component_data['PopulatedFRU']['OutletFRUInfo'].update(extra_fru_info)
    return component_data


class TestCabinetPDUPowerConnector(unittest.TestCase):
    """Test the CabinetPDUPowerConnector class."""

    def setUp(self):
        """Create a CabinetPDUPowerConnector object to use in the tests."""
        self.raw_data = get_cabinet_pdu_power_connector_raw_data()
        self.cabinet_pdu_power_connector = CabinetPDUPowerConnector(self.raw_data)

    def test_init(self):
        """Test initialization of a CabinetPDUPowerConnector object."""
        self.assertEqual(self.raw_data, self.cabinet_pdu_power_connector.raw_data)

    def test_nominal_voltage(self):
        """Test the nominal_voltage property."""
        self.assertEqual(self.cabinet_pdu_power_connector.nominal_voltage, NOMINAL_VOLTAGE)

    def test_outlet_type(self):
        """Test the outlet_type property."""
        self.assertEqual(self.cabinet_pdu_power_connector.outlet_type, EMPTY_VALUE)

    def test_phase_wiring_type(self):
        """Test the phase_wiring_type property."""
        self.assertEqual(self.cabinet_pdu_power_connector.phase_wiring_type, PHASE_WIRING_TYPE)

    def test_power_enabled(self):
        """Test the power enabled or not in CabinetPDUPowerConnector."""
        self.assertEqual(self.cabinet_pdu_power_connector.power_enabled, POWER_ENABLED)

    def test_rated_current_amps(self):
        """Test rated current amps in CabinetPDUPowerConnector."""
        self.assertEqual(self.cabinet_pdu_power_connector.rated_current_amps, RATED_CURRENT_AMPS)

    def voltage_type(self):
        """Test the voltage_type property."""
        self.assertEqual(self.cabinet_pdu_power_connector.voltage_type, VOLTAGE_TYPE)


if __name__ == '__main__':
    unittest.main()
