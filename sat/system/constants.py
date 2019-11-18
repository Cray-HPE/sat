"""
Constant values to be used in hwinv.

Copyright 2019 Cray Inc. All Rights Reserved.
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
NODE_ENCLOSURE_TYPE = 'NodeEnclosure'
NODE_TYPE = 'Node'
MEMORY_TYPE = 'Memory'
PROCESSOR_TYPE = 'Processor'
HSN_BOARD_TYPE = 'HSNBoard'
ROUTER_MODULE_TYPE = 'RouterModule'

# The types of cabinets
EX_1_C = "EX-1 C"
EX_1_S = "EX-1 S"

# The value to use when a requested key is missing
MISSING_VALUE = "MISSING"
# The value to use in place of the empty string.
EMPTY_VALUE = "EMPTY"
