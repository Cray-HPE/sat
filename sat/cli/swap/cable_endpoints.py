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
Contains functions for managing cable endpoints using the p2p file.
"""

import csv
import logging
import os
import re
import shlex
import subprocess
import warnings
from yaml import YAMLLoadWarning

from kubernetes.client import CoreV1Api
from kubernetes.client.rest import ApiException
from kubernetes.config import load_kube_config, ConfigException

LOGGER = logging.getLogger(__name__)

JACK_XNAME_REGEX = re.compile(r'^x\d+c\d+r\d+j\d+$')


class CableEndpoints:
    """Manages cable endpoints using data from the Shasta p2p file."""

    def __init__(self):
        self.p2p_file = 'Shasta_system_hsn_pt_pt.csv'
        self.src_dir = '/opt/cray/etc/sct/'
        self.dest_dir = '/sat/'
        self.cables = None

    def copy_shasta_p2p_file(self):
        """Copy Shasta p2p file from the fabric-manager pod.

        Returns:
            True if p2p file was copied and is available in the sat container.
            False if there is an error copying the p2p file.
        """

        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            LOGGER.error('Failed to load kubernetes config: {}'.format(err))
            return False

        namespace = 'services'
        container = 'slingshot-fabric-manager'
        pod_label = f'app.kubernetes.io/name={container}'
        try:
            dump = CoreV1Api().list_namespaced_pod(namespace, label_selector=pod_label)
            pod = dump.items[0].metadata.name
        except ApiException as err:
            LOGGER.error('Could not retrieve list of pods: {}'.format(err))
            return False
        except IndexError:
            LOGGER.info(f'No pods with label {pod_label} could be found.')
            return False

        src_file = os.path.join(self.src_dir, self.p2p_file)
        dest_file = os.path.join(self.dest_dir, self.p2p_file)
        cmd = f'kubectl -n {namespace} -c {container} cp {pod}:{src_file} {dest_file}'
        LOGGER.info(f'Running {cmd}')

        try:
            subprocess.check_call(shlex.split(cmd),
                                  stdout=subprocess.DEVNULL,
                                  stderr=subprocess.STDOUT)
        except (subprocess.CalledProcessError, OSError) as err:
            LOGGER.error('Exception when copying p2p file: {}'.format(err))
            return False

        if not os.path.isfile(dest_file):
            LOGGER.error(f'File {dest_file} does not exist')
            return False

        return True

    def load_cables_from_p2p_file(self):
        """Load cable data from Shasta p2p file.

        Loads keys: src_conn_a, src_conn_b, dst_conn_a, dst_conn_b.
        Replaces any '.' with '' in the xname.

        Returns:
            True if cable data was successfully created from the p2p file.
            False if any errors.
        """

        if not self.copy_shasta_p2p_file():
            LOGGER.error(f'Error copying file from fabric manager pod: {self.p2p_file}')
            return False

        csv_filename = os.path.join(self.dest_dir, self.p2p_file)
        cables = []
        header = []
        try:
            with open(csv_filename, 'r', encoding='utf-8-sig') as csvfile:
                # Skip preamble
                skip_lines = 0
                for line in csvfile.readlines():
                    skip_lines += 1
                    if line.startswith('cable_id'):
                        header = line.split(',')
                        break
        except OSError as err:
            LOGGER.error(f'Unable to open file {csv_filename} for reading: {err}')
            return False

        try:
            with open(csv_filename, 'r', encoding='utf-8-sig') as csvfile:
                for _ in range(skip_lines):
                    next(csvfile)
                for row in csv.DictReader(csvfile, fieldnames=header):
                    try:
                        cable = {
                            'src_conn_a': row['src_conn_a'].replace('.', ''),
                            'src_conn_b': row['src_conn_b'].replace('.', ''),
                            'dst_conn_a': row['dst_conn_a'].replace('.', ''),
                            'dst_conn_b': row['dst_conn_b'].replace('.', '')
                        }
                        if cable not in cables:
                            cables.append(cable)
                    except KeyError as err:
                        LOGGER.error('Key %s for cable data missing from p2p file.', err)
        except OSError as err:
            LOGGER.error(f'Unable to open file {csv_filename} for reading: {err}')
            return False

        if not cables:
            return False

        self.cables = cables
        return True

    def get_cable(self, jack_xname):
        """Get the cable data for a jack xname.

        Args:
            jack_xname (str): The xname of the jack.

        Returns:
            A dictionary of cable data or None.
        """

        if self.cables is None:
            return None

        for cable in self.cables:
            if jack_xname in cable.values():
                return cable

        return None

    def get_linked_jack_list(self, jack_xname):
        """Get the linked jacks for a jack xname using the cable data.

        Only returns endpoints that are jack xnames, i.e., match JACK_XNAME_REGEX.

        Args:
            jack_xname (str): The xname of the jack.

        Returns:
            A list of str of jack xnames that are linked.
        """

        cable = self.get_cable(jack_xname)
        if cable is None:
            LOGGER.warning(f'Jack data for {jack_xname} not available from p2p file')
            return None

        return [jack for jack in cable.values() if re.match(JACK_XNAME_REGEX, jack)]

    def validate_jacks_using_p2p_file(self, jack_xnames):
        """Validate a list of jack xnames that match the format JACK_XNAME_REGEX.

        Uses the cable data from the p2p file to validate the jacks.
        Checks if all jacks are in the p2p file.
        If all jacks are in the p2p file, checks if all jacks are for the same single cable.

        Args:
            jack_xnames ([str]): A list of jack xnames.

        Returns:
            True or False if valid or not.
        """

        if self.cables is None:
            LOGGER.warning('No cable data available from p2p file')
            return False

        # check for all jacks in p2p file
        all_jacks_found = True
        for jack in jack_xnames:
            cable = self.get_cable(jack)
            if cable is None:
                LOGGER.warning(f'Jack data for {jack} not available from p2p file')
                all_jacks_found = False

        if not all_jacks_found:
            return False

        # all jacks were found, so check if they are for a single cable
        cable = None
        for jack in jack_xnames:
            if cable is None:
                cable = self.get_cable(jack)
            elif self.get_cable(jack) != cable:
                LOGGER.warning(f'Jacks {",".join(jack_xnames)} are not connected by a single cable')
                return False

        return True
