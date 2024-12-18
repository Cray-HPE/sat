#
# MIT License
#
# (C) Copyright 2022-2024 Hewlett Packard Enterprise Development LP
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
# (C) Copyright 2022 Hewlett Packard Enterprise Development LP.

"""
Procedure for swapping a blade.
"""

import abc
import enum
from functools import wraps
import json
import logging

from csm_api_client.k8s import load_kube_api
from csm_api_client.service.gateway import APIError
from csm_api_client.service.hsm import HSMClient
import inflect
from kubernetes.client.exceptions import ApiException

from sat.apiclient.pcs import PCSClient
from sat.cached_property import cached_property
from sat.hms_discovery import (
    HMSDiscoveryCronJob,
    HMSDiscoveryError,
    HMSDiscoveryScheduledWaiter,
    HMSDiscoverySuspendedWaiter,
)
from sat.session import SATSession
from sat.util import prompt_continue
from sat.waiting import GroupWaiter, WaitingFailure
from sat.xname import XName

LOGGER = logging.getLogger(__name__)
inf = inflect.engine()


class BladeClass(enum.Enum):
    LIQUID = 'liquid-cooled'
    AIR = 'air-cooled'


def get_available_file(prefix, extension):
    """Get a file object which doesn't overwrite existing files

    The returned file object will have the given prefix and extension. If any
    file exists with the given prefix and extension, the prefix will be
    appended with a numeric suffix. If files exist with the given prefix,
    numeric suffix, and extension, the returned file object will be given the
    first unused numeric suffix.

    Args:
        prefix (str): the filename prefix
        extension (str): the extension to use with the filename

    Returns:
        file: a file object which does not overwrite existing files

    Raises:
        OSError: if a file with the given parameters cannot be opened
    """
    if extension.startswith('.'):
        extension = extension[1:]

    try:
        return open(f'{prefix}.{extension}', 'x')
    except FileExistsError:
        suffix = 1
        while True:
            try:
                return open(f'{prefix}-{suffix}.{extension}', 'x')
            except FileExistsError:
                suffix += 1


class BladeSwapError(Exception):
    """Represents an exception which occurs during blade swapping."""


class blade_swap_stage:
    """A decorator which logs when entering and exiting a function.

    Decorated functions will log the name of the stage before execution, catch
    APIErrors and re-raise them as BladeSwapErrors, and pass through all other
    exceptions.

    The `dry_run` class attribute may be set to True or False. If `dry_run` is
    True and a given decorated function's `allow_in_dry_run` attribute is
    False, then the stage's title will be logged, and the decorated function
    will not be called. If `dry_run` is False or if both `dry_run` and
    `allow_in_dry_run` are True, the stage's title will be logged, and the
    decorated function will be called as normal.

    Class Attributes:
        dry_run (bool): if True, run any decorated function only if its
            `allow_in_dry_run` parameter is True when it is called. If
            `allow_in_dry_run` is False, never run the decorated function if
            this attribute is True. If False, run any decorated function
            regardless of its `allow_in_dry_run` value.

    Attributes:
        stage_title (str): a sentence describing what the stage does.
            The title should always begin with a verb in the imperative mood,
            followed by the subject as the dependent clause. For example,
            "Disable the Redfish endpoints for NodeBMCs."
        allow_in_dry_run (bool): if True, allow this stage to run during a dry
            run. Otherwise, skip this stage during a dry run.
    """
    dry_run = False

    def __init__(self, stage_title, allow_in_dry_run=False):
        self.stage_title = stage_title
        self.allow_in_dry_run = allow_in_dry_run

    def __call__(self, fn):
        verb, sentence_object = self.stage_title.split(' ', maxsplit=1)

        @wraps(fn)
        def inner(*args, **kwargs):
            if self.dry_run and not self.allow_in_dry_run:
                LOGGER.info('Would %s %s', verb.lower(), sentence_object)
                return

            LOGGER.info('%s %s', inf.present_participle(verb), sentence_object)
            try:
                return fn(*args, **kwargs)
            except APIError as api_err:
                raise BladeSwapError(f'Error accessing API: {api_err}') from api_err

        return inner


