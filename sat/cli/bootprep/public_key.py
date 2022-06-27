#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Functions for handling IMS SSH public key records.
"""

from getpass import getuser
import logging
import uuid

from sat.apiclient import APIError
from sat.cli.bootprep.constants import DEFAULT_PUBLIC_KEY_FILE_EXPANDED
from sat.cli.bootprep.errors import PublicKeyError

LOGGER = logging.getLogger(__name__)


def get_ims_public_key_by_id(ims_client, public_key_id):
    """Get the IMS public key record by its id

    Args:
        ims_client (sat.apiclient.IMSClient): the IMS API client to use to get
            info about existing public keys
        public_key_id (str): the id of the public key record in IMS

    Returns:
        dict: the public key record from IMS

    Raises:
        PublicKeyError: if unable to get the public key record of a key with
            the given id, e.g. if it does not exist or IMS cannot be queried
    """
    try:
        matching_keys = ims_client.get_matching_resources('public-key', resource_id=public_key_id)
        matching_key = matching_keys[0]
    except APIError as err:
        raise PublicKeyError(str(err))
    except IndexError:
        # Should not happen since we would get an API error if unable to find
        # a public key with this id, but program defensively.
        raise PublicKeyError(f'Unexpected error while looking for public key '
                             f'with id={public_key_id} in IMS.')

    LOGGER.info(f'Found existing public key in IMS with id={public_key_id}.')
    return matching_key


def get_ims_public_key_by_contents(ims_client, public_key_file_path=None, dry_run=False):
    """Get an IMS public key record by its contents, creating on if necessary

    Args:
        ims_client (sat.apiclient.IMSClient): the IMS API client to use to get
            info about existing public keys or to create new ones.
        public_key_file_path (str or None): the path to a public key file whose
            contents should be searched for in IMS. If None, use the default
            path, DEFAULT_PUBLIC_KEY_FILE_EXPANDED.
        dry_run (bool): whether this is a dry-run or not. If it's a dry-run, do
            only read-only operations. Do not create a new public key, but instead
            make up one with a fake id.

    Returns:
        dict: the public key record from IMS

    Raises:
        PublicKeyError: if the key file cannot be read, or a key record with
            the given contents does not exist and cannot be created.
    """
    # If the user has not specified a public key id or file, fall back on a default file
    public_key_file_path = public_key_file_path or DEFAULT_PUBLIC_KEY_FILE_EXPANDED

    try:
        with open(public_key_file_path, 'r') as public_key_file:
            public_key = public_key_file.read()
    except OSError as err:
        raise PublicKeyError(f'Failed to read public key from {public_key_file_path}: {err}')

    try:
        matching_keys = ims_client.get_matching_resources('public-key', public_key=public_key)
    except APIError as err:
        raise PublicKeyError(str(err))

    if not matching_keys:
        new_key_name = f'{getuser()} public key'
        action = ('will be', 'would be')[dry_run]
        LOGGER.info(f'Found no existing public keys in IMS whose contents match that of '
                    f'{public_key_file_path}. One {action} created.')
        if dry_run:
            return {'name': new_key_name, 'public_key': public_key, 'id': uuid.uuid4()}
        try:
            return ims_client.create_public_key(new_key_name, public_key)
        except APIError as err:
            raise PublicKeyError(f'Failed to create new public key "{new_key_name}" in IMS: {err}')
    elif len(matching_keys) > 1:
        LOGGER.warning(f'Found {len(matching_keys)} public keys in IMS whose contents match the '
                       f'contents of public key file {public_key_file_path}. Using the first one, '
                       f'but you may wish to clean up the duplicates.')
    else:
        LOGGER.info(f'Found existing public key in IMS whose contents match that of {public_key_file_path}.')

    return matching_keys[0]


def get_ims_public_key_id(ims_client, public_key_id=None, public_key_file_path=None, dry_run=False):
    """Get an IMS public key id, uploading a new key if necessary.

    Only one of public_key_id and public_key_file_path should be specified

    Args:
        ims_client (sat.apiclient.IMSClient): the IMS API client to use to get
            info about existing public keys or to create new ones
        public_key_id (str): the uuid of an existing public key in IMS
        public_key_file_path (str): the path to a public key file whose contents
            should be searched for in IMS
        dry_run (bool): whether this is a dry-run or not.

    Returns:
        str: the public key record id from IMS

    Raises:
        PublicKeyError: if we cannot find an IMS public key by id, if unable
            to query IMS for public keys, or if unable to create a new key from
            a file path
        ValueError: if both public_key_id and public_key_file_path are specified
    """
    if public_key_id is not None and public_key_file_path is not None:
        raise ValueError('Either public_key_id or public_key_file_path should be specified, '
                         'but not both.')

    # Get public key for building image with IMS
    if public_key_id:
        public_key_record = get_ims_public_key_by_id(ims_client, public_key_id)
    else:
        public_key_record = get_ims_public_key_by_contents(ims_client, public_key_file_path, dry_run)

    try:
        return public_key_record['id']
    except KeyError as err:
        # This should not happen based on IMS API spec, but if it does, fail gracefully
        raise PublicKeyError(f'IMS public key record is missing "{err}" key.')
