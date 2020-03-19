"""
Entry point for the firmware subcommand.

Copyright 2020 Cray Inc. All Rights Reserved.
"""
import logging

from sat.apiclient import APIError, FirmwareClient
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)


def get_all_snapshot_names():
    """Return all existing snapshots on the FUS.

    Returns:
        A set of all existing snapshot names.

    Raises:
        APIError: If the request to the FUS could not be made.
    """
    api_client = FirmwareClient(SATSession())

    try:
        response = api_client.get('snapshot')

    except APIError as err:
        raise APIError('Getting all snapshots: {}'.format(err))

    response = response.json()
    snapshots = response['snapshots']

    return set([x['name'] for x in snapshots])


def _describe_snapshot(name):
    """Describe data from a particular snapshot.

    The output from this function can be passed to make_fw_table.

    Be careful - a snapshot of the matching name will be created if it
    doesn't exist.

    Args:
        name: Snapshot name.

    Returns:
        List of dicts that can be passed to make_fw_table.

    Raises:
        APIError: The firmware api could not be queried.
    """
    api_client = FirmwareClient(SATSession())
    response = api_client.get('snapshot', name)
    response = response.json()

    devices = response['devices']

    return devices


def describe_snapshots(names):
    """Describe multiple snapshots.

    If a name doesn't exist, then it isn't described, nor is it created.

    Args:
        names: Snapshot names to get descriptions of.

    Returns:
        A dict where the keys are the snapshot names and the values are
        the snapshots themselves. Each value may be passed to make_fw_table.

    Raises:
        APIError: The firmware api could not be queried.
    """
    descriptions = {}
    known_snaps = get_all_snapshot_names()

    for name in names:
        if name not in known_snaps:
            LOGGER.warning('Snapshot "{}" does not exist.'.format(name))
            continue

        descriptions[name] = _describe_snapshot(name)

    return descriptions
