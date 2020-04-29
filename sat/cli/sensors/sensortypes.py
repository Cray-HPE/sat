"""
Sensor classes for the sensors subcommand.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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

from sat.cli.sensors.supertypes import SensorParserBase, MemberSensorParserBase
from sat.cli.sensors.bmc import BMCType, redfish_basename


class SensorsParser(SensorParserBase):
    """A Redfish collection (array of references) of sensors.

    The initial response contains reference to each sensor as a distinct Redfish
    resource. Reading the sensor is an additional network query, so duplicates
    are ignored. Duplicates only occur with Mountain node BMCs.

    A sensor is counted as a duplicate if its sensor number has already been read
    successfully (not missing). This also implies that the sensor number is
    defined (not None).

    For this optimization to work, this parser should be called after the other
    parsers for the BMC.
    """

    query_tail = 'Sensors'

    measurement_def = dict(
        type='ReadingType',
        units='ReadingUnits',
        reading='Reading'
    )

    def query(self, bmc, rsp):
        acquired_sensors = set()

        if bmc.type is BMCType.NODE:
            for sensor in bmc.sensors:
                if sensor.context.sensornum is not None:
                    if sensor.measurement.reading != 'MISSING':
                        acquired_sensors.add(sensor.context.sensornum)

        for member in rsp['Members']:
            sensor_path = member['@odata.id']
            if redfish_basename(sensor_path) not in acquired_sensors:
                self.parse(bmc, bmc.raw_query(sensor_path).response)


class VoltageMarginsParser(SensorParserBase):
    """Single, direct reading. Only found hosted on switch controllers, HSM type
    RouterBMC.
    """

    query_tail = 'Oem/CrayVoltageMargins/VDD'

    measurement_def = dict(
        type='ReadingType',
        units='ReadingUnits',
        reading='VDD 0v85 S0 Voltage Output'
    )

    def query(self, bmc, rsp):
        self.parse(bmc, rsp)


class TemperaturesParser(MemberSensorParserBase):
    query_tail = 'Thermal'
    member_key = 'Temperatures'

    measurement_def = dict(
        type='=Temperature',
        units='=Cel',
        reading='ReadingCelsius')


class VoltagesParser(MemberSensorParserBase):
    query_tail = 'Power'
    member_key = 'Voltages'

    measurement_def = dict(
        type='=Voltage',
        units='=V',
        reading='ReadingVolts')


class FansParser(MemberSensorParserBase):
    query_tail = 'Thermal'
    member_key = 'Fans'

    measurement_def = dict(
        type='=AngularVel',
        units='ReadingUnits',
        reading='Reading')


class PowerSuppliesParser(MemberSensorParserBase):
    query_tail = 'Power'
    member_key = 'PowerSupplies'

    measurement_def = dict(
        type='=Voltage',
        units='=V',
        reading='LineInputVoltage')
