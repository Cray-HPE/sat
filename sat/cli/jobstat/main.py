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
import re
import textwrap

from csm_api_client.service.gateway import APIError

from sat.apiclient.jobstat import JobstatClient
from sat.report import Report
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)


def wrap_long_row_lines(row):
    """Wrap long lines in the output.
    Args:
        row (dict): A row in the application data returned
            from the State Checker.
    Returns:
        None. Modifies row in place.
    """
    if row.get('apid'):
        row['apid'] = row['apid'][:8]
    if row.get('jobid'):
        row['jobid'] = textwrap.fill(text=row['jobid'], width=20)
    if row.get('command'):
        tempstr = textwrap.fill(text=row['command'], width=40)
        tempstr = re.sub(r'\A/.*/mpiexec', 'mpiexec', tempstr, 1)
        tempstr = re.sub(r'\A/.*/aprun', 'aprun', tempstr, 1)
        row['command'] = tempstr
    if row.get('node_list'):
        # number of nodes to print on each line
        length = 4
        nodelist = re.sub(r'nid', '', row['node_list'])
        nodelist = nodelist.split(',')
        nodelist = [nid.lstrip('0') for nid in nodelist]
        row['node_list'] = '\n'.join(
            ','.join(e)
            for e in [nodelist[i: i + length] for i in range(0, len(nodelist), length)]
        )


def do_jobstat(args):
    """Run the jobstat command with the given arguments.
    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.
    """
    state_checker_client = JobstatClient(SATSession())
    try:
        application_data = state_checker_client.get_all()
        if not application_data:
            return
        report = Report(
            tuple(application_data[0].keys()),
            None,
            args.sort_by,
            args.reverse,
            filter_strs=args.filter_strs,
            display_headings=args.fields,
            print_format=args.format,
        )

        for row in application_data:
            if args.format == 'pretty':
                LOGGER.debug('Applying formatting to node_list and command fields.')
                wrap_long_row_lines(row)
            report.add_row(row)
        print(report)
    except APIError as err:
        LOGGER.error(err)
        raise SystemExit(1)
