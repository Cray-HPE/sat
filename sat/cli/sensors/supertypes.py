"""
Super classes of sensor classes for the sensors subcommand.

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

# deep copies of parts of json responses are made; no encounters
# with cycles, special types, or other usual gotchas.

from argparse import Namespace
from copy import deepcopy
import logging

from sat.cli.sensors.bmc import redfish_basename

LOGGER = logging.getLogger(__name__)


class SensorReading(Namespace):
    """A sensor reading

    A container for three members:
        measurement: contains three members:
            reading: the sensor's reading, resolved to a numeric type
            units: physical units, such as Volts or Celsius.
            type: what is measured, such as voltage or temperature.
        context: general metadata for the reading. Should not change over time.
        redfish: the raw response, for long-form yaml-format display
    """

    def __init__(self, rsp, measurement_def):
        super().__init__(redfish=deepcopy(rsp),
                         context=Context(rsp),
                         measurement=Measurement(rsp, measurement_def))


class Context(Namespace):
    def __init__(self, rsp):
        _parse(self, rsp, context_defs)
        super().__init__()


class Measurement(Namespace):
    def __init__(self, rsp, measurement_def):
        _parse(self, rsp, measurement_def)
        super().__init__()


def _parse(target, rsp, defs):
    for dest, pathspec in defs.items():
        if callable(pathspec):
            setattr(target, dest, pathspec(rsp))
            continue

        if pathspec.startswith('='):
            setattr(target, dest, pathspec[1:])
            continue

        path = pathspec.split('.')

        rsp_ref = rsp

        while path:
            key = path.pop(0)
            if path:
                rsp_ref = rsp_ref.get(key, {})
            else:
                value = rsp_ref.get(key, None)

                if dest == 'reading':
                    if value is None:
                        value = 'MISSING'

                    if isinstance(value, float):
                        # Mitigate floating-point display clutter. Most of the
                        # digits from the conspicuous offenders are beyond
                        # conceivable precision, anyway.
                        # Closer inspection suggests truncation after five sig-
                        # nificant figures occurs in all cases, and the extra
                        # digits, when present, are an artifact.
                        value = round(value, 4)

                setattr(target, dest, value)

    return target


# Returns None if a key is found, but the value isn't an integer.
def _parse_sensornum(rsp):

    # frequently defined, usually (not always) distinct from MemberId or @odata.id
    n = rsp.get('SensorNumber', None)

    if n is None:
        pathend = redfish_basename(rsp['@odata.id'])

        try:
            return int(pathend)
        except ValueError:
            return None

    else:
        return int(n)


# telemetry db has "parental_index" and "sub_index" but nothing seems to be in
# redfish for these, although some rows in the river table have parental_index=0
# for the baseboard temps, which don't have a redfish physicalcontext either, so
# something between redfish and postgres is filling those in!

context_defs = dict(
    device='Name',
    index='Oem.Index',
    physical='PhysicalContext',
    physicalsub='PhysicalSubContext',
    electrical='ElectricalContext',
    parental='Oem.ParentalContext',
    refdes='Oem.ReferenceDesignator',
    sensornum=_parse_sensornum
)


class SensorParserBase:
    """Base class for sensor parsers.

    This class knows how to parse a single sensor and add it to a BMC's list of
    sensor readings. Subclasses must provide a query() method that obtains the
    dict-like object, and definitions that define how to parse the object. The
    query() method should call the parse() method, which will use the defini-
    tions to construct a SensorReading object and add it to the BMC's list of
    readings.

    If no processing or additional queries are necessary, query() may simply pass
    it's arguments directly to parse(). The VoltageMarginsParser class is an ex-
    ample.

    There will always be an "initial query" that is made when the __call__ method
    is invoked. The query path is determined by the BMC instance, but an optional
    tail can be appended if defined in manner resolvable at self.query_tail. This
    has a default value as a class variable of None.

    The parse() method expects a dict-like object to be defined as class variable
    (or instance variable or property, but that will usually not be the effective
    implementation) measurement_def that has keys that will be attributes of the
    Measurement instance of the sensor reading. The values are keys into rsp, with
    some interpetation:
        multipart.path.delimited-by-dots: the path is broken into path components
            separated by dots: ".", where each component until the last is a nested
            dict-like object. For instance "foo.bar" would resolve {'foo': {'bar':
            42}} to the value 42.
        leading-equals-sign: a fixed, immediate value, no lookup, equal to the re-
            mainder of the string. For instance "=42" resolves to the string "42".
        callable:
            takes one parameter, the rsp object. Returns the value to store. For
            instance lambda dct: 8*dct['a']+2 resolves {'a': 5} to the value 42.
    """

    query_tail = None
    # exceptions raised if not defined
    measurement_def = None

    def __call__(self, bmc):
        wrapped_rsp = bmc.sensor_query(self.query_tail)

        if wrapped_rsp:
            self.query(bmc, wrapped_rsp.response)

        return wrapped_rsp

    def query(self, bmc, rsp):
        """Obtain the sensor's raw data. Must be overridden by a subclass.

        Passes the raw data to the parse() method.

        Arguments:
            bmc (BMC): The BMC that hosts the sensor data.
            rsp (Map): the JSON of the response to the initial query.

        Returns:
            Nothing
        """
        raise NotImplementedError

    def parse(self, bmc, rsp):
        """Creates a SensorReading object (which does the actual parsing) and
        adds it to a BMC's list of sensor readings.

        May be overridden to implement filters or to make changes to the re-
        sponse, for instance.

        Arguments:
            bmc (BMC): The BMC that hosts the sensor data.
            rsp (Map): the JSON of the response to the initial query.

        Returns:
            Nothing

        """

        bmc.add_sensor(SensorReading(rsp, self.measurement_def))


class MemberSensorParserBase(SensorParserBase):
    """Parses an array of sensors

    References self.member_key (defined as a class variable, for instance) from
    the initial response, then parses each element of the array obtained.
    """

    def query(self, bmc, rsp):
        if self.member_key in rsp:
            for sensor in rsp[self.member_key]:
                self.parse(bmc, sensor)
        else:
            LOGGER.info('key "%s" not found under resource "%s" of %s.',
                        self.member_key, self.query_tail, bmc.xname)
