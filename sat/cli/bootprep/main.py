"""
Entry point for the bootprep subcommand.

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

from sat.apiclient import BOSClient, CFSClient, IMSClient
from sat.cli.bootprep.errors import (
    BootPrepDocsError,
    BootPrepInternalError,
    BootPrepValidationError,
    ConfigurationCreateError,
    ImageCreateError,
    InputItemCreateError,
    InputItemValidateError,
    UserAbortException
)
from sat.cli.bootprep.input.instance import InputInstance
from sat.cli.bootprep.configuration import create_configurations
from sat.cli.bootprep.documentation import (
    display_schema,
    generate_docs_tarball,
    resource_absolute_path,
)
from sat.cli.bootprep.image import create_images
from sat.cli.bootprep.validate import (
    load_and_validate_instance,
    load_and_validate_schema,
    SCHEMA_FILE_RELATIVE_PATH,
)
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)


def do_bootprep(args):
    """Main entry point for bootprep command.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """

    LOGGER.info(f'Loading schema file')
    try:
        schema_contents, schema_validator = load_and_validate_schema()
    except BootPrepInternalError as err:
        LOGGER.error(f'Internal error while loading schema: {err}')
        raise SystemExit(1)

    try:
        if args.view_input_schema:
            display_schema(schema_contents)
            return
        elif args.generate_schema_docs:
            schema_path = resource_absolute_path(SCHEMA_FILE_RELATIVE_PATH)
            generate_docs_tarball(schema_path, args.output_dir)
            return
    except BootPrepDocsError as err:
        LOGGER.error('Could not perform bootprep schema documentation action: %s', err)
        raise SystemExit(1)

    LOGGER.info(f'Validating given input file {args.input_file}')
    try:
        instance_data = load_and_validate_instance(args.input_file, schema_validator)
    except BootPrepValidationError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

    LOGGER.info('Input file successfully validated against schema')

    session = SATSession()
    cfs_client = CFSClient(session)
    ims_client = IMSClient(session)
    bos_client = BOSClient(session)

    instance = InputInstance(instance_data, cfs_client, ims_client, bos_client)

    # TODO (CRAYSAT-1277): Refactor images to use BaseInputItemCollection
    # TODO (CRAYSAT-1278): Refactor configurations to use BaseInputItemCollection
    # As part of the above, do more in methods of those classes. Generally, we
    # should do the following, perhaps in methods on `InputInstance`:
    # - Validate the input file, which includes:
    #   - Validate names of new objects are unique
    #   - Validate that referenced configurations and images exist
    # - Handle any existing objects of the same name
    # - Create the objects, if this is not a dry-run (or validation-only run)
    try:
        create_configurations(instance, args)
    except ConfigurationCreateError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

    try:
        create_images(instance, args)
    except ImageCreateError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

    # The IMSClient caches the list of images. Clear the cache so that we can find
    # newly created images when constructing session templates.
    ims_client.clear_resource_cache(resource_type='image')

    try:
        instance.input_session_templates.handle_existing_items(args.overwrite_templates,
                                                               args.skip_existing_templates,
                                                               args.dry_run)
    except UserAbortException:
        LOGGER.error('Aborted')
        raise SystemExit(1)
    except InputItemCreateError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

    try:
        instance.input_session_templates.validate(dry_run=args.dry_run)
    except InputItemValidateError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

    if not args.dry_run:
        try:
            instance.input_session_templates.create_items()
        except InputItemCreateError as err:
            LOGGER.error(str(err))
            raise SystemExit(1)
