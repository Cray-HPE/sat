#
# MIT License
#
# (C) Copyright 2020-2025 Hewlett Packard Enterprise Development LP
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
Client for querying the Firmware Action Service (FAS) API.
"""
from datetime import datetime, timedelta
import logging
import time

from csm_api_client.service.gateway import APIError, APIGatewayClient
import inflect

from sat.constants import MISSING_VALUE
from sat.xname import XName


inf = inflect.engine()
LOGGER = logging.getLogger(__name__)


class FASClient(APIGatewayClient):
    """API Client for querying the Firmware Action Service (FAS)."""
    # (str): The base URL of the service
    base_resource_path = 'fas/v1/'
    # (str): The name of the field in a response from FAS containing the
    # firmware device's name.
    name_field = 'name'
    # (str): The name of the field in a response from FAS containing the
    # firmware device's version.
    version_field = 'firmwareVersion'
    # (str): The name of the field in a response from FAS containing the
    # device's 'target name' (typically, an alternative name to name_field).
    target_name_field = 'targetName'
    # (str): The string message of the APIError to raise when no firmware
    # was found.
    err_no_firmware_found = 'No firmware found.'
    # (tuple): A tuple of headers that should be used when creating a firmware
    # table.
    headers = ('xname', 'name', 'target_name', 'version')

    @staticmethod
    def _create_row_from_target(target, xname):
        """Given a 'target' dictionary, create a table row. Helper for make_fw_table.

        Args:
            target (dict): The dictionary containing the attributes of a single
                firmware target.
            xname (str): The xname of the component to which this firmware
                target belongs.

        Returns:
            A list of values from the 'target' dictionary, or None if 'target'
                contains an error and not enough information to display a row.
        """
        fw_dev_fields = [FASClient.name_field, FASClient.target_name_field, FASClient.version_field]

        if target.get('error'):  # Do not log an error if the error is just an empty string.
            if xname == MISSING_VALUE:
                LOGGER.warning('FAS returned an error while retrieving firmware from an unknown device')
                return None

            LOGGER.error(
                'Error getting firmware for %s target %s: %s', xname,
                target.get(FASClient.name_field) or target.get(FASClient.target_name_field) or MISSING_VALUE,
                target['error']
            )
            # In the event of an error, skip creating a row if either:
            # - a version field does not exist
            # - neither 'name' nor 'target_name' fields exist
            if FASClient.version_field not in target or not any(f in target for f in [FASClient.name_field,
                                                                                      FASClient.target_name_field]):
                return None
        # Use XName class so xnames sort properly.
        return [XName(xname)] + [target.get(f, MISSING_VALUE) for f in fw_dev_fields]

    @staticmethod
    def make_fw_table(fw_devs):
        """For creating rows to be fed into a Report.

        Args:
            fw_devs (list): A list of dictionaries with xnames and their
                firmware elements and versions. These dictionaries should
                contain an 'xname' key and a 'targets' key. The value of the
                'targets' key is a list of dictionaries each of which has
                the values of name_field, target_name_field, and
                version_field as keys.

        Returns:
            A list-of-lists table of strings, each row representing the
            firmware version for a target beneath a component with an xname.
        """
        fw_table = []
        for fw_dev in fw_devs:
            xname = fw_dev.get('xname', MISSING_VALUE)
            targets = fw_dev.get('targets')
            if fw_dev.get('error'):  # Do not log an error if the error is just an empty string.
                LOGGER.error('Error getting firmware for %s: %s', xname, fw_dev['error'])
            elif not targets:
                # No error was logged, but there is no firmware for this xname
                LOGGER.warning('No firmware found for: %s', xname)

            if targets:
                rows_to_add = [
                    FASClient._create_row_from_target(target, xname) for target in targets
                ]
                fw_table.extend([row for row in rows_to_add if row])

        return fw_table

    def get_actions(self):
        """Get a list of all the firmware actions on the system.

        Returns:
            A list of dicts representing firmware actions on the system.

        Raises:
            APIError: if request to get actions from FAS fails
        """
        try:
            return self.get('actions').json()['actions']
        except ValueError as err:
            raise APIError('Unable to parse json in response from FAS: '
                           '{}'.format(err))
        except KeyError:
            raise APIError("No 'actions' key in response from FAS.")

    def get_active_actions(self):
        """Get a list of all the active firmware actions on the system.

        Returns:
            A list of dicts representing active firmware actions on the system.

        Raises:
            APIError: if request to get actions from FAS fails
        """
        return [update for update in self.get_actions()
                if update.get('state') not in ('aborted', 'completed')]

    def get_all_snapshot_names(self):
        """Return all snapshot names available in the FAS.

        Returns:
            A set of snapshot names.

        Raises:
            APIError: - If querying the FAS failed.
                      - The payload did not contain a 'snapshots' entry.
                      - The payload was invalid JSON.
        """
        try:
            response = self.get('snapshots')
        except APIError as err:
            raise APIError(f'Failed to get snapshots from the FAS API: {err}')

        try:
            response = response.json()
        except ValueError as err:
            raise APIError(f'The JSON payload was invalid: {err}')

        try:
            snapshots = response['snapshots']
        except KeyError:
            raise APIError('The payload was missing an entry for "snapshots".')

        return set([x['name'] for x in snapshots])

    def get_snapshot_devices(self, name, xnames=None):
        """Describe data from a particular snapshot, optionally filtered by xname.

        If any xnames are not in the given snapshot, log a warning for
        each xname not in the given snapshot.

        The output from this function can be passed to make_fw_table.

        Args:
            name (str): Snapshot name.
            xnames (list): A list of xnames for which the returned snapshot
                should include data.

        Returns:
            List of device dictionaries for the given snapshot
            that can be passed to make_fw_table. See the docstring of
            make_fw_table for the format this takes.

        Raises:
            APIError: - The firmware api could not be queried.
                      - The payload did not contain a 'devices' entry.
                      - The payload was invalid JSON.
                      - No firmware was found.
        """
        try:
            response = self.get('snapshots', name)
        except APIError as err:
            raise APIError(f'Failed to get snapshot "{name}" from the FAS API: {err}')

        try:
            response = response.json()
        except ValueError as err:
            raise APIError('The JSON payload from snapshot "{}" was invalid: {}'.format(name, err))

        try:
            devices = response['devices']
        except KeyError:
            raise APIError('The payload from snapshot "{}" was missing a "devices" key.'.format(name))

        if xnames:
            devices_to_return = [dev for dev in devices if dev.get('xname') in xnames]
            xnames_not_in_snapshot = [
                xname for xname in xnames if not any(dev.get('xname') == xname for dev in devices)
            ]
            if xnames_not_in_snapshot:
                LOGGER.warning('Warning: xname(s) %s not in snapshot %s', ','.join(xnames_not_in_snapshot), name)
        else:
            devices_to_return = devices

        if not devices_to_return:
            err_message = (
                f'Snapshot {name} did not have any devices under its "devices" key' +
                f' for xname(s) {",".join(xnames)}.' if xnames else '.'
            )
            raise APIError(err_message)

        return devices_to_return

    def get_multiple_snapshot_devices(self, names, xnames=None):
        """Describe multiple snapshots.

        Checks given snapshots against list of known snapshots,
        and log a warning for each given snapshot that does not exist,
        and skip attempting to get information for it.

        Args:
            names (list): Snapshot names to get descriptions of.
            xnames (list): A list of xnames for which the returned snapshots
                should include information. If unspecified, get_multiple_snapshot_devices
                will return snapshot information for all xnames.

        Returns:
            A dictionary where the keys are the snapshot names and the
            values are the snapshots. Each value may be passed to
            make_fw_table. See the docstring of make_fw_table for
            the format the snapshots take.

        Raises:
            APIError: - The firmware api could not be queried.
                      - The payload did not contain a 'devices' entry.
                      - The payload was invalid JSON.
                      - No firmware was found.
        """
        descriptions = {}
        known_snaps = self.get_all_snapshot_names()

        for name in names:
            if name not in known_snaps:
                LOGGER.warning('Snapshot %s does not exist.', name)
                continue
            try:
                descriptions[name] = self.get_snapshot_devices(name, xnames)
            except APIError as err:
                err_message = (
                    f'Error getting snapshot {name}' +
                    (f', xname(s) {",".join(xnames)}: {err}' if xnames else f': {err}')
                )
                LOGGER.error(err_message)

        if not descriptions:
            raise APIError(FASClient.err_no_firmware_found)

        return {name: description for name, description in descriptions.items()}

    def delete_snapshot(self, snapshot):
        """Delete a snapshot using the FAS API.

        Args:
            snapshot (str): The name of the snapshot to be deleted.

        Raises:
            APIError: If there is an error while attempting to delete the snapshot.
        """
        try:
            self.delete(f'snapshots/{snapshot}')

        except APIError:
            raise APIError(FASClient.err_no_firmware_found)

    def _create_snapshot(self, xnames=None):
        """Create a snapshot and return its data.

        Args:
            xnames: A list of xnames for which to take the snapshot.
                If not specified, then xnames will not be filtered.

        Returns:
            A dictionary of response data from FAS, where the 'devices'
            key points to a list of firmware device dictionaries.

        Raises:
            APIError: if FAS returned an APIError when creating the snapshot.
                This can also raise if:
                    - The payload from creating the snapshot was
                      missing either a 'ready' field while polling, or a
                      'devices' field.
                    - The FAS did not indicate if the snapshot was ready.
        """
        now = datetime.utcnow().replace(microsecond=0)
        name = 'SAT-{}-{}-{}-{}-{}-{}'.format(
            now.year, now.month, now.day, now.hour, now.minute, now.second
        )

        payload = {'name': name}

        # filter on xnames if provided.
        if xnames:
            payload['stateComponentFilter'] = {'xnames': xnames}

        try:
            self.post('snapshots', json=payload)
        except APIError as err:
            raise APIError('Error when posting new snapshot: {}'.format(err))

        # retrieve it and poll until ready
        response = None
        ready = False
        consecutive_failures = 0
        while not ready:
            time.sleep(5)

            try:
                response = self.get('snapshots', name).json()
                consecutive_failures = 0  # Reset consecutive failures on successful response
            except APIError as err:
                consecutive_failures += 1
                if consecutive_failures == 5:  # Maximum consecutive failures
                    raise APIError('Error when polling the snapshot {}: Exceeded maximum consecutive failures',
                                   format(err))
                else:
                    LOGGER.debug('Error when polling the snapshot {}: Retrying...'.format(err))
                    continue

            except ValueError as err:
                raise APIError('The JSON received was invalid: {}'.format(err))

            try:
                ready = response['ready']
            except KeyError:
                raise APIError('Payload returned from GET to snapshots/name did not have "ready" field.')

        LOGGER.info(f'Snapshot {name} created successfully.')

        return response

    def get_device_firmwares(self, xnames=None):
        """Returns devices optionally associated with particular xnames.

        Args:
            xnames ([str]): Xnames to get device firmware information from.
                If no value is provided, then all xnames will be queried.

        Returns:
            A list of device dictionaries for the given xname. This
            can be passed to make_fw_table. See the docstring of
            make_fw_table for the format this list of dictionaries
            takes.

        Raises:
            APIError: If creating the temporary snapshot failed,
                or the schema of the JSON payload returned from FAS
                was malformed.
        """
        # This can raise APIError
        response = self._create_snapshot(xnames)
        try:
            devices = response['devices']
            missing_xnames = set(xnames or []) - set(device.get('xname') for device in devices)
            if missing_xnames:
                LOGGER.warning(
                    'The snapshot is missing the following %s: %s',
                    inf.plural('xname', len(missing_xnames)),
                    inf.join(list(missing_xnames))
                )
            return devices
        except KeyError:
            raise APIError('The JSON payload did not contain a "devices" field.')
