#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
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
Functions for obtaining local OS version information.
"""
import configparser
import logging
import os


LOGGER = logging.getLogger(__name__)


def get_sles_version():
    """Gets SLES version info found in /opt/cray/sat/etc/os-release.

    If that path does not exist, then use /etc/os-release instead.

    Returns:
        A string containing the NAME and VERSION field as found in the file
        /etc/os-release.
    """
    osrel_path = '/opt/cray/sat/etc/os-release'
    if not os.path.isfile(osrel_path):
        LOGGER.debug('OS release path %s does not exist, using default', osrel_path)
        osrel_path = '/etc/os-release'

    try:
        with open(osrel_path, 'r') as f:
            config_string = '[default]\n' + f.read()
    except (FileNotFoundError, AttributeError, PermissionError):
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


def get_kernel_version():
    """Return the Kernel version as reported by `uname`"""
    return os.uname().release


def get_local_os_information():
    """Gets local OS information

    Returns:
        A list of tuples that contains version information about the
        local host Kernel version and OS distribution.
    """
    return [
        ('Kernel', get_kernel_version()),
        ('SLES', get_sles_version())
    ]
