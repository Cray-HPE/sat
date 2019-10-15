"""
Class to represent an HSNBoard object obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from sat.hwinv.component import BaseComponent
from sat.hwinv.constants import HSN_BOARD_TYPE


class HSNBoard(BaseComponent):
    """A High-speed Network (HSN) Board in the EX-1 system."""

    hsm_type = HSN_BOARD_TYPE
    arg_name = 'hsn_board'
    pretty_name = 'HSN board'

    # Any fields needed specifically on an HSNBoard can be added here.
    fields = BaseComponent.fields + []

    def __init__(self, raw_data):
        """Creates a HSN board with the raw JSON returned by the HSM API.

        Args:
            raw_data (dict): The dictionary returned as JSON by the HSM API
                that contains the raw data for the HSN board.
        """
        super().__init__(raw_data)

        # TODO: Add anything that is needed for HSNBoard-type objects
