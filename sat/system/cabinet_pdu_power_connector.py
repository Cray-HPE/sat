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
Class to represent a CabinetPDUPowerConnector object obtained from Hardware State Manager (HSM).
"""

from sat.system.component import BaseComponent
from sat.system.constants import CABINET_PDU_POWER_CONNECTOR_TYPE
from sat.system.field import ComponentField
from sat.cached_property import cached_property


class CabinetPDUPowerConnector(BaseComponent):
    """A Cabinet PDU Power Connector in the system."""

    hsm_type = CABINET_PDU_POWER_CONNECTOR_TYPE
    arg_name = 'cabinet_pdu_power_connector'
    pretty_name = 'cabinet pdu power connector'

    fields = BaseComponent.fields + [
        ComponentField('Nominal Voltage'),
        ComponentField('Outlet Type'),
        ComponentField('Phase Wiring Type'),
        ComponentField('Power Enabled'),
        ComponentField('Rated Current Amps'),
        ComponentField('Voltage Type')
    ]

    @cached_property
    def nominal_voltage(self):
        """str: the Nominal Voltage of Cabinet PDU Power Connector"""
        return self.fru_info['NominalVoltage']

    @cached_property
    def outlet_type(self):
        """str: the Outlet type of Cabinet PDU Power Connector"""
        return self.fru_info['OutletType']

    @cached_property
    def phase_wiring_type(self):
        """str: the Phase Wiring type of Cabinet PDU Power Connector"""
        return self.fru_info['PhaseWiringType']

    @cached_property
    def power_enabled(self):
        """str: the Power Enabled or not in Cabinet PDU Power Connector"""
        return self.fru_info['PowerEnabled']

    @cached_property
    def rated_current_amps(self):
        """str: the Rated Current in Amps for Cabinet PDU Power Connector"""
        return self.fru_info['RatedCurrentAmps']

    @cached_property
    def voltage_type(self):
        """str: the Voltage type of Cabinet PDU Power Connector"""
        return self.fru_info['VoltageType']
