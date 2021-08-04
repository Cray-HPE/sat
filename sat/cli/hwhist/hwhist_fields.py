"""
Contains structures and code for fields that are displayed by the hwhist subcommand.

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


# Fields that are displayed for hardware component history by location (xname)
XNAME_FIELD = [
    ('xname', lambda event: XName(event.get('ID', MISSING_VALUE)))
]
FRUID_FIELD = [
    ('FRUID', lambda event: event.get('FRUID', MISSING_VALUE))
]
COMMON_FIELDS = [
    ('Timestamp', lambda event: event.get('Timestamp', MISSING_VALUE)),
    ('EventType', lambda event: event.get('EventType', MISSING_VALUE))
]
BY_LOCATION_FIELDS = XNAME_FIELD + FRUID_FIELD + COMMON_FIELDS
BY_FRU_FIELDS = FRUID_FIELD + XNAME_FIELD + COMMON_FIELDS

BY_LOCATION_FIELD_MAPPING = OrderedDict(BY_LOCATION_FIELDS)
BY_FRU_FIELD_MAPPING = OrderedDict(BY_FRU_FIELDS)
