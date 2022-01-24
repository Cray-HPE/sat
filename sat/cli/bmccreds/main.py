"""
The main entry point for the bmccreds subcommand.

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

from sat.apiclient import APIError, HSMClient
from sat.cli.bmccreds.creds_manager import BMCCredsManager, BMCCredsException
from sat.cli.bmccreds.constants import (
    BMC_USERNAME,
    MAX_XNAMES_TO_DISPLAY,
    USER_PASSWORD_MAX_LENGTH,
    VALID_BMC_PASSWORD_CHARACTERS
)
from sat.session import SATSession
from sat.util import format_long_list, get_username_and_password_interactively, pester


LOGGER = logging.getLogger(__name__)


def validate_args(args):
    """Check command-line arguments to 'sat bmccreds'.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit: if invalid options were given.
    """
    if args.pw_domain and not args.random_password:
        LOGGER.error('--pw-domain is only valid with --random-password.')
        raise SystemExit(1)

    if args.no_hsm_check and not args.xnames:
        LOGGER.error('--no-hsm-check requires xnames to be specified.')
        raise SystemExit(1)


def check_password_requirements(password):
    """Check password requirements.

    Check password is not longer than the maximum length and is
    only comprised of allowed characters.

    Args:
        password (str): the password to check.

    Returns:
        None

    Raises:
        ValueError: if the password does not meet the requirements.
    """
    if len(password) > USER_PASSWORD_MAX_LENGTH:
        raise ValueError(
            f'Password must be less than or equal to {USER_PASSWORD_MAX_LENGTH} characters.'
        )
    if not all(char in VALID_BMC_PASSWORD_CHARACTERS for char in password):
        raise ValueError(
            f'Password may only contain letters, numbers and underscores.'
        )


def set_creds_with_retry(credentials_manager, retries, session):
    """Call set_bmc_passwords with a retry.

    Args:
        credentials_manager (BMCCredsManager): A BMCCredsManager object.
        retries (int): Number of times to retry.
        session (SATSession): A SAT Session object.

    Returns:
        None

    Raises:
        SystemExit: if updating credentials failed after the specified number of tries.
    """
    num_tries = 1
    while num_tries <= retries:
        try:
            credentials_manager.set_bmc_passwords(session)
            return
        except BMCCredsException as err:
            LOGGER.error('Attempt %s of %s: %s', num_tries, retries, err)
        num_tries += 1

    LOGGER.error('Failed to update BMC credentials after %s retries', retries)
    raise SystemExit(1)


def do_bmccreds(args):
    """Executes the bmccreds command with the given arguments.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit: if invalid arguments are given.
        SystemExit: if checking BMC eligibility fails.
        SystemExit: if the chosen password does not meet the requirements.
        SystemExit: if setting BMC credentials fails.
    """
    validate_args(args)

    # Use same session for both HSMClient and SCSDClient
    session = SATSession()

    # Get BMC xnames from HSM or validate against HSM.
    if not args.no_hsm_check:
        hsm_client = HSMClient(session)
        try:
            xnames = hsm_client.get_and_filter_bmcs(
                args.bmc_types,
                args.include_disabled,
                args.include_failed_discovery,
                args.xnames
            )
        except APIError as err:
            LOGGER.error('Failed to contact HSM to check BMC eligibility: %s', err)
            raise SystemExit(1)
    else:
        xnames = set(args.xnames)

    if not xnames:
        LOGGER.error('No valid xnames for which to set credentials.')
        raise SystemExit(1)

    if not args.disruptive and not pester(
                f'Setting BMC credentials on the following BMCs: '
                f'{format_long_list(list(xnames), MAX_XNAMES_TO_DISPLAY)}. Proceed?'):
        raise SystemExit(1)

    # Get and validate user password if specified.
    if not args.random_password:
        user_password = args.password or get_username_and_password_interactively(
            BMC_USERNAME, password_prompt='BMC password', confirm_password=True
        )[1]
        try:
            check_password_requirements(
                user_password
            )
        except ValueError as err:
            LOGGER.error(err)
            raise SystemExit(1)
    else:
        user_password = None

    credentials_manager = BMCCredsManager(
        password=user_password,
        xnames=xnames,
        domain=args.pw_domain,
        force=args.no_hsm_check,
        report_format=args.format,
    )
    set_creds_with_retry(credentials_manager, args.retries, session)
