"""
Constant values for system representation

Copyright 2019-2020 Cray Inc. All Rights Reserved.
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

# The value to use when a requested key is missing
MISSING_VALUE = 'MISSING'
# The value to use in place of the empty string.
EMPTY_VALUE = 'EMPTY'
