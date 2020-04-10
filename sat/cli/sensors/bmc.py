"""
BMC classes for the sensors subcommand.

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

from collections.abc import Mapping
from argparse import Namespace
from enum import Enum

import requests
import logging
import json
import re

# TODO: This is very bad practice, but we need it for now. See: SAT-140.
import urllib3
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

LOGGER = logging.getLogger(__name__)


def redfish_basename(path):
    return path.split('/')[-1]


# CHASSIS: not typically seen on River, but doesn't seem to be excluded,
# according to the Shasta HSS Naming Convention document.

# SWITCH: may be either cabinet type
# RIVER: River node
# NODE: Mountain node

class BMCType(Enum):
    CHASSIS = object()
    SWITCH = object()
    RIVER = object()
    NODE = object()


# Only UNKNOWN affects execution, but the rest are helpful in log entries.
class RiverType(Enum):
    RACKMOUNT = object()
    BASEBOARD = object()
    UNKNOWN = object()
    SELF = object()


class SwitchType(Enum):
    MARGINS = object()
    NO_MARGINS = object()


class ResponseStatus(Enum):
    OKAY = object()
    HTTP_ERR = object()
    PARSE_ERR = object()
    REDFISH_ERR = object()
    CONNECTION_ERR = object()


# Skip the heuristics if the node type and subtype can be inferred from the xname.
CHASSIS_REGEX = re.compile(r'x\d{1,4}c\db\d+$')
SWITCH_REGEX = re.compile(r'x\d{1,4}c\dr\d{1,2}b\d+$')

# Conditional: a Mountain node may be detected if the chassis number is greater than zero.
NODE_REGEX = re.compile(r'x\d{1,4}c(\d)s\d{1,2}b\d+$')


class WrappedResponse(Namespace):
    def __init__(self, status):
        super().__init__(status=status, logged=False, response=None)

    def __bool__(self):
        return self.status is ResponseStatus.OKAY


class BMC:
    """BMC class. Detects BMC type at initialization, and handles Redfish queries.
    """

    def __init__(self, xname, username, password):
        self.xname = xname
        self.username = username
        self.password = password
        self.sensors = []

        self.type = None
        self.sub_type = None
        self.query_head = None
        self.already_logged = False

        self._query_cache = {}

        self.requester = requests.Session()
        self.requester.auth = (username, password)

    def detect_type(self):
        # Can detect chassis and switch BMCs by xname, and Mountain node BMCs
        # if chassis>0, but unsatisfying heuristics are necessary if the xname
        # is not used or ambiguous, as with NodeBMCs with chassis=0.

        # Xname detections are additionally queried to eliminate false positives.
        # The query is reused if successful, so no overhead is incurred. Ideally,
        # it prevents pointless future queries.

        # River nodes are heterogeneous, but mainly in the query path, making the
        # required heuristics less arbitrary. A subset of sensors may be present,
        # but extra queries should be avoided since the omissions observed have
        # always occurred within a response that was already queried for a set
        # of sensors more reliably present.

        xname = self.xname

        m = NODE_REGEX.match(xname)

        if m and int(m.group(1)) > 0:
            if self.redfish_query('Chassis/Enclosure'):
                self.type = BMCType.NODE
                self.query_head = 'Enclosure'

        elif CHASSIS_REGEX.match(xname):
            if self.redfish_query('Chassis/Enclosure'):
                self.type = BMCType.CHASSIS
                self.query_head = 'Enclosure'

        elif SWITCH_REGEX.match(xname):
            if self.redfish_query('Chassis/Enclosure'):
                self.type = BMCType.SWITCH
                self.query_head = 'Enclosure'

        else:
            wrapped_rsp = self.redfish_query('Chassis')

            if wrapped_rsp:
                rsp = wrapped_rsp.response

                paths_next = tuple([redfish_basename(i['@odata.id']) for i in rsp['Members']])

                if 'Enclosure' in paths_next:
                    self.query_head = 'Enclosure'

                    rsp = self.redfish_query('Chassis/Enclosure').response

                    n = len(rsp['Actions']['#Chassis.Reset']['ResetType@Redfish.AllowableValues'])

                    if n == 0:
                        self.type = BMCType.NODE
                    elif n == 3:
                        self.type = BMCType.CHASSIS
                    else:
                        self.type = BMCType.SWITCH

                else:
                    self.type = BMCType.RIVER

                    if 'Self' in paths_next:
                        self.query_head = 'Self'
                        self.sub_type = RiverType.SELF

                    elif 'Unknown' in paths_next:
                        # A "known" unknown, so don't log as undetected type.
                        self.sub_type = RiverType.UNKNOWN

                    elif 'RackMount' in paths_next:
                        self.query_head = 'RackMount/Baseboard'
                        self.sub_type = RiverType.RACKMOUNT

                    elif 'Baseboard' in paths_next:
                        self.query_head = 'Baseboard'
                        self.sub_type = RiverType.BASEBOARD

                    else:
                        self.type = None

        if self.type is BMCType.SWITCH:
            rsp = self.redfish_query('Chassis/Enclosure').response

            # This detection will prevent unnecessary network traffic later.
            if 'Oem' in rsp and 'CrayVoltageMargins' in rsp['Oem']:
                self.sub_type = SwitchType.MARGINS
            else:
                self.sub_type = SwitchType.NO_MARGINS

        if self:
            LOGGER.info('Sensor query of %s; detected type, subtype: %s, %s',
                        xname, self.type, self.sub_type)

        elif not self.already_logged:
            LOGGER.error('Unable to identify %s.', xname)

    def add_sensor(self, sensor):
        """Stores a sensor reading.

        Arguments:
            sensor (Sensor): an instance of the Sensor class.

        Returns:
            Nothing.
        """

        self.sensors.append(sensor)

    def dump(self, f, **kwargs):
        """Dumps the query cache to a file-like object.

        JSON-formatted. Optional metadata may be included.

        Arguments:
            f (file object): a writable file-like object.
            **kwargs: extra keyword arguments are passed to json.dump().

        Returns:
            Nothing.
        """

        json.dump(dict(version=1,
                       payload={k: v.response for k, v in self._query_cache.items()}), f)

    def load(self, f, **kwargs):
        """Loads the query cache from a file-like object.

        No validation is performed, except to confirm the general format is correct;
        corrupted data may cause undefined subsequent behavior.

        Arguments:
            f (file object): a readable file-like object.
            **kwargs: extra keyword arguments are passed to json.load().

        Raises:
            JSONDecodeError if not valid JSON, and any OS or filesystem related
            exceptions that apply to the provided object.
        """

        dct = json.load(f, **kwargs)

        version = dct.get('version', None)
        payload = dct.get('payload', None)

        if payload is None:
            LOGGER.error('Unable to load: unrecognized format.')
        else:
            if isinstance(payload, Mapping):
                items = []
                for req, rsp in payload.items():
                    wrapped_rsp = WrappedResponse(ResponseStatus.OKAY)
                    wrapped_rsp.response = rsp
                    items.append((req, wrapped_rsp))

                self._query_cache = dict(items)

                LOGGER.info('Successfully loaded query cache, version %s.', version)

            else:
                LOGGER.error('Unable to load: payload was not a mapping.')

    def __bool__(self):
        """Object's boolean value, as when tested in a conditional statement.

        Returns:
            True if BMC type detection has completed successfully.
        """

        return self.type is not None

    def sensor_query(self, query_tail, **kwargs):
        """Execute a sensors-aware Redfish query.

        Arguments:
            query_tail (str): path to Redfish resource, from the query head determined
            at initialization.

            **kwargs: extra keyword arguments are passed to json.load().

        Returns:
            A WrappedResponse object
        """

        return self.redfish_query('Chassis/' + self.query_head + (
            ('/' + query_tail) if query_tail else ''), **kwargs)

    def redfish_query(self, path, **kwargs):
        """Execute a Redfish query.

        Arguments:
            path (str): path to Redfish resource, from /redfish/v1/.

            **kwargs: extra keyword arguments are passed to json.load().

        Returns:
            A WrappedResponse object
        """

        return self.raw_query('redfish/v1/' + path, **kwargs)

    def raw_query(self, path, **kwargs):
        """Execute a direct query.

        Results are cached to avoid unnecessary network traffic. The requests
        Response object is wrapped in a class that facilitates error handling.

        The main purpose of this handling is to distinguish connection failures
        from errors that do not preclude the success of a different query.

        Arguments:
            path (str): path to Redfish resource, from /.

            **kwargs: extra keyword arguments are passed to json.load().

        Returns:
            A WrappedResponse object
        """

        while '//' in path:
            path = path.replace('//', '/')

        if path.startswith('/'):
            path = path[1:]

        url = 'https://{}/{}'.format(self.xname, path)

        path_key = path[len('redfish/v1/'):]

        cache = self._query_cache

        if path_key in cache:
            wrapped_rsp = cache[path_key]

            if not wrapped_rsp.logged:
                # If the query cache is loaded, log the first time a path is queried, so logs can be compared.
                # A better message is needed (and the attendant increased sophistication of replay to capture
                # matching), but this should only occur during testing or demonstrations.
                LOGGER.debug('Redfish Query: %s', url)
                wrapped_rsp.logged = True

        else:
            LOGGER.debug('Redfish Query: %s', url)

            try:
                requests_rsp = self.requester.get(url, verify=False)

            except requests.exceptions.RequestException as err:
                msg = 'Redfish query to {} responded with request error: '.format(self.xname)
                wrapped_rsp = WrappedResponse(ResponseStatus.CONNECTION_ERR)

                # Cleans up the message a bit if it's a yucky chain of messages, which urllib3
                # likes to foist upon us.
                if hasattr(err.args[0], 'reason'):
                    err = err.args[0].reason

                LOGGER.error(msg + str(err))
                self.already_logged = True

            else:
                if not requests_rsp:
                    # occurs when http response status >= 400
                    msg = 'Redfish query to {} responded with HTTP error ({:d}): {}'.format(
                        self.xname, requests_rsp.status_code, requests_rsp.reason)
                    wrapped_rsp = WrappedResponse(ResponseStatus.HTTP_ERR)
                    wrapped_rsp.response = requests_rsp

                    LOGGER.error(msg)
                    self.already_logged = True

                else:
                    try:
                        rsp = requests_rsp.json(**kwargs)
                    except json.decoder.JSONDecodeError:
                        LOGGER.error('Unable to parse response to Redfish query to %s: %s',
                                     self.xname, requests_rsp.text)
                        wrapped_rsp = WrappedResponse(ResponseStatus.PARSE_ERR)
                        wrapped_rsp.response = requests_rsp
                    else:
                        if 'error' in rsp:
                            msg = 'Redfish query to {} responded with Redfish error: {}'.format(
                                self.xname, rsp['error']['message'])
                            wrapped_rsp = WrappedResponse(ResponseStatus.REDFISH_ERR)
                            wrapped_rsp.response = rsp

                            LOGGER.error(msg)
                            self.already_logged = True
                        else:
                            wrapped_rsp = WrappedResponse(ResponseStatus.OKAY)
                            wrapped_rsp.response = rsp
                            wrapped_rsp.logged = True

                            cache[path_key] = wrapped_rsp

        return wrapped_rsp
