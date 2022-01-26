"""
Implements the creation of CFS configurations from the input file.

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

from sat.apiclient import APIError, CFSClient
from sat.cli.bootprep.input.configuration import InputConfigurationLayer
from sat.cli.bootprep.output import RequestDumper
from sat.cli.bootprep.errors import ConfigurationCreateError
from sat.session import SATSession
from sat.util import pester_choices

LOGGER = logging.getLogger(__name__)


def handle_existing_configs(cfs_client, input_configs, args):
    """Check for configs that already exist and return the configs to create.

    Args:
        cfs_client (CFSClient): The CFS API client
        input_configs (list of sat.cli.bootprep.input.configuration.InputConfiguration):
            the list of CFS configurations defined in the input instance.
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootprep subcommand.

    Returns:
         list of InputConfiguration: the list of CFS configurations that should
            be created.

    Raises:
        ConfigurationCreateError: If unable to query CFS for existing configurations
            or if some configs already exist and user requested to abort.
    """
    try:
        cfs_config_names = set(config.get('name') for config in cfs_client.get_configurations())
    except APIError as err:
        raise ConfigurationCreateError(f'Failed to query CFS for existing configurations: {err}')

    existing_names = [config.name for config in input_configs
                      if config.name in cfs_config_names]

    verb = ('will be', 'would be')[args.dry_run]

    if not existing_names:
        return input_configs

    overwrite = args.overwrite_configs
    skip = args.skip_existing_configs

    if not overwrite and not skip:
        answer = pester_choices(f'The following CFS configurations already exist: '
                                f'{", ".join(existing_names)}. Would you like to skip, '
                                f'overwrite, or abort?', ('skip', 'overwrite', 'abort'))
        if answer == 'abort':
            raise ConfigurationCreateError('User chose to abort')
        skip = answer == 'skip'
        overwrite = answer == 'overwrite'

    msg_template = (f'The following CFS configurations already exist and '
                    f'{verb} %(action)s: {", ".join(existing_names)}')
    if overwrite:
        LOGGER.info(msg_template, {'action': 'overwritten'})
        return input_configs
    elif skip:
        LOGGER.info(msg_template, {'action': 'skipped'})
        # Create all configs that do not already exist
        return [config for config in input_configs if config.name not in existing_names]


def create_configurations(instance, args):
    """Create the CFS configurations defined in the given instance.

    Args:
        instance (sat.cli.bootprep.input.instance.InputInstance): the full bootprep
            input instance loaded from the input file and already validated
            against the schema.
        args: The argparse.Namespace object containing the parsed arguments
            passed to the bootprep subcommand.

    Returns:
        None

    Raises:
        ConfigurationCreateError: if there was a failure to create any of the
            configurations defined in `instance`
    """
    InputConfigurationLayer.resolve_branches = args.resolve_branches

    input_configs = instance.input_configurations

    if not input_configs:
        LOGGER.info('Given input did not define any CFS configurations')
        return

    create_verb = ('Creating', 'Would create')[args.dry_run]

    LOGGER.info(f'{create_verb} {len(input_configs)} CFS configuration(s)')

    cfs_client = CFSClient(SATSession())
    configs_to_create = handle_existing_configs(cfs_client, input_configs, args)
    failed_configs = []

    request_dumper = RequestDumper('CFS config', args)

    for cfs_configuration in configs_to_create:
        config_name = cfs_configuration.name
        LOGGER.info(f'{create_verb} CFS configuration with name "{config_name}"')

        try:
            request_body = cfs_configuration.get_cfs_api_data()
        except ConfigurationCreateError as err:
            LOGGER.error(f'Failed to get data to create configuration {config_name}: {err}')
            failed_configs.append(cfs_configuration)
            continue

        request_dumper.write_request_body(config_name, request_body)

        if not args.dry_run:
            try:
                # request_body guaranteed to have 'name' key, so no need to catch ValueError
                cfs_client.put_configuration(cfs_configuration.name, request_body)
            except APIError as err:
                LOGGER.error(f'Failed to create or update configuration '
                             f'{cfs_configuration.name}: {err}')
                failed_configs.append(cfs_configuration)

    if failed_configs:
        raise ConfigurationCreateError(f'Failed to create {len(failed_configs)} configuration(s)')
