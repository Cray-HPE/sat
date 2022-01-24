"""
The parser for the bmccreds subcommand.

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

from argparse import HelpFormatter

from sat.constants import BMC_TYPES
from sat.parsergroups import create_format_options, create_xname_options


PASSWORD_DOMAIN_HELP = '''\
Specify the domain or 'reach' of a password.
When generating a random password, this option
specifies which (if any) BMCs will have the same
randomly-generated password. Only valid with
--random-password.

Choices are:
system    Use the same password for all specified
          BMCs (default).
cabinet   Use the same password for all BMCs within
          each cabinet.  Use different passwords
chassis   Use the same password for all BMCs within
          each chassis (Mountain only -- for River,
          chassis == cabinet)
bmc       Use a different password for all
          specified BMCs.
'''


class BMCCredsFormatter(HelpFormatter):
    """An argparse.HelpFormatter that does not wrap lines for some text."""

    # Argument descriptions that should not be line-wrapped by argparse
    RAW_TEXT_HELP = [PASSWORD_DOMAIN_HELP]

    def _split_lines(self, text, width):
        if text in self.RAW_TEXT_HELP:
            return text.splitlines()
        return super()._split_lines(text, width)


def add_bmccreds_subparser(subparsers):
    """Add the bmccreds subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.

    Returns:
        None
    """
    format_options = create_format_options()
    xname_options = create_xname_options()

    bmccreds_subparser = subparsers.add_parser(
        'bmccreds', help='Set BMC Redfish access credentials.',
        description='Set BMC Redfish access credentials '
                    'for some or all BMCs in the system.',
        formatter_class=BMCCredsFormatter,
        parents=[format_options, xname_options]
    )

    password_options = bmccreds_subparser.add_mutually_exclusive_group()

    password_options.add_argument(
        '--password',
        help='Specify BMC password. If this option is not specified and '
             '--random-password is not given, then the user will be prompted '
             'to enter a password. This option is not valid with '
             '--random-password.'
    )

    password_options.add_argument(
        '--random-password', action='store_true',
        help='If given, then generate a random BMC password. If this option is '
             'not specified and --password is not given, then the user will be '
             'prompted to enter a password. This option is not valid with '
             '--password.'
    )

    # Even though the default is 'system', do not set it as default, so we
    # check whether --pw-domain was given without --random-password and if
    # so raise an error.
    bmccreds_subparser.add_argument(
        '--pw-domain', choices=['system', 'cabinet', 'chassis', 'bmc'],
        help=PASSWORD_DOMAIN_HELP,
    )

    bmccreds_subparser.add_argument(
        '--disruptive', action='store_true',
        help='Do not prompt for confirmation.'
    )

    bmccreds_subparser.add_argument(
        '--no-hsm-check', action='store_true',
        help='Don\'t consult HSM to check BMC eligibility. Requires '
             'xnames to be specified.  This is used when BMC credentials '
             'need to be set but HSM is unavailable (emergency use).'
    )

    bmccreds_subparser.add_argument(
        '--include-disabled', action='store_true',
        help='Include BMCs which are discovered but currently disabled. '
             'Without this option, disabled BMCs are ignored.'
    )

    bmccreds_subparser.add_argument(
        '--include-failed-discovery', action='store_true',
        help='Include BMCs for which discovery failed. Without this option, '
             'BMCs with discovery errors are ignored.'
    )

    bmccreds_subparser.add_argument(
        '--retries', type=int, default=3,
        help='Number of times to retry setting credentials. Default: 3'
    )

    bmccreds_subparser.add_argument(
        '--bmc-types', choices=BMC_TYPES, nargs='+', default=BMC_TYPES,
        help='Specify the BMC type to include in the operation. '
             'More than one of these types can be specified. The default is '
             'all BMC types. Types not specified will be excluded from consideration.'
    )