class BladeSwapProcedure(abc.ABC):
    """A container class which encapsulates a procedure for adding or removing a blade"""
    action_verb = 'swap'  # This may be overridden in subclasses

    def __init__(self, args):
        """Constructor for a BladeSwapProcedure.

        Args:
            args (argparse.Namespace): the parsed command line arguments
        """
        self.xname = args.xname

        session = SATSession()
        self.hsm_client = HSMClient(session)
        self.pcs_client = PCSClient(session)

    @cached_property
    def blade_nodes(self):
        """list: metadata for the nodes on the blade retrieved from HSM"""
        return self.hsm_client.get_node_components(ancestor=self.xname)

    @cached_property
    def blade_node_bmcs(self):
        """list: metadata for the node BMCs on the blade retrieved from HSM"""
        return self.hsm_client.query_components(component=self.xname, type='NodeBMC')

    @cached_property
    def blade_class(self):
        """BladeClass: the class of the blade (BladeClass.LIQUID or BladeClass.AIR)

        "Mountain" and "Hill" blades are liquid-cooled, while "River" blades are
        air-cooled.

        Raises:
            BladeSwapError: if there is a problem determining the slot class
        """
        err_prefix = f'Could not determine blade class for {self.xname}'
        node_classes = set()
        for node in self.blade_nodes:
            try:
                node_classes.add(node['Class'])
            except KeyError as err:
                raise BladeSwapError(f'{err_prefix}: node {node["ID"]} is '
                                     f'missing {err} field in HSM')

        if len(node_classes) > 1:
            if set(node_class.lower() for node_class in node_classes) == {'mountain', 'hill'}:
                # This mismatch has been observed, and it doesn't change the procedure,
                # so we'll just log it and continue.
                LOGGER.warning('Multiple node classes detected on blade %s: %s',
                               self.xname, ', '.join(node_classes))
                return BladeClass.LIQUID
            else:
                reason = f'incompatible node classes: {", ".join(node_classes)}'
                raise BladeSwapError(f'{err_prefix}: {reason}')
        elif not node_classes:
            raise BladeSwapError(f'{err_prefix}: no nodes on blade')

        # In this case, there is just one node class on the blade
        hsm_class = node_classes.pop()
        if hsm_class.lower() in ('mountain', 'hill'):
            return BladeClass.LIQUID
        elif hsm_class.lower() == 'river':
            return BladeClass.AIR
        else:
            raise BladeSwapError(f'{err_prefix}: unsupported blade class "{hsm_class}"')

    @abc.abstractmethod
    def procedure(self):
        """The procedure which runs when performing the blade add or remove process

        Raises:
            BladeSwapError: if there is an error during the blade swap procedure
        """

    def run(self):
        """A helper function which runs the procedure and handles errors

        This helper simply calls procedure(), catches BladeSwapErrors, logs
        them, and exits.

        Returns: None

        Raises:
            SystemExit: if a BladeSwapError is raised during execution of the blade swap procedure
        """
        try:
            # This property can raise a BladeSwapError
            _ = self.blade_class
        except BladeSwapError as err:
            LOGGER.error(str(err))
            raise SystemExit(1)

        try:
            self.procedure()
        except BladeSwapError as err:
            LOGGER.error('Could not %s blade: %s', self.action_verb, err)
            raise SystemExit(1)


