#
# MIT License
#
# (C) Copyright 2021, 2024 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.slscheck module.
"""

import unittest
from argparse import Namespace
from unittest import mock

from sat.cli.slscheck.main import (
    create_crosscheck_results,
    create_hsm_hw_to_crosscheck,
    create_sls_hw_to_check,
    do_slscheck
)
from sat.xname import XName


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.types = ['CabinetPDUController', 'Node', 'ChassisBMC', 'NodeBMC', 'RouterBMC']
    namespace.checks = ['Class', 'Component', 'RFEndpoint', 'Role']
    namespace.include_consistent = False
    namespace.sort_by = 0
    namespace.reverse = False
    namespace.filter_strs = None
    namespace.format = None
    namespace.fields = None


class TestDoSlscheck(unittest.TestCase):
    """Unit test for slscheck"""

    def setUp(self):
        """Mock functions called."""
        self.sls_hw_dumpstate = {
            'x3000m0': {
                'Parent': 'x3000',
                'Xname': 'x3000m0',
                'Class': 'River',
                'TypeString': 'CabinetPDUController'
            },
            'x3000c0r22b0': {
                'Parent': 'x3000',
                'Xname': 'x3000c0r22b0',
                'Class': 'River',
                'TypeString': 'RouterBMC'
            },
            'x3000c0s11b0n0': {
                'Parent': 'x3000c0s11b0',
                'Xname': 'x3000c0s11b0n0',
                'Class': 'River',
                'TypeString': 'Node',
                'ExtraProperties': {
                    'Role': 'Management',
                    'SubRole': 'Storage'
                }
            },
            'x3000c0s17b1n0': {
                'Parent': 'x3000c0s17b1',
                'Xname': 'x3000c0s17b1n0',
                'Class': 'River',
                'TypeString': 'Node',
                'ExtraProperties': {
                    'Aliases': ['nid000001'],
                    'NID': 1,
                    'Role': 'Compute'
                }
            },
            'x3000c0s17b999': {
                'Parent': 'x3000',
                'Xname': 'x3000c0s17b999',
                'Class': 'River',
                'TypeString': 'ChassisBMC'
            },
            'x3000c0s1b0n0': {
                'Parent': 'x3000c0s1b0',
                'Xname': 'x3000c0s1b0n0',
                'Class': 'River',
                'TypeString': 'Node',
                'ExtraProperties': {
                    'Aliases': ['ncn-m001'],
                    'NID': 100001,
                    'Role': 'Management',
                    'SubRole': 'Master'
                }
            },
            'x3000c0s24b0n0': {
                'Parent': 'x3000c0s24b0',
                'Xname': 'x3000c0s24b0n0',
                'Class': 'River',
                'TypeString': 'Node',
                'ExtraProperties': {
                    'Aliases': ['ncn-w003'],
                    'NID': 100009,
                    'Role': 'Management',
                    'SubRole': 'Worker'
                }
            },
            'x3000c0s26b0n0': {
                'Parent': 'x3000c0s26b0',
                'Xname': 'x3000c0s26b0n0',
                'Class': 'River',
                'TypeString': 'Node',
                'ExtraProperties': {
                    'Aliases': ['uan01'],
                    'Role': 'Application',
                    'SubRole': 'UAN'
                }
            }
        }
        self.mock_sls_client = mock.patch('sat.cli.slscheck.main.SLSClient',
                                          autospec=True).start().return_value
        self.mock_sls_client.get_hardware.return_value = self.sls_hw_dumpstate

        self.all_hsm_components = [
            {'ID': 'x3000m0',
             'Type': 'CabinetPDUController'},
            {'ID': 'x3000c0r22b0',
             'Type': 'RouterBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s11b0n0',
             'Type': 'Node',
             'Role': 'Management',
             'SubRole': 'Worker',
             'Class': 'River'},
            {'ID': 'x3000c0s11b0',
             'Type': 'NodeBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s17b1n0',
             'Type': 'Node',
             'Role': 'Compute',
             'Class': 'River'},
            {'ID': 'x3000c0s17b1',
             'Type': 'NodeBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s1b0n0',
             'Type': 'Node',
             'Role': 'Management',
             'SubRole': 'Master',
             'Class': 'River'},
            {'ID': 'x3000c0s24b0n0',
             'Type': 'Node',
             'Role': 'Management',
             'SubRole': 'Worker',
             'Class': 'River'},
            {'ID': 'x3000c0s24b0',
             'Type': 'NodeBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s26b0n0',
             'Type': 'Node',
             'Role': 'Application',
             'SubRole': 'UAN',
             'Class': 'Mountain'},
            {'ID': 'x3000c0s26b0',
             'Type': 'NodeBMC',
             'Class': 'River'}
        ]

        self.all_hsm_redfish_endpoints = [
            {'ID': 'x3000c0r22b0',
             'Type': 'RouterBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s11b0',
             'Type': 'NodeBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s17b1',
             'Type': 'NodeBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s1b0',
             'Type': 'NodeBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s24b0',
             'Type': 'NodeBMC',
             'Class': 'River'},
            {'ID': 'x3000c0s26b0',
             'Type': 'NodeBMC',
             'Class': 'River'}
        ]
        self.mock_hsm_client = mock.patch('sat.cli.slscheck.main.HSMClient',
                                          autospec=True).start().return_value
        self.mock_hsm_client.get_all_components.return_value = self.all_hsm_components
        self.mock_hsm_client.get_bmcs_by_type.return_value = self.all_hsm_redfish_endpoints

        self.mock_sat_session = mock.patch('sat.cli.slscheck.main.SATSession').start()
        self.mock_print = mock.patch('builtins.print', autospec=True).start()

        self.fake_args = Namespace()
        set_options(self.fake_args)

    def tearDown(self):
        """Stop all patches."""
        mock.patch.stopall()

    def test_basic(self):
        """Test do_slscheck using default checks and types."""
        do_slscheck(self.fake_args)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_component(self):
        """Test do_slscheck using Compoment check and default types."""
        self.fake_args.checks = ['Component']
        do_slscheck(self.fake_args)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_redfish_endpoint(self):
        """Test do_slscheck using RFEndpoint check and default types."""
        self.fake_args.checks = ['RFEndpoint']
        do_slscheck(self.fake_args)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_class(self):
        """Test do_slscheck using Class check and default types."""
        self.fake_args.checks = ['Class']
        do_slscheck(self.fake_args)
        self.assertEqual(self.mock_print.call_count, 1)

    def test_role(self):
        """Test do_slscheck using Role check and default types."""
        self.fake_args.checks = ['Role']
        do_slscheck(self.fake_args)
        self.assertEqual(self.mock_print.call_count, 1)

    @staticmethod
    def build_expected_output_of_create_sls_hw_to_check(include_types=None):
        """Build expected output of create_sls_hw_to_check for given types."""
        all_output = {
            'x3000m0': {
                'Xname': XName('x3000m0'),
                'Type': 'CabinetPDUController',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            },
            'x3000c0r22b0': {
                'Xname': XName('x3000c0r22b0'),
                'Type': 'RouterBMC',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            },
            'x3000c0s11b0n0': {
                'Xname': XName('x3000c0s11b0n0'),
                'Type': 'Node',
                'Class': 'River',
                'Role': 'Management',
                'SubRole': 'Storage'
            },
            'x3000c0s11b0': {
                'Xname': XName('x3000c0s11b0'),
                'Type': 'NodeBMC',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            },
            'x3000c0s17b1n0': {
                'Xname': XName('x3000c0s17b1n0'),
                'Type': 'Node',
                'Class': 'River',
                'Role': 'Compute',
                'SubRole': 'MISSING'
            },
            'x3000c0s17b1': {
                'Xname': XName('x3000c0s17b1'),
                'Type': 'NodeBMC',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            },
            'x3000c0s17b999': {
                'Xname': XName('x3000c0s17b999'),
                'Type': 'ChassisBMC',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            },
            'x3000c0s1b0n0': {
                'Xname': XName('x3000c0s1b0n0'),
                'Type': 'Node',
                'Class': 'River',
                'Role': 'Management',
                'SubRole': 'Master'
            },
            'x3000c0s1b0': {
                'Xname': XName('x3000c0s1b0'),
                'Type': 'NodeBMC',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            },
            'x3000c0s24b0n0': {
                'Xname': XName('x3000c0s24b0n0'),
                'Type': 'Node',
                'Class': 'River',
                'Role': 'Management',
                'SubRole': 'Worker'
            },
            'x3000c0s24b0': {
                'Xname': XName('x3000c0s24b0'),
                'Type': 'NodeBMC',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            },
            'x3000c0s26b0n0': {
                'Xname': XName('x3000c0s26b0n0'),
                'Type': 'Node',
                'Class': 'River',
                'Role': 'Application',
                'SubRole': 'UAN'
            },
            'x3000c0s26b0': {
                'Xname': XName('x3000c0s26b0'),
                'Type': 'NodeBMC',
                'Class': 'River',
                'Role': 'MISSING',
                'SubRole': 'MISSING'
            }
        }
        if not include_types:
            return all_output

        expected_output = {}
        for xname, hw_dict in all_output.items():
            if hw_dict['Type'] in include_types:
                expected_output[xname] = hw_dict

        return expected_output

    def test_create_sls_hw_to_check(self):
        """Test create_sls_hw_to_check for all types."""
        expected_output = self.build_expected_output_of_create_sls_hw_to_check()
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        self.assertEqual(sls_hw_to_check, expected_output)

    def test_create_sls_hw_to_check_for_type_router_bmc(self):
        """Test create_sls_hw_to_check for RouterBMC."""
        self.fake_args.types = ['RouterBMC']
        expected_output = self.build_expected_output_of_create_sls_hw_to_check(self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        self.assertEqual(sls_hw_to_check, expected_output)

    def test_create_sls_hw_to_check_for_type_chassis_bmc(self):
        """Test create_sls_hw_to_check for ChassisBMC."""
        self.fake_args.types = ['ChassisBMC']
        expected_output = self.build_expected_output_of_create_sls_hw_to_check(self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        self.assertEqual(sls_hw_to_check, expected_output)

    def test_create_sls_hw_to_check_for_type_node_bmc(self):
        """Test create_sls_hw_to_check for NodeBMC."""
        self.fake_args.types = ['NodeBMC']
        expected_output = self.build_expected_output_of_create_sls_hw_to_check(self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        self.assertEqual(sls_hw_to_check, expected_output)

    def test_create_sls_hw_to_check_for_type_node(self):
        """Test create_sls_hw_to_check for Node."""
        self.fake_args.types = ['Node']
        expected_output = self.build_expected_output_of_create_sls_hw_to_check(self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        self.assertEqual(sls_hw_to_check, expected_output)

    def test_create_sls_hw_to_check_for_type_cabinet_pdu_controller(self):
        """Test create_sls_hw_to_check for CabinetPDUController."""
        self.fake_args.types = ['CabinetPDUController']
        expected_output = self.build_expected_output_of_create_sls_hw_to_check(self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        self.assertEqual(sls_hw_to_check, expected_output)

    @staticmethod
    def build_expected_output_of_create_crosscheck_results(include_types=None):
        """Build expected output of create_crosscheck_results for given types."""
        all_output = [
            [XName('x3000m0'),
             'CabinetPDUController',
             'River',
             'MISSING',
             'MISSING',
             'Class mismatch: SLS:River,HSM:MISSING'],
            [XName('x3000c0s11b0n0'),
             'Node',
             'River',
             'Management',
             'Storage',
             'SubRole mismatch: SLS:Storage,HSM:Worker'],
            [XName('x3000c0s17b999'),
             'ChassisBMC',
             'River',
             'MISSING',
             'MISSING',
             'SLS component missing in HSM Components'],
            [XName('x3000c0s17b999'),
             'ChassisBMC',
             'River',
             'MISSING',
             'MISSING',
             'SLS component missing in HSM Redfish Endpoints'],
            [XName('x3000c0s1b0'),
             'NodeBMC', 'River',
             'MISSING',
             'MISSING',
             'SLS component missing in HSM Components'],
            [XName('x3000c0s26b0n0'),
             'Node',
             'River',
             'Application',
             'UAN',
             'Class mismatch: SLS:River,HSM:Mountain']
        ]
        if not include_types:
            return all_output

        expected_output = []
        for output in all_output:
            if output[1] in include_types:
                expected_output.append(output)

        return expected_output

    def test_create_crosscheck_results(self):
        """Test create_crosscheck_results for all types and all checks."""
        expected_output = self.build_expected_output_of_create_crosscheck_results()
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        hsm_components = create_hsm_hw_to_crosscheck(self.all_hsm_components)
        hsm_redfish_endpoints = create_hsm_hw_to_crosscheck(self.all_hsm_redfish_endpoints)
        crosscheck_results = create_crosscheck_results(
            False,
            self.fake_args.checks,
            sls_hw_to_check,
            hsm_components,
            hsm_redfish_endpoints)
        self.assertEqual(crosscheck_results, expected_output)

    def test_create_crosscheck_results_for_type_chassis_bmc(self):
        """Test create_crosscheck_results for ChassisBMC for all checks."""
        self.fake_args.types = ['ChassisBMC']
        expected_output = self.build_expected_output_of_create_crosscheck_results(
            self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        hsm_components = create_hsm_hw_to_crosscheck(self.all_hsm_components)
        hsm_redfish_endpoints = create_hsm_hw_to_crosscheck(self.all_hsm_redfish_endpoints)
        crosscheck_results = create_crosscheck_results(
            False,
            self.fake_args.checks,
            sls_hw_to_check,
            hsm_components,
            hsm_redfish_endpoints)
        self.assertEqual(crosscheck_results, expected_output)

    def test_create_crosscheck_results_for_type_node_bmc(self):
        """Test create_crosscheck_results for NodeBMC for all checks."""
        self.fake_args.types = ['NodeBMC']
        expected_output = self.build_expected_output_of_create_crosscheck_results(
            self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        hsm_components = create_hsm_hw_to_crosscheck(self.all_hsm_components)
        hsm_redfish_endpoints = create_hsm_hw_to_crosscheck(self.all_hsm_redfish_endpoints)
        crosscheck_results = create_crosscheck_results(
            False,
            self.fake_args.checks,
            sls_hw_to_check,
            hsm_components,
            hsm_redfish_endpoints)
        self.assertEqual(crosscheck_results, expected_output)

    def test_create_crosscheck_results_for_type_node(self):
        """Test create_crosscheck_results for Node for all checks."""
        self.fake_args.types = ['Node']
        expected_output = self.build_expected_output_of_create_crosscheck_results(
            self.fake_args.types)
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        hsm_components = create_hsm_hw_to_crosscheck(self.all_hsm_components)
        hsm_redfish_endpoints = create_hsm_hw_to_crosscheck(self.all_hsm_redfish_endpoints)
        crosscheck_results = create_crosscheck_results(
            False,
            self.fake_args.checks,
            sls_hw_to_check,
            hsm_components,
            hsm_redfish_endpoints)
        self.assertEqual(crosscheck_results, expected_output)

    def test_create_crosscheck_results_for_check_class(self):
        """Test create_crosscheck_results for Class for all types."""
        self.fake_args.checks = ['Class']
        expected_output = [
            [XName('x3000m0'),
             'CabinetPDUController',
             'River',
             'MISSING',
             'MISSING',
             'Class mismatch: SLS:River,HSM:MISSING'],
            [XName('x3000c0s26b0n0'),
             'Node',
             'River',
             'Application',
             'UAN',
             'Class mismatch: SLS:River,HSM:Mountain']
        ]
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        hsm_components = create_hsm_hw_to_crosscheck(self.all_hsm_components)
        crosscheck_results = create_crosscheck_results(
            False,
            self.fake_args.checks,
            sls_hw_to_check,
            hsm_components,
            None)
        self.assertEqual(crosscheck_results, expected_output)

    def test_create_crosscheck_results_for_check_role(self):
        """Test create_crosscheck_results for Role for all types."""
        self.fake_args.checks = ['Role']
        expected_output = [
            [XName('x3000c0s11b0n0'),
             'Node',
             'River',
             'Management',
             'Storage',
             'SubRole mismatch: SLS:Storage,HSM:Worker']
        ]
        sls_hw_to_check = create_sls_hw_to_check(self.sls_hw_dumpstate, self.fake_args.types)
        hsm_components = create_hsm_hw_to_crosscheck(self.all_hsm_components)
        crosscheck_results = create_crosscheck_results(
            False,
            self.fake_args.checks,
            sls_hw_to_check,
            hsm_components,
            None)
        self.assertEqual(crosscheck_results, expected_output)


if __name__ == '__main__':
    unittest.main()
