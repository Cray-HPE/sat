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
Implements the build and customization of IMS images from the input file.
"""
from collections import defaultdict, Counter
import logging
import math

from sat.apiclient import APIError, CFSClient, IMSClient
from sat.cli.bootprep.errors import ImageCreateError
from sat.cli.bootprep.input.image import DependentInputImage, IMSInputImage
from sat.cli.bootprep.public_key import get_ims_public_key_id
from sat.session import SATSession
from sat.util import pester_choices
from sat.waiting import (
    DependencyCycleError,
    DependencyGroupWaiter,
    WaitingFailure
)


LOGGER = logging.getLogger(__name__)


def validate_unique_image_ref_names(input_images):
    """Validate that all images have unique value for ref_name property.

    Args:
        input_images (list of sat.cli.bootprep.input.image.BaseInputImage): the
            input images in the bootprep input instance

    Raises:
        ImageCreateError: if the images do not have unique ref_name values
    """
    counts_by_ref_name = Counter(image.ref_name for image in input_images if image.ref_name)
    non_unique_ref_names = [name for name, count in counts_by_ref_name.items() if count > 1]
    if non_unique_ref_names:
        raise ImageCreateError(f'Images must have unique values for "ref_name" if specified.'
                               f'Non-unique names: '
                               f'{", ".join(non_unique_ref_names)}')


def validate_unique_image_names(input_images):
    """Validate that the input images all have unique names

    Images must have unique names, so that they can be referenced by name in the
    session templates in a bootprep input file.

    Args:
        input_images (list of sat.cli.bootprep.input.image.BaseInputImage): the
            input images in the bootprep input instance

    Raises:
        ImageCreateError: if the images do not have unique names
    """
    counts_by_name = Counter()

    failed_name_renders = 0
    for image in input_images:
        try:
            counts_by_name[image.name] += 1
        except ImageCreateError as err:
            failed_name_renders += 1
            LOGGER.error(f'Failed to render name of {image}: {err}')

    if failed_name_renders:
        raise ImageCreateError(f'Failed to render {failed_name_renders} image names.')

    non_unique_names = [name for name, count in counts_by_name.items() if count > 1]
    if non_unique_names:
        raise ImageCreateError(f'Names of images to create must be unique. Non-unique names: '
                               f'{", ".join(non_unique_names)}')


def validate_no_overwritten_ims_bases(input_images):
    """Validate that no images will overwrite another's IMS base.

    The supported way for an image to depend on another is to refer to an image
    by its ref_name in the base.image_ref property. Replacing an IMS image used
    by another image as its base can result in undefined behavior because both
    images could be built at the same time.
    """
    # Find all named IMS images used as bases
    name_based_images = [image for image in input_images
                         if isinstance(image, IMSInputImage) and not image.base_is_recipe
                         and 'name' in image.ims_data]

    conflicts_exist = False
    for name_based_image in name_based_images:
        for other_image in input_images:
            if other_image.name == name_based_image.ims_data['name']:
                conflicts_exist = True
                LOGGER.error(f'{name_based_image} uses {name_based_image.base_description}'
                             f'which conflicts with the image created by {other_image}.')

    if conflicts_exist:
        raise ImageCreateError(f'Conflicts between images bases and generated image names '
                               f'exist. Use "ref_name" and "base.image_ref" to correctly '
                               f'declare dependencies between images.')


def get_ims_images_by_name(ims_client):
    """Get a dict mapping from name to IMS image record for all existing IMS images.

    Args:
        ims_client (sat.apiclient.IMSClient): the IMS API client to query

    Returns:
        dict: a dictionary mapping from IMS image name to the IMS image record
            data dictionary

    Raises:
        ImageCreateError: if unable to query IMS for existing images
    """
    try:
        all_ims_images = ims_client.get_matching_resources('image')
    except APIError as err:
        raise ImageCreateError(f'Failed to query IMS for existing images: {err}')

    ims_images_by_name = defaultdict(list)
    for ims_image in all_ims_images:
        ims_images_by_name[ims_image.get('name')].append(ims_image)

    return dict(ims_images_by_name)


def handle_existing_images(ims_client, input_images, overwrite, skip, dry_run):
    """Handle any images that have a name collision with images already in IMS.

    Although IMS identifies images by a uuid field, 'id', bootprep requires that
    all images have unique names, so that the admin can always refer to an image
    by its name rather than an non-descriptive id.

    Args:
        ims_client (sat.apiclient.IMSClient): the IMS API client to use to get
            info about existing public keys or to create new ones
        input_images (list of sat.cli.bootprep.input.image.InputImage): the input
            images in the bootprep input instance
        overwrite (bool): if True, existing images should be overwritten
        skip (bool): if True, existing images should be overwritten
        dry_run (bool): whether this is a dry-run or not

    Returns:
        list of IMSImage: the list of images that should be created

    Raises:
        ImageCreateError: if unable to query IMS for existing images, or if
            some images already exist and user chose to abort
    """
    ims_images_by_name = get_ims_images_by_name(ims_client)

    existing_input_images = [input_image for input_image in input_images
                             if input_image.name in ims_images_by_name]

    if not existing_input_images:
        return input_images

    verb = ('will be', 'would be')[dry_run]

    existing_input_names = [image.name for image in existing_input_images]
    if not overwrite and not skip:
        answer = pester_choices(f'One or more images already exist in IMS with the following '
                                f'names: {", ".join(existing_input_names)}. Would you like to skip, '
                                f'overwrite, or abort?', ('skip', 'overwrite', 'abort'))
        if answer == 'abort':
            raise ImageCreateError('User chose to abort')
        skip = answer == 'skip'
        overwrite = answer == 'overwrite'

    msg_template = (f'Images with the following names already exist in IMS and '
                    f'{verb} %(action)s: {", ".join(existing_input_names)}')
    if overwrite:
        failed_overwrites = []
        LOGGER.info(msg_template, {'action': 'overwritten'})
        for existing_input_image in existing_input_images:
            try:
                existing_input_image.add_images_to_delete(ims_images_by_name[existing_input_image.name])
            except ImageCreateError as err:
                LOGGER.error(str(err))
                failed_overwrites.append(existing_input_image)

        if failed_overwrites:
            raise ImageCreateError(f'Failed to set up overwrite of {len(failed_overwrites)} '
                                   f'input image(s).')

        return input_images
    elif skip:
        LOGGER.info(msg_template, {'action': 'skipped'})

        # Remove already existing images as dependencies of other images. They can be built right away
        for existing_image in existing_input_images:
            existing_image.skip = True
            for image in input_images:
                if existing_image in image.dependencies:
                    LOGGER.debug(f'Removing skipped, already existing {existing_image} '
                                 f'from dependencies of {image}.')
                    image.remove_dependency(existing_image)

        # Create all images that do not already exist
        return [image for image in input_images if image.name not in existing_input_names]


def find_image_dependencies(input_images):
    """Find and record any dependencies between images.

    For example, suppose the bootprep input file looks like this:

    images:
    - name: "{{ base.name }}"
      ref_name: cos-base-image
      base:
        product:
          name: cos
          version: "{{ cos.version }}"
    - name: compute-gpu-{{ base.name }}
      base:
        image_ref: cos-base-image
      configuration: compute-gpu
      configuration_group_names:
      - Compute
    - name: compute-no-gpu-{{ base.name }}
      base:
        image_ref: cos-base-image
      configuration: compute-no-gpu
      configuration_group_names:
      - Compute

    In this case, the second and third images whose names start with "compute-gpu"
    and "compute-no-gpu", respectively, both depend on the first image with the
    "ref_name" property value of "cos-base-image". That image must be built first,
    before the second and third images customize it with different configurations.

    Args:
        input_images (list of sat.cli.bootprep.input.image.InputImage): the list
            of images from the bootprep input file that are to be built.

    Returns:
        None. The input_images will have their dependency_images and
        dependent_images attributes populated.

    Raises:
        ImageCreateError: if the images defined in the input file have circular
            dependencies or unresolved dependencies.
    """
    # Get a list of any input images which have dependencies
    input_images_by_ref_name = {input_image.ref_name: input_image
                                for input_image in input_images if input_image.ref_name is not None}
    errors_exist = False
    for index, image in enumerate(input_images):

        # Only DependentInputImages will depend on other images
        if not isinstance(image, DependentInputImage):
            continue

        if image.base_image_ref in input_images_by_ref_name:
            dependency_image = input_images_by_ref_name[image.base_image_ref]
            LOGGER.info(f'{image} depends on {dependency_image}.')

            try:
                image.add_dependency(dependency_image)
            except DependencyCycleError as err:
                errors_exist = True
                LOGGER.error(str(err))
        else:
            errors_exist = True
            LOGGER.error(f'Unable to resolve {image.base_description}.')

    if errors_exist:
        raise ImageCreateError('Invalid dependencies exist in images to be created. '
                               'Resolve the dependency issues and try again.')


def validate_image_ims_bases(input_images):
    """Validate that the ims bases are valid for the given input images

    Args:
        input_images (list of sat.cli.bootprep.input.image.BaseInputImage): the
            IMSImages which should have their IMS base validated. These images
            should be just the images without dependencies on other images from
            the input, since an image with dependencies depends on images that
            are not yet in IMS and will be created by other images in the input
            file.

    Returns: None

    Raises:
        ImageCreateError: if any images do not have a valid IMS base
    """
    failed_images = []
    for image in input_images:
        try:
            # Accessing this property for the first time queries the IMS API
            ims_base = image.ims_base
            LOGGER.info(f'Found IMS base for {image}: {image.base_description}')
            LOGGER.debug(f'IMS base for {image}: {ims_base}')
        except ImageCreateError as err:
            failed_images.append(image)
            LOGGER.error(f'Failed to find base for {image}: {err}')

    if failed_images:
        raise ImageCreateError(f'Failed to find match in IMS for {len(failed_images)} '
                               f'input images')


def validate_image_configurations(input_images, cfs_client, input_config_names, dry_run):
    """Validate that the images refer to valid existing configurations.

    Args:
        input_images (list of sat.cli.bootprep.input.image.InputImage): the
            IMSImages which should have their configurations validated.
        cfs_client (csm_api_client.service.cfs.CFSClient): the CFS client to query to
            determine whether the configuration for the image exists.
        input_config_names (list of str): the list of configuration names that
            are defined in the input file
        dry_run (bool): True if this is a dry run, False otherwise.
    """
    failed_images = []
    for image in input_images:
        if not image.configuration:
            continue

        # In the dry-run case, configurations will not actually be created, so
        # we have to check against what would have been created.
        if dry_run and image.configuration in input_config_names:
            continue

        resp = cfs_client.get('configurations', image.configuration, raise_not_ok=False)
        if not resp.ok:
            if resp.status_code == 404:
                LOGGER.error('Configuration %s not found for image %s',
                             image.configuration, image.name)
            else:
                LOGGER.error('Could not query configuration %s for image %s: %s',
                             image.configuration, image.name, resp.reason)
            failed_images.append(image)

    if failed_images:
        raise ImageCreateError(f'Failed to validate CFS configuration for {len(failed_images)} '
                               f'input images')


class ImageCreationGroupWaiter(DependencyGroupWaiter):
    """Kicks off image creation in IMS and waits for jobs to complete

    This will also handle creating jobs for dependent images once their
    dependencies have completed.
    """

    def __init__(self, members, timeout, poll_interval=10, retries=0):
        """Create a new ImageCreationWaiter

        This just overrides the default for poll_interval from the superclass.

        Args:
            members (list of sat.cli.bootprep.input.image.InputImage): the list
                of IMSImage objects without dependencies to create first.
            timeout: See GroupWaiter docstring
            poll_interval: See GroupWaiter docstring
            retries: See GroupWaiter docstring
        """
        super().__init__(members, timeout, poll_interval, retries)

    def condition_name(self):
        """str: the name of the condition being waited for"""
        return 'creation of IMS images'

    def member_has_completed(self, member):
        """Check whether the given IMSImage member has been created and/or configured

        Args:
            member (sat.cli.bootprep.input.image.InputImage): the IMS image to
                check for completion

        Raises:
            WaitingFailure: if a fatal error occurred while getting status of
                member, or member failed at some point in creation.
        """
        # Raising WaitingFailure causes the image to be added to `self.failed`
        # and an error message will be logged that mentions which member failed
        try:
            if member.has_completed:
                if not member.completed_successfully:
                    raise WaitingFailure(f'creation failed')
                return True

            return False
        except ImageCreateError as err:
            raise WaitingFailure(f'status check failed: {err}')


def create_images(instance, args):
    """Create and customize IMS images defined in the given instance

    Args:
        instance (sat.cli.bootprep.input.instance.InputInstance): the full bootprep
            input instance loaded from the input file and already validated
            against the schema.
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootprep subcommand.

    Returns: None

    Raises:
        ImageCreateError: if there is a failure to create images
    """
    input_images = instance.input_images
    if not input_images:
        LOGGER.info('Given input did not define any IMS images')
        return

    sat_session = SATSession()
    ims_client = IMSClient(sat_session)
    cfs_client = CFSClient(sat_session)

    ims_public_key_id = get_ims_public_key_id(ims_client, public_key_id=args.public_key_id,
                                              public_key_file_path=args.public_key_file_path,
                                              dry_run=args.dry_run)
    LOGGER.info(f'Using IMS public key with id {ims_public_key_id}')

    # TODO (CRAYSAT-1275): Fix up this error-prone way of requiring that we set public_key_id later
    for image in input_images:
        image.public_key_id = ims_public_key_id

    validate_unique_image_ref_names(input_images)
    # Validate dependencies on the full set of input images
    find_image_dependencies(input_images)

    # Raises ImageCreateError if validation of IMS bases fails
    # Do this early to provide information required to render names.
    validate_image_ims_bases(input_images)

    # Raises ImageCreateError if validation of CFS configurations fails
    validate_image_configurations(input_images, cfs_client,
                                  instance.input_configuration_names, args.dry_run)

    # This is where name properties are first accessed and thus rendered
    validate_unique_image_names(input_images)

    images_to_create = handle_existing_images(ims_client, input_images, args.overwrite_images,
                                              args.skip_existing_images, args.dry_run)

    validate_no_overwritten_ims_bases(images_to_create)

    images_without_dependencies = [image for image in images_to_create
                                   if not image.has_dependencies()]

    verb = ("will be", "would be")[args.dry_run]
    LOGGER.info(f'Of the {len(images_to_create)} that {verb} created, '
                f'{len(images_without_dependencies)} have no dependencies '
                f'and {verb} created first.')

    create_verb = ('Creating', 'Would create')[args.dry_run]
    LOGGER.info(f'{create_verb} {len(images_to_create)} images.')

    if args.dry_run:
        LOGGER.info("Dry run, not creating images.")
        return

    # Default to no timeout since it's unknown how long image creation could take
    waiter = ImageCreationGroupWaiter(images_to_create, math.inf)
    LOGGER.info('Creating images')
    waiter.wait_for_completion()
    if waiter.failed:
        raise ImageCreateError(f'Creation of {len(waiter.failed)} images failed')
    else:
        LOGGER.info('Image creation completed successfully')

    if args.delete_ims_jobs:
        for image in images_to_create:
            image.clean_up_image_create_job()
