"""
Client for querying the API gateway.

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
import json
import logging
import time
from datetime import datetime, timedelta

from sat.apiclient import APIGatewayClient, APIError
from sat.xname import XName


LOGGER = logging.getLogger(__name__)


def _now_and_later(minutes):
    """Return now and now + minutes as a pair

    Returns:
        now, later: datetime pair.
    """
    now = datetime.utcnow().replace(microsecond=0)
    later = now + timedelta(minutes=minutes)
    return now, later


class _DateTimeEncoder(json.JSONEncoder):
    """For encoding datetimes in JSON compatible with the FAS.

    Only works with times in UTC.
    """
    def default(self, o):
        if isinstance(o, datetime):
            return o.isoformat() + 'Z'

        return json.JSONEncoder.default(self, o)


class _FirmwareClient(APIGatewayClient):
    """Defines the interface for FASClient and FUSClient.
    """
    def get_all_snapshot_names(self):
        raise NotImplementedError

    def get_snapshot(self, name):
        raise NotImplementedError

    def get_snapshots(self, names):
        raise NotImplementedError

    def get_device_firmwares(self, xname=None):
        raise NotImplementedError

    def make_fw_table(self, fw_devs):
        raise NotImplementedError

    def get_updates(self):
        raise NotImplementedError

    def get_active_updates(self):
        raise NotImplementedError

    def _make_fw_table(self, fw_devs, name, version):
        """For creating rows to be fed into a Report.

        Meant to be called by the FASClient and FUSClient subclasses.

        Args:
            fw_devs (list): A list of dictionaries with xnames and their
                firmware elements and versions. See the FASClient and
                FUSClient docstrings for what format this should take.

            name, version: The FUS and FAS have different key-names for
                the 'name' and 'version' fields within the payload.

                FUS: 'id', 'version'
                FAS: 'name', 'firmwareVersion'

        Returns:
            A list-of-lists table of strings, each row representing
            the firmware version for an xname and ID.
        """
        fw_table = []
        for fw_dev in fw_devs:
            if 'xname' not in fw_dev:
                LOGGER.error('Missing xname key.')
                continue

            xname = fw_dev['xname']
            if 'targets' in fw_dev and fw_dev['targets'] is not None:
                targets = fw_dev['targets']
                for target in targets:
                    if 'error' in target:
                        LOGGER.error('Error getting firmware for %s ID %s: %s', xname,
                                     target.get(name, 'MISSING'), target['error'])
                        # Fall through to show version only if ID and version values exist.
                        if name not in target or version not in target:
                            continue
                    # Use XName class so xnames sort properly.
                    fw_table.append([XName(xname), target.get(name, 'MISSING'),
                                     target.get(version, 'MISSING')])

            elif 'error' in fw_dev:
                LOGGER.error('Error getting firmware for %s: %s', xname, fw_dev['error'])
            else:
                # It is unclear whether this can actually occur.
                LOGGER.warning('No firmware found for: %s', xname)

        return fw_table


# Should have the same interface as FUSClient
class FASClient(_FirmwareClient):
    base_resource_path = 'fw-action/v1/'

    def get_updates(self):
        """Get a list of all the firmware updates on the system.

        Returns:
            A list of dicts representing firmware updates on the system.

        Raises:
            APIError: if request to get updates from FAS fails
        """
        try:
            return self.get('actions').json()['actions']
        except ValueError as err:
            raise APIError('Unable to parse json in response from FAS: '
                           '{}'.format(err))
        except KeyError as err:
            raise APIError("No 'actions' key in response from FAS.")

    def get_active_updates(self):
        """Get a list of all the active firmware updates on the system.

        Returns:
            A list of dicts representing active firmware updates on the system.

        Raises:
            APIError: if request to get updates from FAS fails
        """
        return [update for update in self.get_updates()
                if update.get('state') not in ('aborted', 'completed')]

    def get_all_snapshot_names(self):
        """Return all snapshot names available in the FAS.

        Returns:
            A list of snapshot names.

        Raises:
            APIError: - If querying the FAS failed.
                      - The payload did not contain a 'snapshots' entry.
                      - The payload was invalid JSON.
        """
        try:
            response = self.get('snapshots')
        except APIError as err:
            raise APIError('Contacting the FW API: {}'.format(err))

        try:
            response = response.json()
        except ValueError as err:
            raise APIError('The JSON payload was invalid.'.format(err))

        try:
            snapshots = response['snapshots']
        except KeyError:
            raise APIError('The payload was missing an entry for "snapshots".')

        return set([x['name'] for x in snapshots])

    def get_snapshot(self, name):
        """Describe data from a particular snapshot.

        The output from this function can be passed to make_fw_table.

        Args:
            name: Snapshot name.

        Returns:
            List of dicts that can be passed to make_fw_table.

        Raises:
            APIError: - The firmware api could not be queried.
                      - The payload did not contain a 'devices' entry.
                      - The payload was invalid JSON.
        """
        try:
            response = self.get('snapshots', name)
        except APIError as err:
            raise APIError('Contacting the FAS for snapshot "{}": {}'.format(name, err))

        try:
            response = response.json()
        except ValueError as err:
            raise APIError('The JSON payload from snapshot "{}" was invalid: {}'.format(name, err))

        try:
            devices = response['devices']
        except KeyError:
            raise APIError('The payload from snapshot "{}" was missing a "devices" key.'.format(name))

        return devices

    def get_snapshots(self, names):
        """Describe multiple snapshots.

        If a name doesn't exist, then it isn't got.

        Args:
            names: Snapshot names to get descriptions of.

        Returns:
            A dict where the keys are the snapshot names and the values are
            the snapshots themselves. Each value may be passed to make_fw_table.

        Raises:
            APIError: - The firmware api could not be queried.
                      - The payload did not contain a 'devices' entry.
                      - The payload was invalid JSON.
        """
        descriptions = {}
        known_snaps = self.get_all_snapshot_names()

        for name in names:
            if name not in known_snaps:
                LOGGER.warning('Snapshot "{}" does not exist.'.format(name))
                continue

            descriptions[name] = self.get_snapshot(name)

        return descriptions

    def get_device_firmwares(self, xname=''):
        """Returns devices associated with a particular xname.

        Args:
            xname: Xname to get device firmware information from. If no value
                is provided, then all xnames will be queried.

        Returns:
            A list of all devices for the specified xname.

        Raises:
            APIError: If any call to the FAS failed to go through. This can also
                raise if
                    - The payload was missing either a 'ready' field while
                      polling, or a 'devices' field.
                    - If the FAS did not indicate if the snapshot was ready.
        """
        now, later = _now_and_later(10)
        name = '{}-{}-{}-{}-{}-{}-all-xnames'.format(
            now.year, now.month, now.day, now.hour, now.minute, now.second)

        # create a system snapshot set to expire in 10 minutes
        payload = {'name': name, 'expirationTime': later}

        # filter on xnames if provided.
        if xname:
            payload['stateComponentFilter'] = {'xnames': [xname]}

        payload = json.dumps(payload, cls=_DateTimeEncoder)

        try:
            self.post('snapshots', payload=payload)
        except APIError as err:
            raise APIError('Error when posting new snapshot: {}'.format(err))

        # retrieve it and poll until ready
        response = None
        ready = False
        while not ready:
            time.sleep(1)

            try:
                response = self.get('snapshots', name).json()
            except APIError as err:
                raise APIError('Error when polling the snapshot for "ready" status: {}'.format(err))
            except ValueError as err:
                raise APIError('The JSON received was invalid: {}'.format(err))

            try:
                ready = response['ready']
            except KeyError:
                raise APIError('Payload returned from GET to snapshots/name did not have "ready" field.')

        try:
            return response['devices']
        except KeyError:
            raise APIError('The JSON payload did not contain a "devices" field.')

    def make_fw_table(self, fw_devs):
        """For creating rows to be fed into a Report.

        Args:
            fw_devs (list): A list of dictionaries with xnames and their
                firmware elements and versions.

                fw_devs = [
                    {
                        xname: xname,
                        'targets': [{'version': vers, 'id': id}, ...]
                    },
                    ...
                ]

        Returns:
            A list-of-lists table of strings, each row representing
            the firmware version for an xname and ID.
        """
        return self._make_fw_table(fw_devs, 'name', 'firmwareVersion')


# Should have the same interface as FASClient
class FUSClient(_FirmwareClient):
    """Class for interacting with the FUS.
    """
    base_resource_path = 'fw-update/v1/'

    def get_updates(self):
        """Get a list of all the firmware updates on the system.

        Returns:
            A list of dicts representing firmware updates on the system.

        Raises:
            APIError: if request to get updates from FUS fails
        """
        try:
            return self.get('status').json()
        except ValueError as err:
            raise APIError('Unable to parse json in response from FUS: '
                           '{}'.format(err))

    def get_active_updates(self):
        """Get a list of all the active firmware updates on the system.

        Returns:
            A list of dicts representing active firmware updates on the system.

        Raises:
            APIError: if request to get updates from FUS fails
        """
        return [update for update in self.get_updates()
                if 'endTime' not in update]

    def get_all_snapshot_names(self):
        """Return all existing snapshots on the FUS.

        Returns:
            A set of all existing snapshot names.

        Raises:
            APIError: If the request to the FUS could not be made.
        """
        try:
            response = self.get('snapshot')
        except APIError as err:
            raise APIError('Request to FW API failed: {}'.format(err))

        try:
            response = response.json()
        except ValueError as err:
            raise APIError('The JSON payload was invalid: {}'.format(err))

        try:
            snapshots = response['snapshots']
        except KeyError:
            raise APIError('The payload was missing an entry for "snapshots".')

        return set([x['name'] for x in snapshots])

    def get_snapshot(self, name):
        """Get data from a particular snapshot.

        The output from this function can be passed to make_fw_table.

        Be careful - a snapshot of the matching name will be created if it
        doesn't exist.

        Args:
            name: Snapshot name.

        Returns:
            List of dicts that can be passed to make_fw_table.

        Raises:
            APIError: - The firmware api could not be queried.
                      - The payload received was invalid JSON.
                      - The payload was missing a 'devices' entry.
        """
        try:
            response = self.get('snapshot', name)
        except APIError as err:
            raise APIError('Request to firmware API failed for snapshot "{}": {}'.format(name, err))

        try:
            response = response.json()
        except ValueError as err:
            raise APIError('The JSON payload was invalid for snapshot "{}": {}'.format(name, err))

        try:
            devices = response['devices']
        except KeyError:
            raise APIError('The payload from snapshot "{}" was missing an entry for "devices".'.format(name))

        return devices

    def get_snapshots(self, names):
        """Get multiple snapshots.

        If a name doesn't exist, then it isn't retrieved, nor is it created.

        Args:
            names: Snapshot names to get descriptions of.

        Returns:
            A dict where the keys are the snapshot names and the values are
            the snapshots themselves. Each value may be passed to make_fw_table.

        Raises:
            APIError: - The firmware api could not be queried.
                      - If get_snapshot raised.
        """
        descriptions = {}
        known_snaps = self.get_all_snapshot_names()

        for name in names:
            if name not in known_snaps:
                LOGGER.warning('Snapshot "{}" does not exist.'.format(name))
                continue

            descriptions[name] = self.get_snapshot(name)

        return descriptions

    def get_device_firmwares(self, xname='all'):
        """Get device firmware information for the specified xname.

        Args:
            xname: Xname for which devices should be obtained. Omit to
                get 'all' xnames.

        Raises:
            APIError: - The call to the FUS failed.
                      - Invalid JSON was returned.
                      - There was no 'devices' field in the JSON.
        """
        try:
            response = self.get('version', xname)
        except APIError as err:
            raise APIError('Error contacting the FUS: {}'.format(err))

        try:
            response_json = response.json()
        except ValueError as err:
            raise APIError('The JSON received was invalid: {}'.format(err))

        # can raise KeyError
        try:
            ret = response_json['devices']
            return ret or []
        except KeyError:
            raise APIError('The JSON payload was missing an entry for "devices".')

    def make_fw_table(self, fw_devs):
        """For creating rows to be fed into a Report.

        Args:
            fw_devs (list): A list of dictionaries with xnames and their
                firmware elements and versions.

                fw_devs = [
                    {
                        xname: xname,
                        'targets': [{'version': vers, 'id': id}, ...]
                    },
                    ...
                ]

        Returns:
            A list-of-lists table of strings, each row representing
            the firmware version for an xname and ID.
        """
        return self._make_fw_table(fw_devs, 'id', 'version')


def create_firmware_client(session=None, host=None, cert_verify=None):
    """Determines which client type (FUS or FAS) to initialize.

    Args:
        Same as APIGatewayClient.__init__.

    Returns:
        A new instance of FASClient or FUSClient depending on which service
        was available.

    Raises:
        APIError: Neither service was available.
    """
    client = FASClient(session, host, cert_verify)

    try:
        response = client.get('service', 'status')
        LOGGER.debug('Using the FAS')
    except APIError:
        client = FUSClient(session, host, cert_verify)
        try:
            response = client.get('status')
        except APIError:
            LOGGER.error('Neither the FUS or FAS was available.')
            raise

        LOGGER.debug('Using the FUS')

    return client
