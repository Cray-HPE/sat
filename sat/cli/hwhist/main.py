"""
Entry point for the hwhist subcommand.

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
from sat.config import get_config_value
from sat.constants import MISSING_VALUE
from sat.report import Report
from sat.session import SATSession

from sat.cli.hwhist.hwhist_fields import (
    BY_FRU_FIELD_MAPPING,
    BY_LOCATION_FIELD_MAPPING
)


LOGGER = logging.getLogger(__name__)


def make_raw_table(hw_history, field_mapping):
    """Create a table of hardware history data for components from HSM API data.

    Args:
        hw_history ([dict]): A list of dictionaries with component history data.
        field_mapping (OrderedDict): A dictionary of keys for hw_history
           with lambda functions to extract values.

    Returns:
        A list of lists containing hardware history data.
    """

    raw_table = []
    for component in hw_history:
        if not component.get('ID') or not component.get('History'):
            continue
        for event in component.get('History'):
            raw_table.append([extractor(event)
                              for extractor in field_mapping.values()])

    return raw_table


def do_hwhist(args):
    """Reports hardware component history from HSM inventory history.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None
    """

    if args.xnames and args.fruids:
        LOGGER.error('The fruid option is not valid with the xname option.')
        raise SystemExit(1)
    if args.xnames and args.by_fru:
        LOGGER.error('The xname option is not valid with the by-fru option.')
        raise SystemExit(1)

    id_args = None
    if args.fruids:
        id_args = set(arg for arg in args.fruids if arg != '')
    if args.xnames:
        id_args = set(arg for arg in args.xnames if arg != '')

    by_fru = args.by_fru
    if args.fruids:
        by_fru = True

    if by_fru:
        field_mapping = BY_FRU_FIELD_MAPPING
    else:
        field_mapping = BY_LOCATION_FIELD_MAPPING

    hsm_client = HSMClient(SATSession())

    try:
        hw_history = hsm_client.get_component_history(cids=id_args, by_fru=by_fru)
    except APIError as err:
        LOGGER.error('Request to HSM API failed: %s', err)
        raise SystemExit(1)

    report = Report(
        tuple(field_mapping.keys()), None,
        args.sort_by, args.reverse,
        get_config_value('format.no_headings'),
        get_config_value('format.no_borders'),
        filter_strs=args.filter_strs,
        display_headings=args.fields,
        print_format=args.format)

    raw_table = make_raw_table(hw_history, field_mapping)
    report.add_rows(raw_table)

    if id_args:
        cids_in_history = set(
            component.get('ID') for component in hw_history if component.get('History')
        )
        ids_not_included = id_args - cids_in_history
        if ids_not_included:
            LOGGER.warning(
                f'{ids_not_included} not available from HSM hardware component history API.'
            )

    print(report)
