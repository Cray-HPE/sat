# MIT License
#
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP
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
The main entry point for the jobstat subcommand.
"""
import logging
import requests
from sat.cli.jobstat import parser
from sat.report import Report
from sat.config import get_config_value


URL = "http://localhost:1999/all"
LOGGER = logging.getLogger(__name__)


def unload_json(url):
    """Unloads the JSON object from the server url and formats the data as a dictionary"""
    data = {}
    try:
        response = requests.get(url)
        data = response.json()
    except Exception as err:
        LOGGER.error(f"Failed to parse JSON from component state response: {err}")
        raise SystemExit(1)
    return data


def do_jobstat(args):
    """Run the jobstat command with the given arguments.
    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """
    # print('Hello jobstat')
    try:
        if args.all is True:
            server_data = unload_json(URL)
            application_data = server_data.get("jobstat")
            keys = []
            for i in application_data[0]:
                keys.append(i)
            report = Report(
                tuple(keys),
                None,
                args.sort_by,
                args.reverse,
                get_config_value("format.no_headings"),
                get_config_value("format.no_borders"),
                filter_strs=args.filter_strs,
                display_headings=args.fields,
                print_format=args.format,
            )
            for i in application_data:
                report.add_row(i)
            print(report)
    except Exception as err:
        LOGGER.error(f"Failed to execute jobstat command: {err}")
        raise SystemExit(1)
