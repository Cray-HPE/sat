"""
Class to represent a RouterModule object obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from sat.hwinv.component import BaseComponent
from sat.hwinv.constants import ROUTER_MODULE_TYPE


class RouterModule(BaseComponent):
    """A router module in the EX-1 system."""

    hsm_type = ROUTER_MODULE_TYPE
    arg_name = 'router_module'
    pretty_name = 'router module'

    # Any fields needed specifically on a RouterModule can be added here.
    fields = BaseComponent.fields + []

    def __init__(self, raw_data):
        """Creates a router module with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the router module.
        """
        super().__init__(raw_data)

        # TODO: Add anything that is needed for RouterModule-type objects
