"""
Constant values for system representation

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

# The key that stores the object type in HSM output
TYPE_KEY = 'Type'
# The key that stores the object status in HSM output
STATUS_KEY = 'Status'
# Status can be either 'Populated' or 'Empty'. Most objects do not even show up
# in HSM if they aren't there. The exceptions are RouterModule and ComputeModule.
POPULATED_STATUS = 'Populated'
EMPTY_STATUS = 'Empty'

# The various known values for TYPE_KEY in HSM output
CHASSIS_TYPE = 'Chassis'
COMPUTE_MODULE_TYPE = 'ComputeModule'
DRIVE_TYPE = 'Drive'
HSN_BOARD_TYPE = 'HSNBoard'
MEMORY_TYPE = 'Memory'
NODE_ENCLOSURE_TYPE = 'NodeEnclosure'
NODE_TYPE = 'Node'
PROCESSOR_TYPE = 'Processor'
ROUTER_MODULE_TYPE = 'RouterModule'

# The types of cabinets are C-Series and S-Series.
# C-Series is densely liquid cooled.
CAB_TYPE_C = 'C-Series'
CAB_TYPE_S = 'S-Series'
