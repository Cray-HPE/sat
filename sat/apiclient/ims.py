#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
Client for querying the Image Management Service (IMS) API
"""
import base64
import copy
import datetime
import hashlib
import json
import logging
import os
from tempfile import TemporaryDirectory
import warnings

import boto3
from boto3.exceptions import Boto3Error
from inflect import engine
from kubernetes.client import ApiException, CoreV1Api
from kubernetes.config import load_kube_config, ConfigException
from urllib3.exceptions import InsecureRequestWarning
from yaml import YAMLLoadWarning

from sat.apiclient.gateway import APIGatewayClient, APIError
from sat.cached_property import cached_property
from sat.config import get_config_value
from sat.util import get_val_by_path

LOGGER = logging.getLogger(__name__)


class IMSClient(APIGatewayClient):
    base_resource_path = 'ims/v3/'
    valid_resource_types = ('image', 'recipe', 'public-key')
    # The bucket for boot images created by IMS
    boot_images_bucket = 'boot-images'

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dictionary to cache the list of different types of resources from IMS
        self._cached_resources = {}
        self.inflector = engine()

    @cached_property
    def s3_credentials(self):
        """Get the IMS s3 credentials from a kubernetes secret.

        TODO (CRAYSAT-1267): Remove manual image rename code once one of these is done:
        - CASMCMS-7634: Ability to rename IMS images
        - CASMCMS-7564: Ability to specify destination image name with CFS

        Returns:
            tuple: access_key, secret_key from the ims-s3-credentials secret in the
                ims namespace

        Raises:
            APIError: if unable to load the kubernetes config or read the
                kubernetes secret containing IMS S3 credentials
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            raise APIError(f'Failed to load Kubernetes config which is required '
                           f'to obtain IMS S3 credentials: {err}')

        kube_client = CoreV1Api()
        try:
            secret = kube_client.read_namespaced_secret('ims-s3-credentials', 'ims')
        except ApiException as err:
            raise APIError(f'Failed to read ims-s3-credentials secret'
                           f'which is required to rename an image: {err}')

        return (
            base64.b64decode(secret.data['access_key']).decode(),
            base64.b64decode(secret.data['secret_key']).decode(),
        )

    @cached_property
    def s3_resource(self):
        """Helper function to load the S3 API from configuration variables.

        Returns:
            A boto3 ServiceResource object.

        Raises:
            APIError: if unable to get IMS S3 credentials or unable to create
                the boto3 ServiceResource object.
        """
        try:
            access_key, secret_key = self.s3_credentials
            # TODO (CRAYSAT-926): Start verifying HTTPS requests (remove verify=False)
            return boto3.resource(
                's3',
                endpoint_url=get_config_value('s3.endpoint'),
                aws_access_key_id=access_key,
                aws_secret_access_key=secret_key,
                region_name='',
                verify=False
            )
        except Boto3Error as err:
            raise APIError(f'Unable to get S3 resource: {err}')

    def _get_resources_cached(self, resource_type):
        """Get the resources of the given type from the cache or from IMS API if not cached.

        Args:
            resource_type (str): The type of the resource to look for in IMS.
                Must be one of `IMSClient.valid_resource_types`.

        Raises:
            APIError: if there is an issue getting the images or recipes
            ValueError: if given an invalid resource_type
        """
        if resource_type not in self.valid_resource_types:
            raise ValueError(f'IMS resource type must be one of {self.valid_resource_types}, '
                             f'got {resource_type}')

        plural_resource = self.inflector.plural(resource_type)

        fail_msg = f'Failed to get IMS {plural_resource}'
        if plural_resource not in self._cached_resources:
            try:
                resources = self.get(f'{resource_type}s').json()
            except APIError as err:
                resources = APIError(f'{fail_msg}: {err}')
            except ValueError as err:
                resources = APIError(f'{fail_msg} due to failure parsing JSON in response: {err}')

            self._cached_resources[plural_resource] = resources

        cached_value = self._cached_resources[plural_resource]
        if isinstance(cached_value, Exception):
            raise cached_value
        else:
            return cached_value

    def clear_resource_cache(self, resource_type=None):
        """Clear the cached copy of the resources of the given type.

        Args:
            resource_type (str): the type of resource for which to clear the
                cache. Must be one of `IMSClient.valid_resource_types`. If not
                specified, the cache for all resource types will be cleared.

        Raises:
            ValueError: if given an invalid `resource_type`
        """
        if resource_type is not None and resource_type not in self.valid_resource_types:
            raise ValueError(f'IMS resource type must be one of {self.valid_resource_types}, '
                             f'got {resource_type}')

        if resource_type is None:
            self._cached_resources = {}
        else:
            plural_resource = self.inflector.plural(resource_type)
            if plural_resource in self._cached_resources:
                del self._cached_resources[plural_resource]

    def get_matching_resources(self, resource_type, resource_id=None, **kwargs):
        """Get the resource(s) matching the given type and id or name.

        If neither `resource_id` nor `name` are specified, then return all the
        resources of the given type.

        Args:
            resource_type (str): The type of the resource to look for in IMS.
                Must be one of 'image', 'recipe', or 'public-key'
            resource_id (str): The uid of the resource to look for in IMS.
                if this is specified, anything in **kwargs is ignored.
            **kwargs: Additional properties to match against the existing
                resources. These can be any property of the resource, e.g.
                'name' for images, recipes, and public keys.

        Returns:
            list of dict: The list of images or recipes.

        Raises:
            APIError: if there is an issue getting the images or recipes
            ValueError: if given an invalid resource_type
        """
        if resource_type not in self.valid_resource_types:
            raise ValueError(f'IMS resource type must be one of {self.valid_resource_types}, '
                             f'got {resource_type}')

        fail_msg = f'Failed to get IMS {resource_type}'

        if resource_id is not None:
            fail_msg = f'{fail_msg} with id={resource_id}'
            try:
                # Always return a list even when there's only one
                return [self.get(f'{resource_type}s/{resource_id}').json()]
            except APIError as err:
                raise APIError(f'{fail_msg}: {err}')
            except ValueError as err:
                raise APIError(f'{fail_msg} due to failure parsing JSON in response: {err}')

        resources = self._get_resources_cached(resource_type)

        if not kwargs:
            return resources

        return [resource for resource in resources
                if all(resource.get(prop) == value
                       for prop, value in kwargs.items())]

    def create_public_key(self, name, public_key):
        """Create a new public key record in IMS.

        Args:
            name (str): the name of the public key record to create in IMS
            public_key (str): the full public key

        Returns:
            dict: the created IMS public key record

        Raises:
            APIError: if there is a failure to create the public key in IMS
        """
        request_body = {'name': name, 'public_key': public_key}
        try:
            return self.post('public-keys', json=request_body).json()
        except APIError as err:
            raise APIError(f'Failed to create new public key with name "{name}": {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON response from creating new '
                           f'public key with name "{name}": {err}')

    def create_image_build_job(self, image_name, recipe_id, public_key_id):
        """Create an IMS job to build an image from a recipe.

        Args:
            image_name (str): the name of the image to create
            recipe_id (str): the id of the IMS recipe to build into an image
            public_key_id (str): the id of the SSH public key stored in IMS to
                use for passwordless SSH into the IMS debug or configuration
                shell.

        Returns:
            dict: the job record that was created

        Raises:
            APIError: if there is a failure to create the IMS job
        """
        request_body = {
            'job_type': 'create',
            'artifact_id': recipe_id,
            'public_key_id': public_key_id,
            'image_root_archive_name': image_name
        }

        try:
            return self.post('jobs', json=request_body).json()
        except APIError as err:
            raise APIError(f'Failed to create image creation job in IMS: {err}')
        except ValueError as err:
            raise APIError(f'Failed to decode JSON from IMS job creation response: {err}')

    def get_job(self, job_id):
        """Get an IMS job.

        Args:
            job_id (str): the job ID
        """
        try:
            return self.get('jobs', job_id).json()
        except APIError as err:
            raise APIError(f'Failed to get job {job_id}: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON response for job {job_id}: {err}')

    def get_image(self, image_id):
        """Get an IMS image directly by its ID.

        Args:
            image_id (str): the image ID
        """
        try:
            return self.get('images', image_id).json()
        except APIError as err:
            raise APIError(f'Failed to get image {image_id}: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON response for image {image_id}: {err}')

    def create_empty_image(self, name):
        """Create a new empty image record in IMS that has no link data yet.

        Args:
            name (str): the name of the image record to create

        Returns:
            dict: the created image record

        Raises:
            APIError: if the request to create the new image fails or the
                response is not valid JSON
        """
        try:
            return self.post('images', json={'name': name}).json()
        except APIError as err:
            raise APIError(f'Failed to create new empty image named {name}: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON response when creating empty '
                           f'image named {name}: {err}')

    @staticmethod
    def split_s3_artifact_path(path):
        """Split a path to an artifact in S3 into its bucket and path components.

        Args:
            path (str): An artifact path in the format stored by IMS, e.g.
                s3://boot-images/<UUID>/rootfs

        Returns:
            tuple: a tuple consisting of the S3 bucket name and the path to the
                object in that bucket, e.g. ('boot-images', '<UUID>/rootfs').
        """
        s3_host, bucket_path = path.split('://')
        return bucket_path.split('/', maxsplit=1)

    def get_image_manifest(self, image_id):
        """Get the contents of the image manifest for the given image.

        Args:
            image_id (str): the ID of the image to get the manifest for

        Returns:
            dict or None: the manifest for the given image or None if the image
                does not have a manifest

        Raises:
            APIError: if the image manifest cannot be obtained, either due to
                errors accessing S3 or errors querying IMS for the manifest path
        """
        image = self.get_image(image_id)
        s3_manifest_path = get_val_by_path(image, 'link.path')
        if not s3_manifest_path:
            return None

        with TemporaryDirectory(prefix='sat-ims-manifest') as tempdir:
            local_manifest_path = os.path.join(tempdir, 'manifest.json')
            LOGGER.debug(f'Downloading manifest file for image with id {image_id} '
                         f'to {local_manifest_path}')

            s3_manifest_bucket, s3_manifest_key = self.split_s3_artifact_path(s3_manifest_path)
            try:
                # TODO(SAT-926): Start verifying HTTPS requests
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=InsecureRequestWarning)
                    self.s3_resource.Object(s3_manifest_bucket,
                                            s3_manifest_key).download_file(local_manifest_path)
            except Boto3Error as err:
                raise APIError(f'Failed to download manifest with key {s3_manifest_key} '
                               f'from bucket {s3_manifest_bucket}: {err}')
            try:
                with open(local_manifest_path, 'r') as manifest_file:
                    return json.load(manifest_file)
            except OSError as err:
                raise APIError(f'Failed to open downloaded manifest file for image '
                               f'with id {image_id}: {err}')
            except ValueError as err:
                raise APIError(f'Failed to parse JSON manifest file for image '
                               f'with id {image_id}: {err}')

    def copy_manifest_artifacts(self, manifest, new_image_id, new_name):
        """Copy artifacts specified in a manifest to a location for use by a new image.

        Args:
            manifest (dict): an IMS image manifest
            new_image_id (str): the image ID of the new manifest. This image ID
                will be used in the s3 key for each new artifact.
            new_name (str): the name of the new IMS image. This is placed in the
                metadata of each artifact

        Returns:
            dict: the new manifest that refers to the copied artifacts

        Raises:
            APIError: if unable to copy artifacts
        """
        old_artifacts = manifest.get('artifacts', [])

        artifact_types = set(get_val_by_path(artifact, 'link.type') for artifact in old_artifacts)
        unrecognized_types = artifact_types - {'s3'}
        if unrecognized_types:
            raise APIError(f'Unable to copy unrecognized artifact types: '
                           f'{", ".join(t for t in unrecognized_types)}')

        new_artifacts = []

        for old_artifact in old_artifacts:
            old_artifact_path = get_val_by_path(old_artifact, 'link.path')

            if not old_artifact_path:
                raise APIError(f'Unable to copy artifact of {old_artifact.get("type", "unknown")} '
                               f'type due to missing path')

            old_artifact_bucket, old_artifact_key = self.split_s3_artifact_path(old_artifact_path)
            artifact_name = os.path.basename(old_artifact_key)
            new_artifact_key = f'{new_image_id}/{artifact_name}'

            try:
                # TODO (CRAYSAT-926): Start verifying HTTPS requests
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=InsecureRequestWarning)

                    new_metadata = {
                        'x-shasta-ims-image-id': new_image_id,
                        'x-shasta-ims-image-name': new_name
                        # No applicable 'x-shasta-ims-job-id' metadata
                    }

                    # md5sum is lost by REPLACE if we don't manually preserve it
                    old_object = self.s3_resource.Object(old_artifact_bucket, old_artifact_key)
                    md5sum = old_object.metadata.get('md5sum')
                    if md5sum:
                        new_metadata['md5sum'] = md5sum

                    new_object = self.s3_resource.Object(self.boot_images_bucket, new_artifact_key)
                    LOGGER.debug(f'Created new S3 object: {new_object}')
                    copy_result = new_object.copy_from(CopySource=f'{old_artifact_bucket}/{old_artifact_key}',
                                                       Metadata=new_metadata, MetadataDirective='REPLACE')
                    LOGGER.debug(f'Got response from copying S3 object: {copy_result}')
            except Boto3Error as err:
                raise APIError(f'Failed to copy artifact {old_artifact_key} to {new_artifact_key}: {err}')

            new_artifact = copy.deepcopy(old_artifact)
            new_artifact['link']['etag'] = get_val_by_path(copy_result, 'CopyObjectResult.ETag')
            new_artifact['link']['path'] = f's3://{self.boot_images_bucket}/{new_artifact_key}'
            new_artifacts.append(new_artifact)

        return {
            'artifacts': new_artifacts,
            'created': datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S.%f'),
            'version': manifest['version']
        }

    def upload_image_manifest(self, image_id, manifest):
        """Upload the image manifest to S3 for the given image ID.

        Args:
            image_id (str): the ID of the image to upload the manifest for
            manifest (dict): the image manifest

        Returns:
            The newly created manifest S3 Object

        Raises:
            APIError: if the image manifest cannot be uploaded to S3
        """
        with TemporaryDirectory(prefix='sat-ims-manifest') as tempdir:
            local_manifest_path = os.path.join(tempdir, 'manifest.json')
            try:
                with open(local_manifest_path, 'w') as new_manifest_file:
                    json.dump(manifest, new_manifest_file, indent=4)
            except OSError as err:
                raise APIError(f'Unable to save manifest to local file {local_manifest_path}: {err}')

            with open(local_manifest_path, 'rb') as new_manifest_file:
                md5sum = hashlib.md5()
                for chunk in iter(lambda: new_manifest_file.read(4096), b''):
                    md5sum.update(chunk)
                md5sum_digest = md5sum.hexdigest()

            manifest_key = f'{image_id}/manifest.json'
            try:
                # TODO (CRAYSAT-926): Start verifying HTTPS requests
                with warnings.catch_warnings():
                    warnings.filterwarnings('ignore', category=InsecureRequestWarning)
                    manifest_object = self.s3_resource.Object(self.boot_images_bucket, manifest_key)
                    manifest_object.upload_file(local_manifest_path,
                                                ExtraArgs={'Metadata': {'md5sum': md5sum_digest}})
            except Boto3Error as err:
                raise APIError(f'Failed to upload manifest file to {manifest_key} '
                               f'in S3 bucket {self.boot_images_bucket}: {err}')
            LOGGER.debug(f'Created new S3 manifest object: {manifest_object}')
            return manifest_object

    def copy_image(self, image_id, new_name):
        """Make a deep copy of an image.

        This is a deep copy in that it examines the manifest file of the image
        being copied, copies all artifacts referenced by that manifest in S3,
        creates a new manifest that references the newly copied artifacts, and
        then uploads that new manifest to S3.

        Args:
            image_id (str): the ID of the image to be copied
            new_name (str): the new copied image name

        Returns:
            str: the image ID of the newly created image

        Raises:
            APIError: if there is an error accessing S3 or making requests to
                the IMS API
        """
        new_image = self.create_empty_image(new_name)
        try:
            new_image_id = new_image['id']
        except KeyError as err:
            raise APIError(f'Copy image failed due to missing "{err}" in new '
                           f'image named {new_name}')

        old_manifest = self.get_image_manifest(image_id)
        if not old_manifest:
            LOGGER.warning(f'Image with id {image_id} has no manifest file so '
                           f'no artifacts will be copied.')
            return new_image_id

        try:
            new_manifest = self.copy_manifest_artifacts(old_manifest, new_image_id, new_name)
            new_manifest_object = self.upload_image_manifest(new_image_id, new_manifest)

            # TODO (CRAYSAT-926): Start verifying HTTPS requests
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=InsecureRequestWarning)
                try:
                    # For some reason the etag contains explicit quotes
                    new_etag = new_manifest_object.e_tag.strip('"')
                except Boto3Error as err:
                    raise APIError(f'Failed to get etag of new manifest object: {err}')

            new_image_link_info = {
                'etag': new_etag,
                'path': f's3://{self.boot_images_bucket}/{new_manifest_object.key}',
                'type': 's3'
            }
            try:
                self.patch('images', new_image_id, json={'link': new_image_link_info})
            except APIError:
                raise APIError(f'Failed to update image manifest for new image with id {new_image_id}')
        except APIError as err:
            LOGGER.debug(f'Cleaning up partial image copy with id {new_image_id}')
            self.delete_image(new_image_id)
            raise APIError(f'Failed to copy image {image_id} to a new image named {new_name}: {err}')

        return new_image_id

    def delete_image(self, image_id, permanent=False):
        """Delete an image.

        Args:
            image_id (str): the id of the image to delete
            permanent (bool): if True, permanently delete the image by deleting
                it from /deleted/images/ as well.

        Raises:
            APIError: if the request to delete the image failed
        """
        try:
            self.delete('images', image_id)
        except APIError as err:
            raise APIError(f'Failed to delete image with id {image_id}: {err}')

        if not permanent:
            return

        try:
            self.delete('deleted', 'images', image_id)
        except APIError as err:
            raise APIError(f'Failed to permanently delete image with id {image_id}: {err}')

    # TODO (CRAYSAT-1267): Once CASMCMS-7634 is resolved, simplify this to be a PATCH request
    def rename_image(self, image_id, new_name):
        """Rename an image by performing a deep copy and then delete.

        The IMS API does not currently support renaming an image, so this is
        way more complicated than it should be. To accomplish the copy, we must
        do the following:

        * Create a new empty image record with the desired name and record its ID
        * Get the manifest of the image to be renamed
        * Do a copy in S3 of each artifact from the manifest to a path that
          includes the new image ID in S3.
        * Create a new manifest file that references the newly copied artifacts.
        * Upload that manifest to S3 at a path that includes the new image ID
        * Update the new image to refer to the newly uploaded manifest.
        * Delete the old image.

        Returns:
            str: the new ID of the renamed image

        Raises:
            APIError: if there is a failure when trying to do the rename
        """
        new_image_id = self.copy_image(image_id, new_name)
        try:
            self.delete_image(image_id, permanent=True)
        except APIError as err:
            raise APIError(f'Failed to delete old image with id {image_id} after '
                           f'it was copied to a new image with id {new_image_id}: {err}')

        return new_image_id
