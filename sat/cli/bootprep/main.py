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
Entry point for the bootprep subcommand.
"""
import logging
import os

from cray_product_catalog.query import ProductCatalog, ProductCatalogError
from jinja2.sandbox import SandboxedEnvironment
import yaml

from sat.apiclient import CFSClient, IMSClient
from sat.apiclient.bos import BOSClientCommon
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
from sat.cli.bootprep.constants import EXAMPLE_FILE_NAME
from sat.cli.bootprep.documentation import (
    display_schema,
    generate_docs_tarball,
    resource_absolute_path,
)
from sat.cli.bootprep.example import BootprepExampleError, get_example_cos_and_uan_data
from sat.cli.bootprep.image import create_images
from sat.cli.bootprep.output import ensure_output_directory, RequestDumper
from sat.cli.bootprep.validate import (
    load_and_validate_instance,
    load_and_validate_schema,
    SCHEMA_FILE_RELATIVE_PATH,
)
from sat.cli.bootprep.vars import VariableContext, VariableContextError
from sat.config import get_config_value
from sat.report import Report
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)


def load_vars_or_exit(recipe_version, vars_file_path, additional_vars):
    """Load variables and construct the variable context.

    This is a simple wrapper around VariableContext.load_vars()
    which handles constructing the context and loading variables.
    If there is a problem loading the variables, exit the program.

    Args:
        recipe_version (str): the version of the software recipe to
            load from VCS
        vars_file_path (str): the path to the vars file to load
        additional_vars (dict): additional variables, e.g. from
            the command line

    Returns:
        VariableContext: the context containing the loaded variables

    Raises:
        SystemExit: if the variables cannot be loaded.
    """
    try:
        var_context = VariableContext(recipe_version, vars_file_path, additional_vars)
        var_context.load_vars()
        return var_context
    except VariableContextError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)


def do_bootprep_docs(args):
    """Generate bootprep documentation.


    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit: If a fatal error is encountered.
    """

    try:
        schema_path = resource_absolute_path(SCHEMA_FILE_RELATIVE_PATH)
        generate_docs_tarball(schema_path, args.output_dir)
    except BootPrepDocsError as err:
        LOGGER.error(f'Could not perform bootprep schema documentation action: {err}')
        raise SystemExit(1)


def do_bootprep_schema(schema_file_contents):
    """Display the bootprep schema in raw format.

    Args:
        schema_file_contents (bytes): the schema file contents as bytes.

    Returns:
        None

    Raises:
        SystemExit: If a fatal error is encountered.
    """
    try:
        display_schema(schema_file_contents)
    except BootPrepDocsError as err:
        LOGGER.error(f'Internal error while displaying schema: {err}')
        raise SystemExit(1)


def do_bootprep_example(schema_validator, args):
    """Generate an example bootprep input file.

    Args:
        schema_validator (jsonschema.protocols.Validator): the validator object
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit: If a fatal error is encountered.
    """
    full_example_file_path = os.path.join(args.output_dir, EXAMPLE_FILE_NAME)

    try:
        example_data = get_example_cos_and_uan_data()
    except BootprepExampleError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

    # Get current schema version
    example_data['schema_version'] = schema_validator.schema['version']

    try:
        with open(full_example_file_path, 'w') as f:
            yaml.dump(example_data, f, sort_keys=False)
    except OSError as err:
        LOGGER.error(f'Failed to write example data to file {full_example_file_path}: {err}')
        raise SystemExit(1)

    LOGGER.info(f'Wrote example bootprep input file to {full_example_file_path}.')


def do_bootprep_run(schema_validator, args):
    """Create images, configurations, and/or session templates.

    Args:
        schema_validator (jsonschema.protocols.Validator): the validator object
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit: If a fatal error is encountered.
    """
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
    # CASMTRIAGE-4288: IMS can be extremely slow to return DELETE requests for
    # large images, so this IMSClient will not use a timeout on HTTP requests
    ims_client.set_timeout(None)
    bos_client = BOSClientCommon.get_bos_client(session)

    try:
        product_catalog = ProductCatalog()
    except ProductCatalogError as err:
        LOGGER.warning(f'Failed to load product catalog data. Creation of any input items '
                       f'that require data from the product catalog will fail. ({err})')
        # Any item from the InputInstance that needs to access product catalog
        # data will fail. Otherwise, this is not a problem.
        product_catalog = None

    var_context = load_vars_or_exit(
        args.recipe_version,
        args.vars_file,
        args.vars
    )

    jinja_env = SandboxedEnvironment()
    jinja_env.globals = var_context.vars

    instance = InputInstance(instance_data, cfs_client, ims_client, bos_client, jinja_env, product_catalog)

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

    # Must validate first because `handle_existing_items` must know the name of each
    # item to be created, and validation will render names.
    try:
        instance.input_session_templates.validate(dry_run=args.dry_run)
    except InputItemValidateError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

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

    if not args.dry_run:
        try:
            request_dumper = RequestDumper('BOS session template', args)
            instance.input_session_templates.create_items(dumper=request_dumper)
        except InputItemCreateError as err:
            LOGGER.error(str(err))
            raise SystemExit(1)


def do_bootprep_list_available_vars(args):
    var_context = load_vars_or_exit(
        args.recipe_version,
        args.vars_file,
        args.vars
    )
    report = Report(
        ['Variable name', 'Value', 'Source'], 'Bootprep Variables',
        args.sort_by, args.reverse,
        get_config_value('format.no_headings'),
        get_config_value('format.no_borders'),
        filter_strs=args.filter_strs,
        display_headings=args.fields,
        print_format=args.format
    )
    report.add_rows(var_context.enumerate_vars_and_sources())
    print(report)


def do_bootprep(args):
    """Main entry point for bootprep command.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """
    try:
        schema_file_contents, schema_validator = load_and_validate_schema()
    except BootPrepInternalError as err:
        LOGGER.error(f'Internal error while loading schema: {err}')
        raise SystemExit(1)

    ensure_output_directory(args)

    if args.action == 'run':
        do_bootprep_run(schema_validator, args)
    elif args.action == 'generate-docs':
        do_bootprep_docs(args)
    elif args.action == 'view-schema':
        do_bootprep_schema(schema_file_contents)
    elif args.action == 'generate-example':
        do_bootprep_example(schema_validator, args)
    elif args.action == 'list-vars':
        do_bootprep_list_available_vars(args)
