"""
Class to represent a NodeAccelRiser object obtained from Hardware State Manager (HSM).

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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
from sat.cached_property import cached_property
from sat.system.component import NodeComponent
from sat.system.constants import NODE_ACCEL_RISER_TYPE
from sat.system.field import ComponentField


class NodeAccelRiser(NodeComponent):
    """A node accelerator riser in the system."""

    hsm_type = NODE_ACCEL_RISER_TYPE
    arg_name = 'node_accel_riser'
    pretty_name = 'node accelerator riser'

    # Any fields needed specifically on a nodeAccelRiser can be added here.
    fields = NodeComponent.fields + [
        ComponentField(pretty_name='Board Serial Number', property_name='pcb_serial_number'),
        ComponentField('Producer'),
        ComponentField('Engineering Change Level')
    ]

    @cached_property
    def pcb_serial_number(self):
        """str: the PCB serial number of the riser card."""
        return self.fru_info['Oem']['PCBSerialNumber']

    @cached_property
    def producer(self):
        """str: the producer of the riser card."""
        return self.fru_info['Producer']

    @cached_property
    def engineering_change_level(self):
        """str: the engineering change level of the riser card."""
        return self.fru_info['EngineeringChangeLevel']
