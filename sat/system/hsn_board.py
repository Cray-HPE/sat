#
# MIT License
#
# (C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP
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
Class to represent an HSNBoard object obtained from Hardware State Manager (HSM).
"""
from sat.system.component import BaseComponent
from sat.system.constants import HSN_BOARD_TYPE


class HSNBoard(BaseComponent):
    """A High-speed Network (HSN) Board in a system."""

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