class RedfishEndpointDiscoveryWaiter(GroupWaiter):
    """Waiter which waits for a slot's Redfish endpoints to become populated"""

    def __init__(self, members, hsm_client, timeout, poll_interval=1, retries=0):
        self.hsm_client = hsm_client

        node_bmcs = set()
        for member in members:
            node_bmcs |= set(component['ID'] for component in
                             self.hsm_client.query_components(component=member, type='NodeBMC'))

        super().__init__(node_bmcs, timeout,
                         poll_interval=poll_interval, retries=retries)

    def condition_name(self):
        return f'slots {", ".join(self.members)} populated'

    def member_has_completed(self, member):
        resp = self.hsm_client.get('Inventory', 'RedfishEndpoints', member, raise_not_ok=False)
        # Missing endpoints may have not been discovered yet, in which case
        # querying their xnames will simply return a 404.
        if not resp.ok:
            if resp.status_code != 404:
                raise WaitingFailure(f'Could not query Redfish endpoint for {member}: {resp.reason}')
            else:
                return False

        endpoint = resp.json()
        if not endpoint:
            raise WaitingFailure(f'No Redfish endpoint found for {member}')
        return endpoint['DiscoveryInfo']['LastDiscoveryStatus'] == 'DiscoverOK'


class SwapOutProcedure(BladeSwapProcedure):
    """The blade removal portion of the blade swap procedure."""
    action_verb = 'remove'

    @blade_swap_stage('Perform pre-swap checks', allow_in_dry_run=True)
    def pre_swap_checks(self):
        """Check if the given slot xnames are ready for blade swapping.

        Raises:
            BladeSwapError: If the blades in the given slots are not ready to be
                swapped.
        """
        xname = XName(self.xname)
        if xname.get_type() != 'SLOT':
            raise BladeSwapError(f'xname {xname} does not refer to a slot.')

        ready_nodes = set(
            compute_node['ID'] for compute_node in self.blade_nodes
            if compute_node['State'] == 'Ready'
        )
        if ready_nodes:
            raise BladeSwapError(
                f'{inf.plural("Node", count=len(ready_nodes))} '
                f'{inf.join(list(ready_nodes))} {inf.plural_verb("is", count=len(ready_nodes))} '
                f'in "Ready" state.'
            )

    @blade_swap_stage('Disable Redfish endpoints for NodeBMC')
    def disable_redfish_endpoints(self):
        """Disable redfish endpoints for NodeBMCs in slot.

        Raises:
            BladeSwapError: if there is a problem querying HSM or disabling
                Redfish endpoints.
        """
        for node_bmc in self.blade_node_bmcs:
            self.hsm_client.set_redfish_endpoint_enabled(node_bmc['ID'], enabled=False)

    @blade_swap_stage('Disable slot')
    def disable_slot(self):
        """Disable slot in HSM inventory.

        Raises:
            BladeSwapError: if there is a problem disabling the slot in HSM
        """
        self.hsm_client.set_component_enabled(self.xname, enabled=False)

    @blade_swap_stage('Power off slot')
    def power_off_slot(self):
        """Powers off a slot using PCS

        Raises:
            BladeSwapError: if there is a problem powering off the slot with PCS
        """
        if self.blade_class == BladeClass.AIR:
            # Power off nodes on the blade individually on River blades
            xnames_on = self.pcs_client.get_xnames_power_state(
                [node['ID'] for node in self.blade_nodes]
            ).get('on')
            if xnames_on:
                self.pcs_client.set_xnames_power_state(
                    xnames_on, 'off',
                    recursive=True,
                    force=True,
                )
                LOGGER.info('Powered off nodes %s', inf.join(xnames_on))
            else:
                LOGGER.info('All nodes on River blade %s are already powered off, continuing', self.xname)
        else:
            # Power off the whole slot on Mountain
            self.pcs_client.set_xnames_power_state(
                [self.xname], 'off',
                recursive=True,
                force=True,
            )
            LOGGER.info('Powered off chassis slot %s', self.xname)

    @blade_swap_stage('Collect ethernet interface information', allow_in_dry_run=True)
    def store_ip_mac_address_mapping(self):
        """Collect MAC and IP addresses of ethernet interfaces for the given xname

        The MAC/IP address mapping will be written in a JSON file with the
        following rough schema:

            [
                {
                    "ComponentID": component_xname,
                    "MACAddress": mac_address,
                    "IPAddress": ip_address,
                }
            ]

        Raises:
            BladeSwapError: if ethernet interface information cannot be queried
                from HSM, or the mapping file cannot be written to disk.
        """
        interface_addr_mappings = []

        try:
            for node in self.blade_nodes:
                ethernet_interfaces = self.hsm_client.get_ethernet_interfaces(node['ID'])

                ifaces_added_for_node = False
                for interface in ethernet_interfaces:
                    if 'IPAddresses' in interface and interface['IPAddresses']:
                        interface_addr_mapping = {
                            'Description': interface['Description'],
                            'ComponentID': interface['ComponentID'],
                            'MACAddress': interface['MACAddress'],
                            'IPAddress': interface['IPAddresses'][0]['IPAddress']
                        }

                        interface_addr_mappings.append(interface_addr_mapping)
                        ifaces_added_for_node = True

                if not ifaces_added_for_node:
                    LOGGER.warning('No ethernet interfaces detected for node %s.', node['ID'])

            if interface_addr_mappings:
                addr_file_prefix = f'ethernet-interface-mappings-{self.xname}'
                with get_available_file(addr_file_prefix, 'json') as addr_file:
                    json.dump(interface_addr_mappings, addr_file)
                LOGGER.info('Stored ethernet interface mappings in %s', addr_file.name)
            else:
                LOGGER.warning('No ethernet interfaces were detected on any nodes on blade %s.', self.xname)

        except KeyError as err:
            raise BladeSwapError(f'API response missing "{err}" key') from err
        except OSError as err:
            raise BladeSwapError(f'Error writing ethernet interface mapping: {err}') from err

    @blade_swap_stage('Suspend hms-discovery cron job')
    def suspend_hms_discovery_cron_job(self):
        """Suspends the hsm-discovery cron job

        Raises:
            BladeSwapError: if there is a problem suspending the cron job.
        """
        try:
            HMSDiscoveryCronJob().set_suspend_status(True)
            if not HMSDiscoverySuspendedWaiter(timeout=180).wait_for_completion():
                raise BladeSwapError('hms-discovery cron job was not suspended.')
        except HMSDiscoveryError as err:
            raise BladeSwapError(f'Could not suspend hms-discovery cron job: {err}') from err

    @blade_swap_stage('Prompt for clearing node controller settings')
    def prompt_clear_node_controller_settings(self):
        """Prompts the user to perform stateful resets on the NodeBMCs before continuing.

        Raises:
            BladeSwapError: if HSM cannot be queried to identify NodeBMCs
            SystemExit: if the user bails
        """
        # CRAYSAT-1373: Do this automatically with SCSD once CASMHMS-5447 is
        # completed.

        if self.blade_class == BladeClass.LIQUID:
            commands = []
            for node_bmc in self.blade_node_bmcs:
                commands.append(
                    'curl -k -u root:PASSWORD -X POST -H \\\n'
                    '    \'Content-Type: application/json\' -d \'{"ResetType":"StatefulReset"}\' \\\n'
                    f'    https://{node_bmc["ID"]}/redfish/v1/Managers/BMC/Actions/Manager.Reset\n'
                )
            prompt_continue(
                'blade removal procedure',
                description='Before continuing, the following commands should be run to perform '
                            'a stateful reset on the NodeBMCs on the blade if the blade is being '
                            'swapped into another system:\n' + '\n'.join(commands)
            )
        else:
            prompt_continue(
                'blade removal procedure',
                description='Before continuing, the following NodeBMCs should be '
                            'reset to factory settings if the blade is being swapped '
                            'into another system:\n' + '\n'.join(f'  - {node_bmc["ID"]}'
                                                                 for node_bmc in self.blade_node_bmcs)
            )

    @blade_swap_stage('Delete ethernet interfaces')
    def delete_ethernet_interfaces(self):
        """Delete the ethernet interfaces for the nodes on the blade.

        Raises:
            APIError: if there is an issue deleting the ethernet interfaces from HSM.
        """
        interface_ids_to_delete = set(
            iface['ID']
            for node in self.blade_nodes
            for iface in self.hsm_client.get_ethernet_interfaces(node['ID'])
        )

        # River blades should have the NodeBMC ethernet interfaces deleted as
        # well. Mountain blades should *only* have the node ethernet interfaces
        # deleted.

        if self.blade_class == BladeClass.AIR:
            interface_ids_to_delete |= set(
                iface['ID']
                for node in self.blade_node_bmcs
                for iface in self.hsm_client.get_ethernet_interfaces(node['ID'])
            )

        for ethernet_interface in interface_ids_to_delete:
            self.hsm_client.delete_ethernet_interface(ethernet_interface)
            LOGGER.info('Deleted ethernet interface %s', ethernet_interface)

    @blade_swap_stage('Delete Redfish endpoints')
    def delete_redfish_endpoints(self):
        """Delete the Redfish endpoints for each node on the blade.

        Raises:
            APIError: if there is an issue deleting the ethernet interfaces from HSM.
        """
        for node_bmc in self.blade_node_bmcs:
            self.hsm_client.delete_redfish_endpoint(node_bmc['ID'])
            LOGGER.info('Deleted Redfish endpoint for NodeBMC %s', node_bmc['ID'])

    def mountain_procedure(self):
        self.disable_redfish_endpoints()
        self.prompt_clear_node_controller_settings()
        self.power_off_slot()

    def river_procedure(self):
        self.power_off_slot()
        self.prompt_clear_node_controller_settings()
        self.disable_redfish_endpoints()

    def procedure(self):
        self.pre_swap_checks()
        self.store_ip_mac_address_mapping()

        self.suspend_hms_discovery_cron_job()

        if self.blade_class == BladeClass.LIQUID:
            self.mountain_procedure()
        else:
            self.river_procedure()

        self.disable_slot()
        self.delete_ethernet_interfaces()
        self.delete_redfish_endpoints()


