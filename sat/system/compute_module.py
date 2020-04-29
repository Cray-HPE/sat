"""
Class to represent a ComputeModule object obtained from Hardware State Manager (HSM).

ComputeModules will have xnames of the form 'xXcCsS'. They represent compute
blades in a liquid-cooled cabinet. They do not exist for nodes in air-cooled
cabinets.

(C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP.

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
from sat.system.component import BaseComponent
from sat.system.constants import COMPUTE_MODULE_TYPE


class ComputeModule(BaseComponent):
    """Represents a compute module in a liquid-cooled system."""

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
