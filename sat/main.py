#
# MIT License
#
# (C) Copyright 2019-2022 Hewlett Packard Enterprise Development LP
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
Entry point for the command-line interface.
"""

import importlib
import logging
import os
import sys

import argcomplete
import urllib3

from sat.config import ConfigFileExistsError, DEFAULT_CONFIG_PATH, generate_default_config, load_config
from sat.logging import bootstrap_logging, configure_logging
from sat.parser import create_parent_parser
from sat.util import ensure_permissions, get_resource_section_path

LOGGER = logging.getLogger(__name__)

# NOTE: SAT will still log a warning for unverified HTTPS requests
# if api_gateway.cert_verify is set to False or if s3.cert_verify
# is set to False. See _log_cert_verify_warnings in config.py.
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)


def main():
    """SAT Main.

    Returns:
        None. Calls sys.exit().
    """
    try:
        bootstrap_logging()

        # cablecheck has been removed in shasta 1.4 - see SAT-745
        if 'cablecheck' in sys.argv:
            LOGGER.warning(
                'sat cablecheck has been replaced by '
                '\'slingshot-topology-tool --cmd "show cables"\'\n'
            )

        # linkhealth has been removed in shasta 1.5 - see SAT-827
        if 'linkhealth' in sys.argv:
            LOGGER.warning(
                'sat linkhealth has been replaced by '
                '\'slingshot-topology-tool --cmd "show switch <ports,jacks> <switch xname>"\'\n'
            )

        parser = create_parent_parser()
        argcomplete.autocomplete(parser)
        args = parser.parse_args()

        # Set the permissions on config directory and token directory in case
        # they have been modified or incorrectly set up
        permissions = {
            DEFAULT_CONFIG_PATH: {
                'file_mode': 0o600,
                'dir_mode': 0o700,
            },
            get_resource_section_path('tokens'): {
                'dir_mode': 0o700,
            }
        }
        for filename, permission_kwargs in permissions.items():
            ensure_permissions(filename, **permission_kwargs)

        # Automatically create config file if it does not exist, except
        # in `sat init` where the subcommand will create it.  With
        # `sat init`, don't bother loading configuration or configuring
        # logging either.
        if args.command != 'init':
            try:
                generate_default_config(
                    os.getenv('SAT_CONFIG_FILE', DEFAULT_CONFIG_PATH),
                    username=args.username
                )
            except ConfigFileExistsError:
                # Would log a debug-level message here, but logging has not yet been configured
                pass
            load_config(args)
            configure_logging()

        # Dynamically importing here affords the following
        # advantages:
        # 1. If Ctrl-C is pressed while imports are occurring, we
        #    can handle it gracefully.
        # 2. We can import only the subcommand code relevant to the
        #    desired subcommand, which gives a small performance benefit,
        #    about a 100ms speedup for the import step.
        subcommand_module = importlib.import_module(
            'sat.cli.{}.main'.format(args.command))

        try:
            subcommand = getattr(subcommand_module, 'do_{}'.format(args.command))
        except AttributeError:
            # Subcommand main-routines need to follow a naming convention
            # of do_<subcommand>.
            LOGGER.error("Couldn't find function 'sat.%s.main.do_%s'. "
                         "Is it named correctly?",
                         args.command, args.command)
            sys.exit(1)

        subcommand(args)

    except KeyboardInterrupt:
        LOGGER.info("Received keyboard interrupt; quitting.", exc_info=True)

    sys.exit(0)


if __name__ == '__main__':
    main()
