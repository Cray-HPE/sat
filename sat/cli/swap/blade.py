"""
Procedure for swapping a blade.

(C) Copyright 2022 Hewlett Packard Enterprise Development LP.

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
import abc
from functools import wraps
import json
import logging
import warnings

from kubernetes.client.exceptions import ApiException
from kubernetes.client import CoreV1Api
from kubernetes.config import (
    ConfigException,
    load_kube_config
)
import inflect
from yaml import YAMLLoadWarning

from sat.cached_property import cached_property
from sat.apiclient.capmc import CAPMCClient
from sat.apiclient.gateway import APIError
from sat.apiclient.hsm import HSMClient
from sat.hms_discovery import (
    HMSDiscoveryCronJob,
    HMSDiscoveryError,
    HMSDiscoveryScheduledWaiter,
)
from sat.session import SATSession
from sat.util import prompt_continue
from sat.waiting import GroupWaiter, WaitingFailure
from sat.xname import XName


LOGGER = logging.getLogger(__name__)
inf = inflect.engine()


class BladeSwapError(Exception):
    """Represents an exception which occurs during blade swapping."""


def blade_swap_stage(stage_title):
    """A decorator which logs when entering and exiting a function.

    Decorated functions will log the name of the stage before execution, catch
    APIErrors and re-raise them as BladeSwapErrors, and pass through all other
    exceptions.

    Args:
        stage_title (str): a sentence describing what the stage doesself.
            The title should always begin with a verb in the imperative mood,
            followed by the subject as the dependent clause. For example,
            "Disable the Redfish endpoints for the slot."
    """
    verb, object = stage_title.split(' ', maxsplit=1)

    def _decorator(fn):
        @wraps(fn)
        def inner(*args, **kwargs):
            LOGGER.info('%s %s', inf.present_participle(verb), object)
            try:
                fn(*args, **kwargs)
            except APIError as api_err:
                raise BladeSwapError(f'Error accessing API: {api_err}') from api_err
            except Exception:
                raise

        return inner
    return _decorator


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
        self.capmc_client = CAPMCClient(session)

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
        try:
            endpoint = self.hsm_client.get_redfish_endpoint_inventory(member)
            if not endpoint:
                raise WaitingFailure(f'No Redfish endpoint found for {member}')
            return endpoint['DiscoveryInfo']['LastDiscoveryStatus'] == 'DiscoverOK'
        except APIError as err:
            raise WaitingFailure(f'Could not query Redfish endpoint for {member}: {err}')


class SwapOutProcedure(BladeSwapProcedure):
    """The blade removal portion of the blade swap procedure."""
    action_verb = 'remove'

    @blade_swap_stage('Perform pre-swap checks')
    def pre_swap_checks(self):
        """Check if the given slot xnames are ready for blade swapping.

        Raises:
            BladeSwapError: If the blades in the given slots are not ready to be
                swapped.
        """
        xname = XName(self.xname)
        if xname.get_type() != 'SLOT':
            raise BladeSwapError(f'xname {xname} does not refer to a slot.')

        blade_compute_nodes = self.hsm_client.get_node_components(ancestor=self.xname)

        nodes_not_off = set(
            compute_node['ID'] for compute_node in blade_compute_nodes
            if compute_node['State'] != 'Off'
        )
        if nodes_not_off:
            raise BladeSwapError(
                f'Compute {inf.plural("node", count=len(nodes_not_off))} '
                f'{inf.join(list(nodes_not_off))} {inf.plural_verb("is", count=len(nodes_not_off))}'
                f' not off.'
            )

    @blade_swap_stage('Disable Redfish endpoint for NodeBMC')
    def disable_redfish_endpoint(self):
        """Disable redfish endpoints for NodeBMCs in slot.

        Raises:
            BladeSwapError: if there is a problem querying HSM or disabling
                Redfish endpoints.
        """
        node_bmcs = self.hsm_client.query_components(component=self.xname, type='NodeBMC')
        for node_bmc in node_bmcs:
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
        """Powers off a slot using CAPMC

        Raises:
            BladeSwapError: if there is a problem powering off the slot with CAPMC
        """
        self.capmc_client.set_xnames_power_state([self.xname], 'off', recursive=True)

    @blade_swap_stage('Collect ethernet interface information')
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
            ethernet_interfaces = self.hsm_client.get_ethernet_interfaces(self.xname)

            for interface in ethernet_interfaces:
                interface_addr_mapping = {
                    'Description': interface['Description'],
                    'ComponentID': interface['ComponentID'],
                    'MACAddress': interface['MACAddress'],
                    'IPAddress': interface['IPAddresses'][0]['IPAddress'] if interface['IPAddresses'] else []
                }

                interface_addr_mappings.append(interface_addr_mapping)

            if not ethernet_interfaces:
                LOGGER.warning('No ethernet interfaces detected for blade %s. '
                               'Ethernet interface MAC/IP address mappings will not be saved.',
                               self.xname)
                return

            addr_file_name = f'ethernet-interface-mappings-{self.xname}.json'
            with open(addr_file_name, 'w') as addr_file:
                json.dump(interface_addr_mappings, addr_file)
            LOGGER.info('Stored ethernet interface mappings in %s', addr_file_name)

        except KeyError as err:
            raise BladeSwapError(f'API repsonse missing "{err}" key') from err
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
        node_bmcs = self.hsm_client.query_components(self.xname, type='NodeBMC')
        commands = []
        for node_bmc in node_bmcs:
            commands.append(
                'curl -k -u root:PASSWORD -X POST -H \\\n'
                '    \'Content-Type: application/json\' -d \'{"ResetType":"StatefulReset"}\' \\\n'
                f'    https://{node_bmc["ID"]}/redfish/v1/Managers/BMC/Actions/Manager.Reset\n'
            )

        prompt_continue(
            'blade removal procedure',
            description='Before continuing, the following commands should be run to perform '
                        'a stateful reset on the NodeBMCs on the blade if the blade is being '
                        'swapped into another system: \n' + '\n'.join(commands)
        )

    @blade_swap_stage('Delete ethernet interfaces')
    def delete_ethernet_interfaces(self):
        """Delete the ethernet interfaces for the nodes on the blade.

        Raises:
            APIError: if there is an issue deleting the ethernet interfaces from HSM.
        """
        for blade_node in self.hsm_client.get_node_components(ancestor=self.xname):
            for ethernet_interface in self.hsm_client.get_ethernet_interfaces(blade_node['ID']):
                self.hsm_client.delete_ethernet_interface(ethernet_interface['ID'])

    @blade_swap_stage('Delete Redfish endpoints')
    def delete_redfish_endpoints(self):
        """Delete the Redfish endpoints for each node on the blade.

        Raises:
            APIError: if there is an issue deleting the ethernet interfaces from HSM.
        """
        for node_bmc in self.hsm_client.query_components(component=self.xname, type='NodeBMC'):
            self.hsm_client.delete_redfish_endpoint(node_bmc['ID'])

    def procedure(self):
        self.pre_swap_checks()
        self.store_ip_mac_address_mapping()

        self.disable_redfish_endpoint()
        self.prompt_clear_node_controller_settings()
        self.disable_slot()
        self.suspend_hms_discovery_cron_job()
        self.power_off_slot()

        self.delete_ethernet_interfaces()
        self.delete_redfish_endpoints()


class SwapInProcedure(BladeSwapProcedure):
    action_verb = 'add'

    def __init__(self, args):
        super().__init__(args)
        self.src_mapping = args.src_mapping
        self.dst_mapping = args.dst_mapping

    @cached_property
    def k8s_api(self):
        """Get a Kubernetes CoreV1Api object.

        This helper function loads the kube config and then instantiates
        an API object.

        Returns:
            CoreV1Api: the API object from the kubernetes library.

        Raises:
            kubernetes.config.config_exception.ConfigException: if failed to load
                kubernetes configuration.
        """
        try:
            with warnings.catch_warnings():
                warnings.filterwarnings('ignore', category=YAMLLoadWarning)
                load_kube_config()
        # Earlier versions: FileNotFoundError; later versions: ConfigException
        except (FileNotFoundError, ConfigException) as err:
            raise ConfigException(
                'Failed to load kubernetes config to get pod status: '
                '{}'.format(err)
            )

        return CoreV1Api()

    def wait_for_endpoints(self, xnames):
        """Helper function to wait for Redfish endpoints to be discovered

        Args:
            xnames (Iterable[str]): xnames of Redfish endpoints that should be
                awaited

        Raises:
            BladeSwapError: if there is a problem waiting for the components
                to be discovered
        """
        waiter = RedfishEndpointDiscoveryWaiter(xnames, self.hsm_client, timeout=300)
        waiter.wait_for_completion()
        if waiter.failed:
            raise BladeSwapError(f'Chassis BMCs were not discovered: {", ".join(waiter.failed)}')

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
        node_bmc_xnames = [
            component['ID'] for component in
            self.hsm_client.query_components(component=self.xname, type='NodeBMC')
        ]
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
        """Power on the slot using CAPMC.

        Raises:
            BladeSwapError: if the slot cannot be powered on
        """
        self.capmc_client.set_xnames_power_state([self.xname], 'on', recursive=True)

    @blade_swap_stage('Enable nodes')
    def enable_nodes(self):
        """Enable the nodes in the blade in HSM

        Raises:
            BladeSwapError: if the nodes cannot be queried or enabled
        """
        node_xnames = [
            component['ID'] for component in
            self.hsm_client.get_node_components(self.xname)
        ]
        self.hsm_client.bulk_enable_components(node_xnames)

    @blade_swap_stage('Discover slot')
    def begin_slot_discovery(self):
        """Kick off discovery of the slot.

        Raises:
            BladeSwapError: if HSM discovery cannot be started
        """
        self.hsm_client.begin_discovery(self.xname)

    @blade_swap_stage('Resume hms-discovery cron job')
    def resume_hms_discovery_cron_job(self):
        """Resume the hms-discovery cron job.

        Raises:
            BladeSwapError: if there is a problem re-enabling the hms-discovery
                cron job
        """
        try:
            HMSDiscoveryCronJob().set_suspend_status(False)
            HMSDiscoveryScheduledWaiter().wait_for_completion()
        except HMSDiscoveryError as err:
            raise BladeSwapError(f'Could not suspend hms-discovery cron job: {err}') from err

    @property
    def kea_pod_name(self):
        """str: the name of the kea pod

        Raises:
            BladeSwapError: if the name of the pod cannot be identified
        """
        try:
            for pod in self.k8s_api.list_namespaced_pod('services'):
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
                        'ComponentID': dst_mapping['ComponentID'],
                        'IPAddress':   dst_mapping['IPAddress'],
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
            self.k8s_api.delete_namespaced_pod(self.kea_pod_name, 'services')

            with open(self.src_mapping) as src_mapping_file:
                src_mapping = json.load(src_mapping_file)

                with open(self.dst_mapping) as dst_mapping_file:
                    dst_mapping = json.load(dst_mapping_file)

                mapping = self.merge_mappings(src_mapping, dst_mapping)

            for ethernet_interface in self.hsm_client.get_ethernet_interfaces(xname=self.xname):
                if (ethernet_interface['Description'] == 'Node Management Network'
                        and XName(ethernet_interface['ComponentID']).get_type() == 'NODE'):
                    self.hsm_client.delete_ethernet_interface(ethernet_interface['ID'])

            for ethernet_interface in mapping:
                self.hsm_client.create_ethernet_interface(ethernet_interface)

        except ApiException as err:
            raise BladeSwapError(f'Could not delete cray-dhcp-kea pod: {err}') from err
        except OSError as err:
            raise BladeSwapError(f'Could not open mapping file: {err}') from err

    @blade_swap_stage('Perform pre-swap checks')
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

        self.begin_slot_discovery()

        self.wait_for_chassisbmc_endpoints()

        self.enable_slot()
        self.power_on_slot()
        self.resume_hms_discovery_cron_job()
        self.wait_for_nodebmc_endpoints()
        self.enable_nodes()


def swap_blade(args):
    """Entrypoint for the `sat swap blade` subcommand.

    Args:
        args (argparse.Namespace): parsed command line arguments
    """
    if args.action == 'disable':
        procedure_cls = SwapOutProcedure
    elif args.action == 'enable':
        procedure_cls = SwapInProcedure

    procedure_cls(args).run()
