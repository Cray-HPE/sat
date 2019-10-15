"""
Class to represent a NodeEnclosure object obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from sat.hwinv.component import BaseComponent
from sat.hwinv.constants import NODE_ENCLOSURE_TYPE


class NodeEnclosure(BaseComponent):
    """A node enclosure in the EX-1 system."""

    hsm_type = NODE_ENCLOSURE_TYPE
    arg_name = 'node_enclosure'
    pretty_name = 'node enclosure'

    # Any fields needed specifically on a NodeEnclosure can be added here.
    fields = BaseComponent.fields + []

    def __init__(self, raw_data):
        """Creates a node enclosure with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the node enclosure.
        """
        super().__init__(raw_data)

        # TODO: Add anything that is needed for NodeEnclosure-type objects
