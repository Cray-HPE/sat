"""
Functions to create the top-level ArgumentParser for the program.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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

    def parse_known_args(self, args=None, namespace=None):
        self.exit_on_error = False
        return super().parse_known_args(args=args, namespace=namespace)

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
        help='Token file to use for authentication. Overrides value derived '
             'from other settings, or set in config file.')

    parser.add_argument(
        '--logfile',
        help='Set location of logs for this run. Overrides value set in config file.')

    parser.add_argument(
        '--loglevel',
        help='Set minimum log severity to report for this run. This level applies to '
             'messages logged to stderr and to the log file. Overrides values set in '
             'config file.',
        choices=['debug', 'info', 'warning', 'error', 'critical'])

    subparsers = parser.add_subparsers(metavar='command', dest='command')
    sat.cli.build_out_subparsers(subparsers)

    return parser
