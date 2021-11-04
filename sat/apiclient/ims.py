"""
Client for querying the Image Management Service (IMS) API

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
import logging

from inflect import engine

from sat.apiclient.gateway import APIGatewayClient, APIError

LOGGER = logging.getLogger(__name__)


class IMSClient(APIGatewayClient):
    base_resource_path = 'ims/v3/'
    valid_resource_types = ('image', 'recipe', 'public-key')

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        # Dictionary to cache the list of different types of resources from IMS
        self._cached_resources = {}
        self.inflector = engine()

    def _get_resources_cached(self, resource_type):
        """Get the resources of the given type from the cache or from IMS API if not cached.

        Args:
            resource_type (str): The type of the resource to look for in IMS.
                Must be one of 'image', 'recipe', or 'public-key'

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

    def get_matching_resources(self, resource_type, resource_id=None, **kwargs):
        """Get the resource(s) matching the given type and id or name

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
        """Create a new public key record in IMS

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
            raise APIError(f'Failed to parse JSON response from creating new public key with name "{name}"')

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
        """Get an IMS job

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
        """Get an IMS image directly by its ID

        Args:
            image_id (str): the image ID
        """
        try:
            return self.get('images', image_id).json()
        except APIError as err:
            raise APIError(f'Failed to get image {image_id}: {err}')
        except ValueError as err:
            raise APIError(f'Failed to parse JSON response for image {image_id}: {err}')