class SwapInProcedure(BladeSwapProcedure):
    action_verb = 'add'

    def __init__(self, args):
        super().__init__(args)
        self.src_mapping = args.src_mapping
        self.dst_mapping = args.dst_mapping
        self.k8s_api = load_kube_api()

    def wait_for_endpoints(self, xnames):
        """Helper function to wait for Redfish endpoints to be discovered

        Args:
            xnames (Iterable[str]): xnames of Redfish endpoints that should be
                awaited

        Raises:
            BladeSwapError: if there is a problem waiting for the components
                to be discovered
        """
        waiter = RedfishEndpointDiscoveryWaiter(xnames, self.hsm_client, timeout=600)
        waiter.wait_for_completion()
        if waiter.failed:
            raise BladeSwapError(f'BMCs were not discovered: {", ".join(waiter.failed)}')

    @blade_swap_stage('Wait for ChassisBMC Redfish endpoint discovery')
    def wait_for_chassisbmc_endpoints(self):
        """Wait for the ChassisBMCs in the slot's chassis to be discovered

        Raises:
            BladeSwapError: if there is a problem waiting for the ChassisBMCs
                to be discovered
        """
        chassis_xname = str(XName(self.xname).get_chassis())
        chassis_bmc_xnames = [
            component['ID'] for component in
            self.hsm_client.query_components(component=chassis_xname, type='ChassisBMC')
        ]
        self.wait_for_endpoints(chassis_bmc_xnames)

    @blade_swap_stage('Wait for NodeBMC Redfish endpoint discovery')
    def wait_for_nodebmc_endpoints(self):
        """Wait for the NodeBMCs in the slot to be discovered

        Raises:
            BladeSwapError: if there is a problem waiting for the NodeBMCs
        """
        node_bmc_xnames = [component['ID'] for component in self.blade_node_bmcs]
        self.wait_for_endpoints(node_bmc_xnames)

    @blade_swap_stage('Enable slot')
    def enable_slot(self):
        """Enable slot in HSM inventory.

        Raises:
            BladeSwapError: if the slot cannot be enabled
        """
        self.hsm_client.set_component_enabled(self.xname, enabled=True)

    @blade_swap_stage('Power on slot')
    def power_on_slot(self):
        """Power on the slot using PCS.

        Raises:
            BladeSwapError: if the slot cannot be powered on
        """
        params = {'recursive': True}
        if self.blade_class == BladeClass.AIR:
            params['force'] = True
        self.pcs_client.set_xnames_power_state([self.xname], 'on', **params)

    @blade_swap_stage('Enable nodes')
    def enable_nodes(self):
        """Enable the nodes in the blade in HSM

        Raises:
            BladeSwapError: if the nodes cannot be queried or enabled
        """
        node_xnames = [
            component['ID'] for component in
            self.blade_nodes
        ]
        self.hsm_client.bulk_enable_components(node_xnames)

    @blade_swap_stage('Discover slot')
    def begin_slot_discovery(self):
        """Kick off discovery of the slot.

        Raises:
            BladeSwapError: if HSM discovery cannot be started
        """
        chassis_xname = str(XName(self.xname).get_chassis())
        try:
            chassis_bmc = self.hsm_client.query_components(chassis_xname, type='ChassisBMC')[0]
        except (APIError, IndexError):
            if self.blade_class == BladeClass.LIQUID:
                LOGGER.warning('Could not locate ChassisBMC for chassis %s; waiting '
                               'for hms-discovery to discover slot',
                               chassis_xname)
            return

        self.hsm_client.begin_discovery([chassis_bmc['ID']], force=True)

    @blade_swap_stage('Resume hms-discovery cron job')
    def resume_hms_discovery_cron_job(self):
        """Resume the hms-discovery cron job.

        Raises:
            BladeSwapError: if there is a problem re-enabling the hms-discovery
                cron job
        """
        try:
            HMSDiscoveryCronJob().set_suspend_status(False)
            if not HMSDiscoveryScheduledWaiter().wait_for_completion():
                raise BladeSwapError('Timed out waiting for hms-discovery cron job to resume')
        except HMSDiscoveryError as err:
            raise BladeSwapError(f'Could not resume hms-discovery cron job: {err}') from err

    @property
    def kea_pod_name(self):
        """str: the name of the kea pod

        Raises:
            BladeSwapError: if the name of the pod cannot be identified
        """
        try:
            for pod in self.k8s_api.list_namespaced_pod('services').items:
                if pod.metadata.name.startswith('cray-dhcp-kea'):
                    return pod.metadata.name
            raise BladeSwapError('cray-dhcp-kea pod not found in "services" namespace')
        except ApiException as err:
            raise BladeSwapError(f'Could not get name of kea pod from kubernetes: {err}') from err

    @staticmethod
    def merge_mappings(src_mappings, dst_mappings):
        """Merge the source blade and destination blade's interface mappings

        It is assumed that the mappings from the source and destination blades
        are the same length (i.e. both blades have the same number of nodes)
        and that they contain nodes in the same relative positions on the
        blades.

        Args:
            src_mappings ([dict]): the interface mappings from the source blade
                using the same schema as was stored from
                store_ip_mac_address_mapping()
            dst_mappings ([dict]): the interface mappings from the destination blade
                using the same schema as was stored from
                store_ip_mac_address_mapping()

        Returns:
            [dict]: the merged mappings, containing MAC addresses from the
                source blade and IP addresses and xnames from the destination
                blade, merged on xnames with the same relative position in their
                respective blades
        """
        if len(src_mappings) != len(dst_mappings):
            raise BladeSwapError(f'The number of nodes on the source and destination '
                                 f'blades does not match: source blade contains {len(src_mappings)} nodes, '
                                 f'destination blade contains {len(dst_mappings)} nodes.')

        merged_mappings = []
        for src_mapping in src_mappings:
            src_xname = XName(src_mapping['ComponentID'])
            for dst_mapping in dst_mappings:
                dst_xname = XName(dst_mapping['ComponentID'])
                if src_xname.relative_node_positions_match(dst_xname):
                    merged_mappings.append({
                        'Description': dst_mapping['Description'],
                        'ComponentID': dst_mapping['ComponentID'],
                        'IPAddresses': [
                            {'IPAddress': dst_mapping['IPAddress']},
                        ],
                        'MACAddress':  src_mapping['MACAddress'],
                    })
                    break
            else:
                raise BladeSwapError(
                    f'No matching node found in destination blade for source node {src_xname}'
                )
        return merged_mappings

    @blade_swap_stage('Map IP and MAC addresses')
    def map_ip_mac_addresses(self):
        """Map the IP/MAC addresses from the source blade on the destination system.

        Raises:
            BladeSwapError: if there is a problem opening the mapping files, deleting the kea pod,
                or re-mapping the interfaces in HSM
        """
        try:
            with open(self.src_mapping) as src_mapping_file:
                src_mapping = json.load(src_mapping_file)

                with open(self.dst_mapping) as dst_mapping_file:
                    dst_mapping = json.load(dst_mapping_file)

                mapping = self.merge_mappings(src_mapping, dst_mapping)

            for ethernet_interface in self.hsm_client.get_ethernet_interfaces(xname=self.xname):
                if XName(ethernet_interface['ComponentID']).get_type().lower() == 'node':
                    self.hsm_client.delete_ethernet_interface(ethernet_interface['ID'])

            for ethernet_interface in mapping:
                self.hsm_client.create_ethernet_interface(ethernet_interface)

            self.k8s_api.delete_namespaced_pod(self.kea_pod_name, 'services')
        except ApiException as err:
            raise BladeSwapError(f'Could not delete cray-dhcp-kea pod: {err}') from err
        except OSError as err:
            raise BladeSwapError(f'Could not open mapping file: {err}') from err

    @blade_swap_stage('Perform pre-swap checks', allow_in_dry_run=True)
    def pre_swap_checks(self):
        """Perform pre-swap checks before swapping in a blade.

        This just asserts that source and destination mappings must be supplied together.

        Raises:
            BladeSwapError: if exactly one of --dst-mapping and
                --src-mapping is supplied
        """
        if bool(self.src_mapping) != bool(self.dst_mapping):
            raise BladeSwapError('If either --dst-mapping or --src-mapping is supplied, '
                                 'both must be supplied.')

    def procedure(self):
        self.pre_swap_checks()

        if self.src_mapping and self.dst_mapping:
            self.map_ip_mac_addresses()

        if self.blade_class == BladeClass.LIQUID:
            self.enable_slot()
            self.power_on_slot()

        self.resume_hms_discovery_cron_job()
        self.begin_slot_discovery()

        if self.blade_class == BladeClass.LIQUID:
            self.wait_for_chassisbmc_endpoints()

        self.wait_for_nodebmc_endpoints()
        self.enable_nodes()


def swap_blade(args):
    """Entrypoint for the `sat swap blade` subcommand.

    Args:
        args (argparse.Namespace): parsed command line arguments
    """
    blade_swap_stage.dry_run = args.dry_run

    if args.action == 'disable' or args.action is None:
        procedure_cls = SwapOutProcedure
    elif args.action == 'enable':
        procedure_cls = SwapInProcedure
    else:
        # Should never happen, but be defensive if for some reason we get a weird action
        raise ValueError(f'action {args.action} is not valid; '
                         'only "disable" and "enable" are valid options')

    procedure_cls(args).run()
