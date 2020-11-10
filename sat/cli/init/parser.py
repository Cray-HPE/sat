"""
The parser for the init subcommand.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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


def add_init_subparser(subparsers):
    """Add the init subparser to the parent parser.

    Args:
        subparsers: The argparse.ArgumentParser object returned by the
            add_subparsers method.
    """
    init_parser = subparsers.add_parser(
        'init', help='Initialize a SAT configuration file.',
        description='Initialize a SAT configuration file with default parameters '
                    'in the location specified on the command line, specified '
                    'by $SAT_CONFIG_FILE or in the default location.')

    init_parser.add_argument('-f', '--force', action='store_true',
                             help='Overwrite an existing config file at the specified location.')
    init_parser.add_argument('-o', '--output',
                             help='The path to which to write the configuration file.  If not set, the value of '
                                  '$SAT_CONFIG_FILE will be used, or $HOME/.config/sat/sat.toml if $SAT_CONFIG_FILE '
                                  'is not set.')
