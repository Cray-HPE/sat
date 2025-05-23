#
# MIT License
#
# (C) Copyright 2019-2023, 2025 Hewlett Packard Enterprise Development LP
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
Functions to create the top-level ArgumentParser for the program.
"""

from argparse import ArgumentParser, _SubParsersAction
import pkg_resources
import sys

import inflect

import sat.cli


def _unrecognized_msg(unknown, subcommand=None):
    """Generates an error message describing unrecognized option(s).

    Args:
        unknown ([str]): unrecognized arguments
        subcommand (str, None): the subcommand in used.

    Returns:
        a string describing the unrecognized arguments.
    """
    inf = inflect.engine()
    return ('unrecognized {}{}: {}'
            .format(inf.plural("argument", len(unknown)),
                    ' for subcommand {}'.format(subcommand) if subcommand else '',
                    inf.join(unknown)))


class SATArgParser(ArgumentParser):
    """Small subclass of argparse.ArgumentParser.

    This is used to automatically print usage information for subcommands. By
    default, ArgumentParser will not print meaningful usage information for
    subparsers when problematic arguments are given. The only difference this
    subclass makes is that it *will* print a usage statement for subcommands
    when they are given problematic arguments.
    """
    def parse_args(self, args=None, namespace=None):
        """Parses command line arguments.

        See superclass documentation.
        """
        parsed, unknown = self.parse_known_args(args, namespace)

        if parsed.command is None:  # No subcommand given
            self.print_help()
            if unknown:
                self.error(_unrecognized_msg(unknown))
            else:
                self.error('missing subcommand')

        elif unknown:  # Some unknown arguments were given
            self.error(_unrecognized_msg(unknown, subcommand=parsed.command))

        else:
            return parsed

    def error(self, message):
        """Prints errors based on invalid arguments.

        See superclass documentation.
        """
        if len(sys.argv) > 1:
            subcommand = sys.argv[1]
            subparser_actions = [action for action in self._actions
                                 if isinstance(action, _SubParsersAction)]
            if len(subparser_actions) < 1:
                # If there aren't any subparsers, that indicates that
                # this method is being called from the context of a
                # subparser instance. Thus we can just print the usage
                # for the "whole" parser.
                self._print_message(self.format_usage(),
                                    file=sys.stderr)
            else:
                # This method is being called from the top-level
                # parser. There *should* only be one _SubparsersAction
                # object in this instance, even though we don't
                # enforce this. For simplicity, we can just take the
                # first (only) one.
                action = subparser_actions.pop()
                if subcommand in action.choices:
                    self._print_message(action.choices[subcommand].format_help(),
                                        file=sys.stderr)

        fargs = {'prog': self.prog, 'message': message}
        self.exit(2, "{prog}: error: {message}\n".format(**fargs))


def create_parent_parser():
    """Creates the top-level parser for sat and adds subparsers for the commands.

    Returns:
        An argparse.ArgumentParser object with all arguments and subparsers
        added to it.
    """

    parser = SATArgParser(description='SAT - The System Admin Toolkit')

    # This gets the version from the installed package.
    version = pkg_resources.require('sat')[0].version
    parser.add_argument('--version', action='version',
                        version='%(prog)s {}'.format(version))

    parser.add_argument(
        '-u', '--username',
        help='Username to use when loading or fetching authentication '
             'tokens. Overrides value set in config file.')

    parser.add_argument(
        '--token-file',
        help='Token file to use for authentication. '
             'In order to share the token file between the host and container '
             'when sat is run in a container environment, '
             'the path should be either an absolute or relative path of a file '
             'in or below the home or current directory. '
             'Overrides value derived from other settings, or set in config file.')

    parser.add_argument(
        '--logfile',
        help='Set location of logs for this run. '
             'In order to share the location between the host and container '
             'when sat is run in a container environment, '
             'the path should be either an absolute or relative path of a file '
             'in or below the home or current directory. '
             'Overrides value set in config file.')

    parser.add_argument(
        '--loglevel-stderr', '--loglevel',
        help='Set minimum log severity for messages output to stderr on this run. '
             'Overrides value set in config file.',
        choices=['debug', 'info', 'warning', 'error', 'critical'])

    parser.add_argument(
        '--loglevel-file',
        help='Set minimum log severity for messages reported to log file on this run. '
             'Overrides values set in config file.',
        choices=['debug', 'info', 'warning', 'error', 'critical'])

    parser.add_argument(
        '--api-timeout',
        help='The amount of time, in seconds, to wait for calls to any HTTP API to '
             'complete before considering them failed.',
        metavar='TIMEOUT',
        type=int)

    parser.add_argument(
        '--tenant-name',
        help='The name of the tenant against which to run administrative commands.',
        metavar='NAME',
    )

    parser.add_argument(
        '--api-retries',
        help='The number of times to retry calls to any HTTP API after encountering '
             'network errors or internal server errors before considering them failed.',
        metavar='RETRIES',
        type=int)

    parser.add_argument(
        '--api-backoff',
        help='The backoff factor controlling the time interval between retries. The time '
             'between retries is calculated as BACKOFF_FACTOR * (2^(numRetries-1)), '
             'per the documentation on urllib3.util.Retry.',
        metavar='BACKOFF_FACTOR',
        type=float)

    subparsers = parser.add_subparsers(metavar='command', dest='command')
    sat.cli.build_out_subparsers(subparsers)

    return parser
