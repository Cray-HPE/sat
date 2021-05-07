"""
Contains structures and code for fields that are displayed by the sensors subcommand.

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

from collections import OrderedDict

from sat.constants import MISSING_VALUE
from sat.xname import XName


def sensor_getter(key):
    """Return a function that extracts a key value from a sensor reading.

    Args:
        key (str): the key to extract from the sensor reading

    Returns:
        A function that takes three arguments of type dict, where the third
        argument is the dict containing the sensor reading values. The function
        returns the value of the key named `key` from that dict, defaulting to
        `MISSING_VALUE` if the `key` is missing.
    """

    return lambda topic, metric, sensor: sensor.get(key, MISSING_VALUE)


# Fields that are displayed for each sensor
GLOBAL_FIELDS = [
    ('xname', lambda topic, metric, sensor: XName(metric.get('Context', MISSING_VALUE))),
    ('Type', lambda topic, metric, sensor: metric.get('Type', MISSING_VALUE)),
    ('Topic', lambda topic, metric, sensor: topic.get('Topic', MISSING_VALUE)),
    ('Timestamp', sensor_getter('Timestamp'))
]

# Fields that uniquely identify a sensor
UNIQUE_SENSOR_FIELDS = [
    ('Location', sensor_getter('Location')),
    ('Parental Context', sensor_getter('ParentalContext')),
    ('Parental Index', sensor_getter('ParentalIndex')),
    ('Physical Context', sensor_getter('PhysicalContext')),
    ('Index', sensor_getter('Index')),
    ('Physical Subcontext', sensor_getter('PhysicalSubContext')),
    ('Device Specific Context', sensor_getter('DeviceSpecificContext')),
    ('Subindex', sensor_getter('SubIndex'))
]

# Field that contains the sensor reading
SENSOR_VALUE_FIELD = [
    ('Value', sensor_getter('Value'))
]

# All fields that are displayed by the subcommand
ALL_FIELDS = GLOBAL_FIELDS + UNIQUE_SENSOR_FIELDS + SENSOR_VALUE_FIELD

UNIQUE_SENSOR_FIELD_MAPPING = OrderedDict(UNIQUE_SENSOR_FIELDS)

FIELD_MAPPING = OrderedDict(ALL_FIELDS)
