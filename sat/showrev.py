"""
Contains functions for the 'showrev' subcommand.

Copyright 2019, Cray Inc. All Rights Reserved.
"""

import os
import socket
import configparser
import subprocess
import shlex
from collections import OrderedDict

import docker


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


def get_dockers(substr=''):
    """Return names and version info from installed images.

    Args:
        substr: Only return information about docker images whose name or id
            contains the substr.
    Returns:
        A list of lists; each containing 3+ entries. The first entry contains
        the docker image id. The second contains the image's base-name. The
        third on to the end contain the image's versions.
    """

    client = docker.from_env()

    ret = []
    for image in client.images.list():
        tags = image.tags
        if len(tags) > 0:

            # Docker id is returned like 'sha256:fffffff'
            full_id = image.id.split(':')[-1]
            short_id = image.short_id.split(':')[-1]
            fields = tags[0].split(':')
            name = fields[-2].split('/')[-1]

            if not substr or substr in name or substr in full_id:
                versions = []
                for tag in tags:
                    version = tag.split(':')[-1]
                    if version not in versions and version != 'latest':
                        versions.append(version)

                if not versions:
                    versions.append('latest')

                ret.append([short_id, name] + versions)

    return ret


def get_rpms(substr=''):
    """Collect version information about installed rpms.

    Returns a list of all rpms and their versions that are installed on
    the system.

    Args:
        substr: Only return packages that contain the substr.
    Returns:
        List of lists where each entry contains the name of an rpm and its
        associated version.

        Returns None if an error occurred.
    """

    format = '"%{NAME} %{VERSION}\n"'
    cmd = 'rpm -qa --queryformat {}'.format(format)
    toks = shlex.split(cmd)

    packages = []
    try:
        packages = subprocess.check_output(toks).decode('utf-8').splitlines()
    except Exception as e:
        print('ERROR: Command {} failed - subprocess raised {}'.format(cmd, str(e)))
        return None

    rpms = []
    for line in packages:
        rpms.append(line.split())

    if substr:
        rpms[:] = [x for x in rpms if substr in x[0]]

    return rpms
