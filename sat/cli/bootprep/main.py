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

from sat.apiclient import CFSClient, IMSClient
from sat.cli.bootprep.errors import (
    BootPrepInternalError,
    BootPrepValidationError,
    ConfigurationCreateError,
    ImageCreateError
)
from sat.cli.bootprep.input.instance import InputInstance
from sat.cli.bootprep.configuration import create_configurations
from sat.cli.bootprep.image import create_images
from sat.cli.bootprep.validate import load_bootprep_schema, load_and_validate_instance
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
        schema_validator = load_bootprep_schema()
    except BootPrepInternalError as err:
        LOGGER.error(f'Internal error while loading schema: {err}')
        raise SystemExit(1)

    LOGGER.info(f'Validating given input file {args.input_file}')
    try:
        instance_data = load_and_validate_instance(args.input_file, schema_validator)
    except BootPrepValidationError as err:
        LOGGER.error(str(err))
        raise SystemExit(1)

    LOGGER.info('Input file successfully validated')

    cfs_client = CFSClient(SATSession())
    ims_client = IMSClient(SATSession())

    instance = InputInstance(instance_data, cfs_client, ims_client)

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
