#
# MIT License
#
# (C) Copyright 2021 Hewlett Packard Enterprise Development LP
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
Entry point for the slscheck subcommand.
"""

import logging
import re

from sat.apiclient import APIError, HSMClient, SLSClient
from sat.config import get_config_value
from sat.constants import BMC_TYPES, MISSING_VALUE
from sat.report import Report
from sat.session import SATSession
from sat.xname import XName


HEADERS = (
    'xname',
    'SLS Type',
    'SLS Class',
    'SLS Role',
    'SLS Subrole',
    'Comparison Result'
)

LOGGER = logging.getLogger(__name__)

ERR_SLS_API_FAILED = 1
ERR_HSM_API_FAILED = 2


def create_hw_component_dict(xname, hw_type, hw_class, hw_role, hw_subrole):
    """Creates a dictionary for a hardware component.

    Args:
        xname (str): The component xname.
        hw_type (str): The component type or None.
        hw_class (str): The component class or None.
        hw_role (str): The component role or None.
        hw_subrole (str): The component subrole or None.

    Returns:
        hw_info (dict): A dictionary of component data for an xname.
    """

    hw_info = {}
    if not xname:
        return hw_info

    hw_info['Xname'] = XName(xname)
    if hw_type:
        hw_info['Type'] = hw_type
    if hw_class:
        hw_info['Class'] = hw_class
    if hw_role:
        hw_info['Role'] = hw_role
    if hw_subrole:
        hw_info['SubRole'] = hw_subrole

    return hw_info


def create_sls_hw_component_dicts(hardware, include_types):
    """Creates dictionaries for SLS hardware for an xname and optionally for the parent.

    Args:
        hardware (dict): A dictionary describing an SLS hardware component from the SLS API.
        include_types ([str]): A list of SLS types to include.

    Returns:
        hw_info (dict): A dictionary of component data for an xname.
        parent_hw_info (dict): A dictionary of component data for a parent xname.
    """

    hw_info = {}
    parent_hw_info = {}
    xname = hardware.get('Xname')
    sls_type = hardware.get('TypeString')
    if not xname or not sls_type:
        return hw_info, parent_hw_info

    # Use MISSING_VALUE for missing strings so that this data is displayed correctly
    sls_class = hardware.get('Class', MISSING_VALUE)
    if sls_type in include_types:
        # Add b0 to xname if the ChassisBMC xname does not end in b followed by a digit
        if sls_type == 'ChassisBMC' and not re.match(r'^.*b\d+$', xname):
            xname = xname + 'b0'
        extra = hardware.get('ExtraProperties', {})
        sls_role = extra.get('Role', MISSING_VALUE)
        sls_subrole = extra.get('SubRole', MISSING_VALUE)
        hw_info = create_hw_component_dict(
            xname,
            sls_type,
            sls_class,
            sls_role,
            sls_subrole)

    # In SLS, there is no NodeBMC value for TypeString
    # The NodeBMC data is created from the SLS data returned for TypeString="Node"
    # The xname of the NodeBMC is the Parent of the Node in SLS
    # For Node, add parent xname as a NodeBMC
    if sls_type == 'Node' and 'NodeBMC' in include_types:
        xname = hardware.get('Parent')
        if xname:
            sls_type = 'NodeBMC'
            sls_role = MISSING_VALUE
            sls_subrole = MISSING_VALUE
            parent_hw_info = create_hw_component_dict(
                xname,
                sls_type,
                sls_class,
                sls_role,
                sls_subrole)

    return hw_info, parent_hw_info


def create_sls_hw_to_check(sls_hardware, include_types):
    """Creates a dictionary of SLS components from the dictionary of sls_hardware.

    Args:
        sls_hardware (dict): A dictionary of hardware components from the SLS API.
        include_types ([str]): A list of SLS types to include.

    Returns:
        sls_hw_to_check (dict): A dictionary with SLS component data with xnames as the keys and
           component dictionary as values.
           An example of a key/value pair: {
               'x3000c0s21b0n0': {
                   'Xname': x3000c0s21b0n0,
                   'Type': 'Node',
                   'Class': 'River',
                   'Role': 'Management'
                   'SubRole': 'Storage'
               }
           }
    """

    sls_hw_to_check = {}
    for hardware in sls_hardware.values():
        hw_info, parent_hw_info = create_sls_hw_component_dicts(hardware, include_types)
        if hw_info:
            xname = hardware.get('Xname')
            if xname:
                sls_hw_to_check[xname] = hw_info
        if parent_hw_info:
            xname = hardware.get('Parent')
            if xname:
                sls_hw_to_check[xname] = parent_hw_info

    return sls_hw_to_check


def create_hsm_hw_to_crosscheck(hsm_hw_list):
    """Creates a dictionary of HSM components or Redfish endpoints from a list of dictionaries.

    Args:
        hsm_hw_list ([dict]): A list of dictionaries of hardware components or Redfish endpoints
            from the HSM API.

    Returns:
        hsm_hw_to_crosscheck (dict): A dictionary with HSM data with xnames as the keys and
           component or Redfish endpoint dictionary as values.
    """

    hsm_hw_to_crosscheck = {}
    for hsm_hw in hsm_hw_list:
        cid = hsm_hw.get('ID')
        if not cid:
            continue
        hw_info = create_hw_component_dict(
            cid,
            hsm_hw.get('Type'),
            hsm_hw.get('Class'),
            hsm_hw.get('Role'),
            hsm_hw.get('SubRole')
        )
        if hw_info:
            hsm_hw_to_crosscheck[cid] = hw_info

    return hsm_hw_to_crosscheck


def add_results(sls_hw, comparison_results, crosscheck_results):
    """Adds the results from comparing an SLS component with HSM to a table of cross-check results.

    Args:
        sls_hw (dict): A dictionary with SLS component data that has been cross-checked.
        comparison_results ([str]): A list of strings containing results of the cross-check.
        crosscheck_results ([list]): A list of lists where the sls_hw data and the
            comparison_results are added.

    Returns:
        None
    """

    for comparison_result in comparison_results:
        result = list(sls_hw.values())
        result.append(comparison_result)
        crosscheck_results.append(result)


def create_components_crosscheck_results(include_consistent, checks, xname, sls_hw, hsm_components):
    """Creates a list of results from comparing an SLS component with HSM components.

    Args:
        include_consistent (bool): If True include results for SLS components that are
            consistent with HSM.
        checks ([str]): A list of checks to perform.
        xname (xname): The xname of the component.
        sls_hw (dict): A dictionary with SLS component data to cross-check.
        hsm_components (dict): A dictionary with HSM component data.
            The dictionary has xnames as the keys and associated component data as
            dictionary values.

    Returns:
        comparison_results ([str]): A list of strings containing results of a cross-check
            between one SLS component and HSM components.
    """

    comparison_results = []
    if not hsm_components:
        return comparison_results

    hsm_component = hsm_components.get(xname)
    if not hsm_component:
        if 'Component' in checks:
            comparison_results.append('SLS component missing in HSM Components')
        return comparison_results

    checks_to_keys = {
        'Component': ['Type'],
        'Class': ['Class'],
        'Role': ['Role', 'SubRole']
    }

    for check, fields in checks_to_keys.items():
        if check not in checks:
            continue
        for field in fields:
            sls_value = sls_hw.get(field, MISSING_VALUE)
            hsm_value = hsm_component.get(field, MISSING_VALUE)
            if sls_value != hsm_value:
                comparison_results.append(f'{field} mismatch: SLS:{sls_value},HSM:{hsm_value}')

    if include_consistent and not comparison_results:
        comparison_results.append('SLS component consistent with HSM Component')

    return comparison_results


def create_redfish_endpoints_crosscheck_results(include_consistent, xname, sls_hw,
                                                hsm_redfish_endpoints):
    """Creates a list of results from comparing an SLS component with HSM Redfish endpoints.

    Args:
        include_consistent (bool): If True include results for SLS components that are
            consistent with HSM.
        xname (xname): The xname of the component.
        sls_hw (dict): A dictionary with SLS component data to cross-check.
        hsm_redfish_endpoints (dict): A dictionary with HSM Redfish endpoint data for BMCs.
            The dictionary has xnames as the keys and associated component data as
            dictionary values.

    Returns:
        comparison_results ([str]): A list of strings containing results of a cross-check
            between one SLS component and HSM Redfish endpoints.
    """

    comparison_results = []
    if not hsm_redfish_endpoints:
        return comparison_results
    if sls_hw['Type'] not in BMC_TYPES:
        return comparison_results

    hsm_endpoint = hsm_redfish_endpoints.get(xname)
    if not hsm_endpoint:
        comparison_results.append('SLS component missing in HSM Redfish Endpoints')
    elif include_consistent:
        comparison_results.append('SLS component consistent with HSM Redfish Endpoint')

    return comparison_results


def create_crosscheck_results(include_consistent, checks, sls_hw_to_check,
                              hsm_components, hsm_redfish_endpoints):
    """Creates a table of results of a cross-check between SLS and HSM.

    Args:
        include_consistent (bool): If True include results for SLS components that are
            consistent with HSM.
        checks ([str]): A list of checks to perform.
        sls_hw_to_check (dict): A dictionary with SLS component data to cross-check.
            The dictionary has xnames as the keys and associated component data as
            dictionary values.
        hsm_components (dict): A dictionary with HSM component data.
            The dictionary has xnames as the keys and associated component data as
            dictionary values. If None, then the checks against HSM components are skipped.
        hsm_redfish_endpoints (dict): A dictionary with HSM Redfish endpoint data for BMCs.
            The dictionary has xnames as the keys and associated component data as
            dictionary values. If None, then the checks against HSM Redfish endpoints are
            skipped.

    Returns:
        crossscheck_results ([list]): A list of lists containing results of a cross-check
            between SLS components and HSM components and/or Redfish endpoints.
    """

    crosscheck_results = []

    for xname, sls_hw in sls_hw_to_check.items():
        if hsm_components:
            comparison_results = create_components_crosscheck_results(
                include_consistent,
                checks,
                xname,
                sls_hw,
                hsm_components
            )
            add_results(
                sls_hw,
                comparison_results,
                crosscheck_results
            )

        if hsm_redfish_endpoints:
            comparison_results = create_redfish_endpoints_crosscheck_results(
                include_consistent,
                xname,
                sls_hw,
                hsm_redfish_endpoints
            )
            add_results(
                sls_hw,
                comparison_results,
                crosscheck_results
            )

    return crosscheck_results


def do_slscheck(args):
    """Performs a cross-check between SLS and HSM.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit(1): if request to SLS API fails.
        SystemExit(2): if request to HSM API fails.
    """

    # Use same session for both SLSClient and HSMClient
    session = SATSession()

    sls_client = SLSClient(session)
    try:
        sls_hardware = sls_client.get_hardware()
    except APIError as err:
        LOGGER.error('Request to SLS API failed: %s', err)
        raise SystemExit(ERR_SLS_API_FAILED)

    hsm_components = None
    hsm_redfish_endpoints = None

    hsm_client = HSMClient(session)
    try:
        if any(check in args.checks for check in ['Component', 'Class', 'Role']):
            hsm_components = create_hsm_hw_to_crosscheck(hsm_client.get_all_components())

        if 'RFEndpoint' in args.checks:
            hsm_redfish_endpoints = create_hsm_hw_to_crosscheck(
                hsm_client.get_bmcs_by_type(check_keys=False))
    except APIError as err:
        LOGGER.error('Request to HSM API failed: %s', err)
        raise SystemExit(ERR_HSM_API_FAILED)

    sls_hw_to_check = create_sls_hw_to_check(
        sls_hardware,
        args.types
    )

    crosscheck_results = create_crosscheck_results(
        args.include_consistent,
        args.checks,
        sls_hw_to_check,
        hsm_components,
        hsm_redfish_endpoints
    )

    report = Report(
        HEADERS, None,
        args.sort_by, args.reverse,
        get_config_value('format.no_headings'),
        get_config_value('format.no_borders'),
        filter_strs=args.filter_strs,
        display_headings=args.fields,
        print_format=args.format)
    report.add_rows(crosscheck_results)

    print(report)
