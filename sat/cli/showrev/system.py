#
# MIT License
#
# (C) Copyright 2019-2023 Hewlett Packard Enterprise Development LP
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
Functions for obtaining system-level version information.
"""

import logging
import shlex
import subprocess
from urllib3.exceptions import MaxRetryError
from collections import defaultdict

from boto3.exceptions import Boto3Error
from botocore.exceptions import BotoCoreError, ClientError
from csm_api_client.k8s import load_kube_api
from kubernetes.client.exceptions import ApiException
from kubernetes.config import ConfigException
import yaml

from sat.apiclient import APIError, HSMClient
from sat.config import get_config_value
from sat.cli.setrev.site_fields import SITE_FIELDS
from sat.session import SATSession
from sat.util import get_s3_resource, S3ResourceCreationError


LOGGER = logging.getLogger(__name__)


def get_site_data(sitefile):
    """Get site-specific information from the sitefile, using S3 if possible.

    Args:
        sitefile: Specify custom sitefile to load. It must be in yaml format.

    Returns:
        A defaultdict which contains the entries within the sitefile. The
        default value for these entries is None.

        If an error occurred while reading the sitefile, then the error
        will be logged and this dict will default its entries to 'ERROR'.
    """
    data = defaultdict(lambda: None)
    default = defaultdict(lambda: 'ERROR')
    if not sitefile:
        sitefile = get_config_value('general.site_info')
    try:
        s3 = get_s3_resource()
    except S3ResourceCreationError as err:
        LOGGER.warning('Error creating S3 resource: %s', err)
    else:
        s3_bucket = get_config_value('s3.bucket')

        try:
            LOGGER.debug('Downloading %s from S3 (bucket: %s)', sitefile, s3_bucket)
            s3.Object(s3_bucket, sitefile).download_file(sitefile)
        except (BotoCoreError, ClientError, Boto3Error) as err:
            LOGGER.error('Unable to download site info file %s from S3. Attempting to read from cached copy. '
                         'Error: %s', sitefile, err)

    try:
        with open(sitefile, 'r') as f:
            site_info = yaml.safe_load(f)
            if site_info is None:
                LOGGER.error('Site info file "%s" is empty; run `sat setrev` to populate.',
                             sitefile)
                return default
            data.update(site_info)
    except FileNotFoundError:
        LOGGER.error('Site information file %s not found. '
                     'Run "sat setrev" to generate this file.', sitefile)
        return default
    except OSError as err:
        LOGGER.error('Unable to open site information file %s: %s', sitefile, err)
        return default
    except yaml.parser.ParserError:
        LOGGER.error('Site file %s is not in yaml format.', sitefile)
        return default

    return data


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


def get_slurm_version():
    """Get version of Slurm.

    Returns:
        String representing version of Slurm. Returns None if something
        went wrong.
    """

    try:
        k8s_api = load_kube_api()
    except ConfigException as err:
        LOGGER.error('Reading kubernetes config: {}'.format(err))
        return None

    ns = 'user'
    try:
        dump = k8s_api.list_namespaced_pod(ns, label_selector='app=slurmctld')
        pod = dump.items[0].metadata.name
    except MaxRetryError as err:
        LOGGER.error('Error connecting to Kubernetes to retrieve list of pods: %s', err)
        return None
    except ApiException as err:
        LOGGER.error('Could not retrieve list of pods: {}'.format(err))
        return None
    except IndexError:
        LOGGER.info('No pods with label app=slurmctld could be found.')
        return None

    cmd = 'kubectl exec -n {} -c slurmctld {} -- sinfo --version'.format(ns, pod)
    toks = shlex.split(cmd)

    try:
        output = subprocess.check_output(toks)
        version = output.decode('utf-8').splitlines()[0]
    except IndexError:
        LOGGER.error('Command to print slurm version returned no stdout.')
        return None
    except subprocess.CalledProcessError as e:
        LOGGER.error('Exception when querying slurm version: {}'.format(e))
        return None

    return version


def get_system_version(sitefile):
    """Collects generic information about the system.

    This is the function that 'decides' what components (and their versions)
    adequately describe the 'version' of the system.

    Returns:
        A list of lists that contains version information about the
        various system components.
    """

    sitedata = get_site_data(sitefile)

    # Keep this list in the order specified in SITE_FIELDS
    system_rows = [
        (site_field.name, sitedata[site_field.name])
        for site_field in SITE_FIELDS
    ]

    # Add the interconnect and Slurm versions
    # TODO: consider removing these.
    system_rows.extend([
        ('Interconnect', ' '.join(get_interconnects())),
        ('Slurm version', get_slurm_version())
    ])

    # Filter out null values
    return [row for row in system_rows if row[1] is not None]
