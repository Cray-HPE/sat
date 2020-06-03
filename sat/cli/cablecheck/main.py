"""
The main entry point for the cablecheck subcommand.

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

import subprocess

COMMAND_LOC = "/usr/bin/check-hsn-cables"


def do_cablecheck(args):
    """Runs the do_cablecheck command with the given arguments.

    The check_hsn_cables.py is invoked (with output going to stdout).

    A standard location or construction method for the point-to-point
    data file has not been defined. The System Layout Service (SLS)
    might provide point-to-point data eventually. Site modification of
    point-to-point data can occur, for example to omit cables not of
    current interest.

    The check_hsn_cables.py script is a work in progress, with JSON/YAML
    output a planned feature. SAT Cable Check will be expanded to format
    output and provide output options when JSON/YAML is available (see
    Jira SSHOTSW-2453 and SAT-63).

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    """

    command_args = [args.p2p_file]

    if args.nic_prefix:
        command_args += ['-n', args.nic_prefix]

    if args.link_levels:
        command_args.append('-l')
        command_args += args.link_levels

    if args.quiet:
        command_args.append('-q')

    subprocess.run([COMMAND_LOC] + command_args)
