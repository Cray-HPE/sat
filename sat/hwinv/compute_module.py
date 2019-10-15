"""
Class to represent a ComputeModule object obtained from Hardware State Manager (HSM).

ComputeModules will have xnames of the form 'xXcCsS'. They represent compute
blades in a Mountain (EX-1 C) cabinet. They do not exist for nodes in a River
cabinet.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from sat.hwinv.component import BaseComponent
from sat.hwinv.constants import COMPUTE_MODULE_TYPE


class ComputeModule(BaseComponent):
    """A compute module in the EX-1 system."""

    hsm_type = COMPUTE_MODULE_TYPE
    arg_name = 'compute_module'
    pretty_name = 'compute module'

    # Any fields needed specifically on a ComputeModule can be added here.
    fields = BaseComponent.fields + []

    def __init__(self, raw_data):
        """Creates a compute module with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the compute module.
        """
        super().__init__(raw_data)

        # TODO: Add anything that is needed for ComputeModule-type objects
