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
Functions to generate fake component data that can be passed in to each component.
"""

# Some sample xnames for different types of components stored in HSM
CHASSIS_XNAME = 'x1000c0'
ROUTER_MODULE_XNAME = 'x1000c0r0'
HSN_BOARD_XNAME = 'x1000c0r0e0'
COMPUTE_MODULE_XNAME = 'x1000c0s0'
NODE_ENCLOSURE_XNAME = 'x1000c0s0e0'
NODE_ENCLOSURE_POWER_SUPPLY_XNAME = 'x1000c0s0e0t0'
NODE_XNAME = 'x1000c0s0b0n0'
PROCESSOR_XNAME = 'x1000c0s0b0n0p0'
NODE_ACCEL_XNAME = 'x1000c0s0b0n0a0'
NODE_ACCEL_RISER_XNAME = 'x1000c0s0b0n0r0'
NODE_HSN_NIC_XNAME = 'x1000c0s0b0n0h0'
MEMORY_MODULE_XNAME = 'x1000c0s0b0n0d0'
DRIVE_XNAME = 'x1000c0s0b0n0g1k1'
CMM_RECTIFIER_XNAME = 'x1000c0t0'

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
