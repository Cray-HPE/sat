#
# MIT License
#
# (C) Copyright 2019-2020, 2024 Hewlett Packard Enterprise Development LP
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
Class to define the entire system hardware inventory.
"""
from collections import defaultdict
import logging

from sat.system.component import NodeComponent
from sat.system.constants import EMPTY_STATUS, STATUS_KEY, TYPE_KEY
from sat.system.chassis import Chassis
from sat.system.cmm_rectifier import CMMRectifier
from sat.system.compute_module import ComputeModule
from sat.system.drive import Drive
from sat.system.hsn_board import HSNBoard
from sat.system.memory_module import MemoryModule
from sat.system.node import Node
from sat.system.node_enclosure import NodeEnclosure
from sat.system.node_enclosure_power_supply import NodeEnclosurePowerSupply
from sat.system.processor import Processor
from sat.system.node_accel import NodeAccel
from sat.system.node_accel_riser import NodeAccelRiser
from sat.system.node_hsn_nic import NodeHsnNic
from sat.system.router_module import RouterModule
from sat.system.node_bmc import NodeBMC
from sat.system.router_bmc import RouterBMC
from sat.system.mgmt_switch import MgmtSwitch
from sat.system.cabinet_pdu import CabinetPDU
from sat.system.cabinet_pdu_power_connector import CabinetPDUPowerConnector
from sat.xname import XName

LOGGER = logging.getLogger(__name__)


class System:
    """The full hardware inventory as returned by the HSM API."""

    def __init__(self, complete_raw_data):
        """Creates a new object representing the full system's hardware inventory.

        Args:
            complete_raw_data (list): The list of dictionaries returned as JSON
                by the HSM API.
        """
        self.complete_raw_data = complete_raw_data
        self.raw_data_by_type = defaultdict(list)

        self.components_by_type = {
            Chassis: {},
            CMMRectifier: {},
            ComputeModule: {},
            Drive: {},
            HSNBoard: {},
            MemoryModule: {},
            Node: {},
            NodeEnclosure: {},
            NodeEnclosurePowerSupply: {},
            Processor: {},
            NodeAccel: {},
            NodeAccelRiser: {},
            NodeHsnNic: {},
            RouterModule: {},
            NodeBMC: {},
            RouterBMC: {},
            MgmtSwitch: {},
            CabinetPDU: {},
            CabinetPDUPowerConnector: {}
        }

        for component in self.complete_raw_data:
            try:
                comp_type = component[TYPE_KEY]
                comp_status = component[STATUS_KEY]
            except KeyError as err:
                LOGGER.warning("Missing '%s' key in hardware inventory component. "
                               "The following keys are present: %s", err,
                               ', '.join(component.keys()))
                continue

            if comp_status == EMPTY_STATUS:
                LOGGER.debug("Skipping empty object of type '%s'.", comp_type)
                continue

            self.raw_data_by_type[comp_type].append(component)

        LOGGER.debug("Found components of the following types: %s",
                     ','.join(self.raw_data_by_type.keys()))

    def parse_all(self):
        """Parse and interrelate objects from raw data."""
        self.parse_raw_data()
        self.relate_node_children()
        self.relate_node_parents()

    def parse_raw_data(self):
        """Creates and stores objects from raw data."""
        for object_type, storage_dict in self.components_by_type.items():
            try:
                raw_comp_data = self.raw_data_by_type[object_type.hsm_type]
            except KeyError:
                LOGGER.warning("No components of type '%s' found in HSM data.",
                               object_type.hsm_type)
                continue

            for raw_comp in raw_comp_data:
                comp = object_type(raw_comp)
                storage_dict[comp.xname] = comp

    def relate_node_children(self):
        """Creates links between nodes and their processors and memory modules."""
        node_children_dicts = [
            comp_dict for comp_type, comp_dict in self.components_by_type.items()
            if issubclass(comp_type, NodeComponent)
        ]
        nodes = self.components_by_type[Node]

        for children_by_xname in node_children_dicts:
            for child_xname, child_object in children_by_xname.items():
                node_xname = child_xname.get_parent_node()
                if node_xname is None:
                    LOGGER.warning("Unable to determine parent node xname of "
                                   "child xname '%s'.", child_xname)
                    continue
                try:
                    node_object = nodes[node_xname]
                except KeyError:
                    LOGGER.warning("Unable to find parent node xname '%s' of child "
                                   "xname '%s' in hardware inventory.",
                                   node_xname, child_xname)
                    continue

                node_object.add_child_object(child_object)
                child_object.node = node_object

    def relate_node_parents(self):
        """Creates links between nodes and their parent chassis."""
        for node_xname, node_object in self.components_by_type[Node].items():
            chassis_xname = XName.get_xname_from_tokens(node_xname.tokens[:4])
            try:
                chassis_object = self.components_by_type[Chassis][chassis_xname]
            except KeyError:
                LOGGER.debug("No chassis object found for node '%s'.", node_xname)
                continue

            LOGGER.debug("Found chassis object '%s' for node '%s'", chassis_object, node_object)
            node_object.chassis = chassis_object
            chassis_object.add_child_object(node_object)
