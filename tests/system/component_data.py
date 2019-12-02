"""
Functions to generate fake component data that can be passed in to each component.

Copyright 2019 Cray Inc. All Rights Reserved.
"""

# Some sample xnames for different types of components stored in HSM
CHASSIS_XNAME = 'x1000c0'
ROUTER_MODULE_XNAME = 'x1000c0r0'
HSN_BOARD_XNAME = 'x1000c0r0e0'
COMPUTE_MODULE_XNAME = 'x1000c0s0'
NODE_ENCLOSURE_XNAME = 'x1000c0s0e0'
NODE_XNAME = 'x1000c0s0b0n0'
PROCESSOR_XNAME = 'x1000c0s0b0n0p0'
MEMORY_MODULE_XNAME = 'x1000c0s0b0n0d0'

# Default values for component raw data.
DEFAULT_HSM_TYPE = 'Sample'
DEFAULT_XNAME = NODE_XNAME
DEFAULT_SERIAL_NUMBER = 'BQWT83500291'
DEFAULT_PART_NUMBER = '102095800'
DEFAULT_SKU = '123456789'
DEFAULT_MODEL = 'S2600WFT'
DEFAULT_MANUFACTURER = 'Cray, Inc.'


def get_component_raw_data(hsm_type=DEFAULT_HSM_TYPE,
                           xname=DEFAULT_XNAME,
                           serial_number=DEFAULT_SERIAL_NUMBER,
                           part_number=DEFAULT_PART_NUMBER,
                           sku=DEFAULT_SKU,
                           model=DEFAULT_MODEL,
                           manufacturer=DEFAULT_MANUFACTURER):
    return {
        'Ordinal': 0,
        'Status': 'Populated',
        '{}LocationInfo'.format(hsm_type): {
            'Description': '{} Component'.format(hsm_type),
            'HostName': '{}-component'.format(hsm_type.lower()),
            'Id': serial_number,
            'Name': '{} Component'.format(hsm_type)
        },
        'HWInventoryByLocationType': 'HWInvByLoc{}'.format(hsm_type),
        'PopulatedFRU': {
            'Subtype': '',
            'FRUID': '{}.{}'.format(hsm_type, serial_number),
            'Type': hsm_type,
            'HWInventoryByFRUType': 'HWInvByFRU{}'.format(hsm_type),
            '{}FRUInfo'.format(hsm_type): {
                'SKU': sku,
                'AssetTag': '',
                'SerialNumber': serial_number,
                'Model': model,
                'PartNumber': part_number,
                'Manufacturer': manufacturer
            }
        },
        'Type': hsm_type,
        'ID': xname
    }
