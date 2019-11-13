"""
Class to represent a Chassis object obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from sat.hwinv.component import BaseComponent
from sat.hwinv.constants import CHASSIS_TYPE
from sat.hwinv.node import Node


class Chassis(BaseComponent):
    """A chassis in the system."""

    hsm_type = CHASSIS_TYPE
    arg_name = 'chassis'
    pretty_name = 'chassis'

    # Any fields needed specifically on a Chassis can be added here.
    fields = BaseComponent.fields + []

    def __init__(self, raw_data):
        """Creates a chassis with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the chassis.
        """
        super().__init__(raw_data)

        # Links to objects that are children of this component in the hierarchy
        self.compute_modules = {}
        self.node_enclosures = {}
        self.nodes = {}

        self.children_by_type = {
            Node: self.nodes
        }
