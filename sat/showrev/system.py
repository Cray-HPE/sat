"""
Functions for obtaining system-level version information.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import configparser
import os
import socket
from collections import OrderedDict


def get_lustre_version():
    return 'TBD'


def get_kernel_version():
    return os.uname().release


def get_site_name():
    return 'TBD'


def get_system_type():
    return 'TBD'


def get_interconnect():
    return 'TBD'


def get_install_date():
    return 'TBD'


def get_system_name():
    return socket.gethostname()


def get_build_version():
    return 'TBD'


def get_sles_version():
    """SLES version info is found in /etc/os-release on Shasta systems.

    Returns:
        A string containing the NAME and VERSION field as found in the file
        /etc/os-release .
    """
    osrel_path = '/etc/os-release'

    if not os.path.exists(osrel_path):
        return 'ERROR: {} does not exist.'.format(osrel_path)

    with open(osrel_path, 'r') as f:
        config_string = '[default]\n' + f.read()

    cp = configparser.ConfigParser(interpolation=None)
    cp.read_string(config_string)

    ret = '{} {}'.format(cp.get('default', 'NAME'), cp.get('default', 'VERSION')).replace('"', '')

    return ret


def get_cle_version():
    return 'TBD'


def get_wlm_version():
    return 'TBD'


def get_system_version(substr=''):
    """Collect generic information about the Shasta system.

    Args:
        substr: Only return information about docker images whose name or id
            contains the substr.
    Returns:
        An ordered dictionary that contains version information about the
        various Shasta system components.

        Returns None if an error occurred.
    """
    sysvers = OrderedDict()
    funcs = OrderedDict()

    funcs['Lustre'] = get_lustre_version
    funcs['Kernel'] = get_kernel_version
    funcs['Site name'] = get_site_name
    funcs['System type'] = get_system_type
    funcs['Interconnect'] = get_interconnect
    funcs['Install date'] = get_install_date
    funcs['System name'] = get_system_name
    funcs['Build version'] = get_build_version
    funcs['SLES version'] = get_sles_version
    funcs['CLE version'] = get_cle_version
    funcs['WLM version'] = get_wlm_version

    for func in funcs:
        if not substr or substr in func:
            try:
                sysvers[func] = funcs[func]()
            except Exception as e:
                print('ERROR: Function {} raised {}'.format(func, str(e)))
                return None

    return sysvers
