"""
Functions for obtaining system-level version information.

Copyright 2019 Cray Inc. All Rights Reserved.
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


LOGGER = logging.getLogger(__name__)


def get_value_streams(relfile='/opt/cray/etc/release'):
    """Returns the version information within the release file.

    Shasta stores release information for various value-streams in a file
    located at /opt/cray/etc/release. This file is stored in YAML format,
    and this function reads the data into a dictionary where the keys are the
    names of the value-streams, and the values are the versions for each.

    Args:
        relfile (str): Path to release file that contains information. This
            file should be in yaml format.

    Returns:
        A dictionary containing the name of the value-stream and its
        associated version(s). If the appropriate key for version does not
        exist, then the dictionary will hold a value of None for that value-
        stream.

        If the file could not be read, or the file was in a non-yaml format,
        then this function will return a defaultdict which will supply the
        value 'ERROR' for any entries.
    """

    reldata = defaultdict(lambda: 'ERROR')
    default = defaultdict(lambda: 'ERROR')
    relstring = ''

    try:
        with open(relfile, 'r') as f:
            relstring = f.read()
    except FileNotFoundError:
        LOGGER.warning('No release file at {} .'.format(relfile))
        return default
    except PermissionError:
        LOGGER.error('Unable to read {} due to permission issue.'.format(relfile))
        return default

    # return {} if file doesn't match yaml format
    try:
        data = yaml.safe_load(relstring)
    except yaml.parser.ParserError:
        LOGGER.error('The release file, {}, has non-yaml format.'.format(relfile))
        return default

    # Return empty-dict if file is empty.
    if data is None:
        LOGGER.error('The release file {} is empty.'.format(relfile))
        return {}

    try:
        for entry in data['products']:
            try:
                reldata[entry] = data['products'][entry]['version']
            except KeyError:
                LOGGER.warning('The product entry {} in {} has no "version" field.'.format(entry, relfile))
                reldata[entry] = None
    except KeyError:
        LOGGER.error('There is no "products" section within {} .'.format(relfile))
        return default

    return reldata


def get_site_data(sitefile):
    """Get site-specific information from the Shasta sitefile.

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
        sitefile = get_config_value('site_info')

    try:
        with open(sitefile, 'r') as f:
            s = f.read()
    except FileNotFoundError:
        LOGGER.error('Sitefile {} not found.'.format(sitefile))
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


def get_interconnects():
    """Get string of unique interconnect types across Shasta.

    Returns:
        A space-separated string of interconnect types.
        None is returned if no interconnects were found.
        'ERROR' is returned if the function encountered an error.
    """

    networks = []

    client = HSMClient()

    try:
        response = client.get('State', 'Components')
    except APIError as err:
        LOGGER.error('Request to HSM API failed: {}.'.format(err))
        return 'ERROR'

    try:
        components = response.json()
    except ValueError as err:
        LOGGER.error('Failed to parse JSON from component state response: %s', err)
        return 'ERROR'

    try:
        for component in components['Components']:
            if 'NetType' in component:
                networks.append(component['NetType'])
    except KeyError:
        LOGGER.error('No components returned.')
        return 'ERROR'

    if not networks:
        LOGGER.warning('No interconnects found.')
        return None

    # remove redundant network types
    networks = sorted(set(networks))

    return ' '.join(networks)


def get_build_version():
    return None


def get_sles_version():
    """SLES version info is found in /etc/os-release on Shasta systems.

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
    """Collect generic information about the Shasta system.

    This is the function that 'decides' what components (and their versions)
    adequately describe the 'version' of a Shasta system.

    Args:
        substr: Only return information about docker images whose name or id
            contains the substr.
    Returns:
        A sorted dictionary that contains version information about the
        various Shasta system components.
    """

    funcs = OrderedDict()
    ret = OrderedDict()
    value_streams = get_value_streams()
    zypper_versions = get_zypper_versions(
        ['cray-lustre-client', 'slurm-slurmd', 'pbs-crayctldeploy']
    )
    sitedata = get_site_data(sitefile)

    # keep this list in ascii-value sorted order on the keys.
    funcs['Build version'] = get_build_version
    funcs['CLE version'] = lambda: value_streams['CLE']
    funcs['General'] = lambda: value_streams['general']
    funcs['Interconnect'] = get_interconnects
    funcs['Kernel'] = get_kernel_version
    funcs['Lustre'] = lambda: zypper_versions['cray-lustre-client']
    funcs['PBS version'] = lambda: zypper_versions['pbs-crayctldeploy']
    funcs['PE'] = lambda: value_streams['PE']
    funcs['SLES version'] = get_sles_version
    funcs['Sat'] = lambda: value_streams['sat']
    funcs['Serial number'] = lambda: sitedata['Serial number']
    funcs['Site name'] = lambda: sitedata['Site name']
    funcs['Slingshot'] = lambda: value_streams['slingshot']
    funcs['Sma'] = lambda: value_streams['sma']
    funcs['Sms'] = lambda: value_streams['sms']
    funcs['System install date'] = lambda: sitedata['System install date']
    funcs['System name'] = lambda: sitedata['System name']
    funcs['System type'] = lambda: sitedata['System type']
    funcs['Urika'] = lambda: value_streams['urika']
    funcs['Slurm version'] = lambda: zypper_versions['slurm-slurmd']

    for func in funcs:
        if substr in func:
            ret[func] = str(funcs[func]())

    return ret
