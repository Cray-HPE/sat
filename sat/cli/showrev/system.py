"""
Functions for obtaining system-level version information.

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

import configparser
import logging
import os
import shlex
import socket
import subprocess
import xml.etree.ElementTree as ET
from collections import OrderedDict
from collections import defaultdict

import yaml

from sat.apiclient import APIError, HSMClient
from sat.config import get_config_value
from sat.session import SATSession


LOGGER = logging.getLogger(__name__)


def get_site_data(sitefile):
    """Get site-specific information from the sitefile.

    Args:
        sitefile: Specify custom sitefile to load. It must be in yaml format.

    Returns:
        A defaultdict which contains the entries within the sitefile. The
        default value for these entries is None.

        If an error occurred while reading the sitefile, then the error
        will be logged and this dict will default its entries to 'ERROR'.
    """

    s = ''
    data = defaultdict(lambda: None)
    default = defaultdict(lambda: 'ERROR')

    if not sitefile:
        sitefile = get_config_value('general.site_info')

    try:
        with open(sitefile, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        LOGGER.error('Sitefile {} not found. '
                     'Run "sat setrev" to generate this file.'.format(sitefile))
        return default

    try:
        data.update(yaml.safe_load(s))
    except yaml.parser.ParserError:
        LOGGER.error('Site file {} is not in yaml format.'.format(sitefile))
        return default

    # use hostname if site name isn't specified
    if not data['System name']:
        try:
            data['System name'] = socket.gethostname()
        except Exception:  # TODO: find specific exception
            LOGGER.error('Site-file {} has no "System name", and gethostname query failed.'.format(sitefile))
            data['System name'] = 'ERROR'

    return data


def get_zypper_versions(packages):
    """Get version information about package as reported by zypper.

    The first found occurrence of the respective package name is what is
    entered for each package.

    Args:
        packages: List of package names. Should be whole package names.

    Returns:
        Dictionary where package-name => version. The entry for a package
        will be None if zypper indicated the package could not be found.
        The entry will be 'ERROR' if the zypper program isn't present, if
        zypper encountered an internal error, or if the query succeeded,
        but the output could not be parsed.

    Raises:
        subprocesses.CalledProcessErorr if the call to zypper encountered some
            sort of internal error.
    """

    versions = defaultdict(lambda: None)

    cmd = 'zypper --quiet --xmlout search -t package -xs'
    toks = shlex.split(cmd) + packages
    lines = ''
    root = None

    try:
        lines = subprocess.check_output(toks).decode('utf-8')

        try:
            root = ET.fromstring(lines)
        except ET.ParseError:
            LOGGER.error('Zypper output could not be parsed for package list {} .'.format(packages))
            return defaultdict(lambda: 'ERROR')
    except subprocess.CalledProcessError as cpe:

        if cpe.returncode == 6:
            # no repositories are defined
            LOGGER.warning('Zypper has no repositories configured.')
            return versions
        elif cpe.returncode == 104:
            # no matches
            LOGGER.warning('Zypper found no matches for any package in {}.'.format(packages))
            return versions
        else:
            # zypper had an internal error and we have a serious problem
            raise
    except FileNotFoundError:
        LOGGER.error('The zypper program is not present on this system.')
        return defaultdict(lambda: 'ERROR')

    try:
        for entry in root[0][0]:
            name = entry.attrib['name']
            try:
                if name not in versions:
                    versions[name] = entry.attrib['edition']
            except KeyError:
                LOGGER.error('Zypper did not report an "edition" for package {}.'.format(name))
                versions[name] = 'ERROR'
    except IndexError:
        LOGGER.error('Zypper did not report an xml-tree in expected format. No entries at depth 2')
        return defaultdict(lambda: 'ERROR')

    return versions


def get_kernel_version():
    return os.uname().release


def _get_hsm_components():
    """Helper used by get_interconnects.

    Returns:
        The json dict from HSMClient.get().
    """
    client = HSMClient(SATSession())

    try:
        response = client.get('State', 'Components')
    except APIError as err:
        LOGGER.error('Request to HSM API failed: {}.'.format(err))
        raise

    try:
        components = response.json()
    except ValueError as err:
        LOGGER.error('Failed to parse JSON from component state response: %s', err)
        raise

    try:
        return components['Components']
    except KeyError:
        LOGGER.error('No components returned.')
        raise


def get_interconnects():
    """Get string of unique interconnect types across the system.

    Returns:
        A space-separated string of interconnect types.
        None is returned if no interconnects were found.
        'ERROR' is returned if the function encountered an error
        when gathering component information.
    """

    networks = []

    try:
        components = _get_hsm_components()
    except (APIError, KeyError, ValueError):
        return ['ERROR']

    for component in components:
        if 'NetType' in component:
            networks.append(component['NetType'])

    if not networks:
        LOGGER.warning('No interconnects found.')
        return [None]

    # remove redundant network types
    networks = sorted(set(networks))

    return networks


def get_build_version():
    return None


def get_sles_version():
    """Gets SLES version info found in /etc/os-release.

    Returns:
        A string containing the NAME and VERSION field as found in the file
        /etc/os-release.
    """
    osrel_path = '/etc/os-release'

    try:
        with open(osrel_path, 'r') as f:
            config_string = '[default]\n' + f.read()
    except (FileNotFoundError, AttributeError):
        LOGGER.error('ERROR: Could not open {}.'.format(osrel_path))
        return 'ERROR'

    cp = configparser.ConfigParser(interpolation=None)
    cp.read_string(config_string)

    try:
        slesname = cp.get('default', 'NAME').replace('"', '')
        slesvers = cp.get('default', 'VERSION').replace('"', '')
        if slesname == '' or slesvers == '':
            LOGGER.error('ERROR: Empty SLES NAME or VERSION field in {}.'.format(osrel_path))
            return 'ERROR'
        else:
            return '{} {}'.format(slesname, slesvers)
    except configparser.NoOptionError:
        LOGGER.error('SLES NAME and VERSION fields not found in {}'.format(osrel_path))
        return 'ERROR'

    return 'ERROR'


def get_system_version(sitefile, substr=''):
    """Collects generic information about the system.

    This is the function that 'decides' what components (and their versions)
    adequately describe the 'version' of the system.

    Args:
        substr: Only return information about docker images whose name or id
            contains the substr.
    Returns:
        A list of lists that contains version information about the
        various system components.
    """

    zypper_versions = get_zypper_versions(
        ['cray-lustre-client', 'slurm-slurmd', 'pbs-crayctldeploy']
    )
    sitedata = get_site_data(sitefile)

    # keep this list in ascii-value sorted order on the keys.
    field_getters_by_name = OrderedDict([
        ('Build version', get_build_version),
        ('Interconnect', lambda: ' '.join(get_interconnects())),
        ('Kernel', get_kernel_version),
        ('Lustre', lambda: zypper_versions['cray-lustre-client']),
        ('PBS version', lambda: zypper_versions['pbs-crayctldeploy']),
        ('SLES version', get_sles_version),
        ('Serial number', lambda: sitedata['Serial number']),
        ('Site name', lambda: sitedata['Site name']),
        ('Slurm version', lambda: zypper_versions['slurm-slurmd']),
        ('System install date', lambda: sitedata['System install date']),
        ('System name', lambda: sitedata['System name']),
        ('System type', lambda: sitedata['System type']),
    ])

    return [[field_name, field_getter()]
            for field_name, field_getter in field_getters_by_name.items()
            if substr in field_name]
