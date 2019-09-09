"""
The main entry point for the cablecheck subcommand.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

import os
import os.path
import subprocess

COMMAND_LOC = "/usr/bin/"
COMMAND_NAME = "check_hsn_cables.py"

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

    The check_hsn_cable.py script is written in Python 2.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    """

    subprocess.run(
        ["python2", os.path.join(COMMAND_LOC, COMMAND_NAME), args.p2p_file])
