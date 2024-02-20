#
# MIT License
#
# (C) Copyright 2022, 2024 Hewlett Packard Enterprise Development LP
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
Tests for the sat.cli.status.status_module module.
"""
from abc import ABC
import inspect
import unittest
import logging
from unittest.mock import MagicMock, patch

from csm_api_client.service.gateway import APIError
import sat.cli.status.status_module as status_module_module
from sat.cli.status.status_module import (
    BOSStatusModule,
    StatusModule,
    StatusModuleException,
)
from sat.constants import MISSING_VALUE


class BaseStatusModuleTestCase(unittest.TestCase):
    def setUp(self):
        self.modules = []
        patch.object(StatusModule, '_modules', self.modules).start()

        self.mock_get_config_value = patch('sat.cli.status.status_module.get_config_value').start()

    def tearDown(self):
        patch.stopall()


class TestStatusModuleSubclassing(BaseStatusModuleTestCase):
    """Tests for the subclassing StatusModule."""

    def test_status_modules_added(self):
        """Test that StatusModule subclasses are registered"""
        class TestStatusModule(StatusModule, ABC):
            pass  # Don't need to define methods, no instances are created.

        self.assertIn(TestStatusModule, StatusModule._modules)

    def test_status_modules_class_attr_isolated(self):
        """Test that we aren't accidentally modifying the real StatusModule._modules and impacting other tests."""
        self.assertEqual(0, len(StatusModule._modules))
        patch.stopall()
        implemented_submodules = [
            module for _, module in inspect.getmembers(status_module_module, inspect.isclass)
            if issubclass(module, StatusModule) and module is not StatusModule
        ]
        self.assertCountEqual(implemented_submodules, StatusModule._modules)


class TestStatusModuleGettingModules(BaseStatusModuleTestCase):
    """Tests for retrieving specific modules"""
    def setUp(self):
        super().setUp()

        class NodeTestModule(StatusModule, ABC):
            component_types = {'Node'}
        self.NodeTestModule = NodeTestModule

        class NodeBMCTestModule(StatusModule, ABC):
            component_types = {'NodeBMC'}
        self.NodeBMCTestModule = NodeBMCTestModule

        class PrimaryTestModule(StatusModule, ABC):
            primary = True
        self.PrimaryTestModule = PrimaryTestModule

    def test_getting_relevant_modules(self):
        """Test that relevant modules are returned by get_relevant_modules()"""
        self.assertIn(self.NodeTestModule, StatusModule.get_relevant_modules(component_type='Node'))

    def test_irrelevant_modules_ignored(self):
        """Test that irrelevant modules are ignored by get_relevant_modules()"""
        self.assertNotIn(self.NodeBMCTestModule, StatusModule.get_relevant_modules(component_type='Node'))

    def test_all_modules_returned_no_component_types(self):
        """Test that all modules are returned if no component types specified"""
        self.assertEqual(self.modules, StatusModule.get_relevant_modules())

    def test_limit_subset_of_modules_returned(self):
        """Test that a limited subset of modules can be returned by get_relevant_modules()"""
        self.assertEqual([self.NodeTestModule],
                         StatusModule.get_relevant_modules(limit_modules=[self.NodeTestModule]))

    def test_getting_primary_module(self):
        """Test getting the primary module"""
        self.assertEqual(StatusModule.get_primary(), self.PrimaryTestModule)

    def test_can_only_get_one_primary_module(self):
        """Test that there can only be one primary module"""
        class AnotherPrimaryModule(StatusModule, ABC):
            primary = True

        with self.assertRaises(ValueError):
            StatusModule.get_primary()


class TestStatusModuleHeadings(BaseStatusModuleTestCase):
    """Tests for getting lists of table headings"""
    def setUp(self):
        super().setUp()

        class SomeTestStatusModule(StatusModule, ABC):
            headings = ['xname', 'some_attribute']
        self.SomeTestStatusModule = SomeTestStatusModule

        class AnotherTestStatusModule(StatusModule, ABC):
            headings = ['xname', 'another_attribute', 'one_more_attribute']
        self.AnotherTestStatusModule = AnotherTestStatusModule

    def test_get_all_headings(self):
        """Test getting headings for all StatusModules"""
        self.assertEqual(StatusModule.get_all_headings(primary_key='xname'),
                         ['xname', 'some_attribute', 'another_attribute', 'one_more_attribute'])

    def test_get_all_headings_initial(self):
        """Test ordering StatusModule headings manually with initial_headings"""
        self.assertEqual(StatusModule.get_all_headings(primary_key='xname',
                                                       initial_headings=['another_attribute']),
                         ['xname', 'another_attribute', 'some_attribute', 'one_more_attribute'])

    def test_get_all_headings_from_some_modules(self):
        """Test getting the headings from a subset of modules"""
        self.assertEqual(StatusModule.get_all_headings(primary_key='xname',
                                                       limit_modules=[self.SomeTestStatusModule]),
                         self.SomeTestStatusModule.headings)

    def test_get_all_headings_subset_with_manual_order(self):
        """Test ordering headings manually with a subset of modules"""
        self.assertEqual(StatusModule.get_all_headings(primary_key='xname',
                                                       limit_modules=[self.AnotherTestStatusModule],
                                                       initial_headings=['one_more_attribute']),
                         ['xname', 'one_more_attribute', 'another_attribute'])


class TestGettingRows(BaseStatusModuleTestCase):
    """Tests for getting populated rows"""
    def setUp(self):
        super().setUp()
        self.all_rows = [
            {'xname': 'x3000c0s1b0n0',
             'state': 'on',
             'config': 'some_config'},
            {'xname': 'x3000c0s1b0n1',
             'state': 'off',
             'config': 'another_config'},
        ]
        outer_self = self

        class TestStatusModuleOne(StatusModule):
            primary = True
            source_name = 'one'
            headings = ['xname', 'state']

            @property
            def rows(self):
                return [{key: row[key] for key in self.headings if key in row}
                        for row in outer_self.all_rows]

        self.TestStatusModuleOne = TestStatusModuleOne

        self.test_module_two_rows = {'x3000c0s1b0n0', 'x3000c0s1b0n1'}

        class TestStatusModuleTwo(StatusModule):
            headings = ['xname', 'config']
            source_name = 'two'

            @property
            def rows(self):
                return [{key: row[key] for key in self.headings}
                        for row in outer_self.all_rows
                        if row['xname'] in outer_self.test_module_two_rows]

        self.TestStatusModuleTwo = TestStatusModuleTwo

    def test_getting_populated_rows(self):
        """Test getting rows in the successful case"""
        for row in StatusModule.get_populated_rows(primary_key='xname', session=MagicMock()):
            self.assertIn(row, self.all_rows)

    def test_getting_populated_rows_fails(self):
        """Test that columns from failing modules are omitted"""
        bad_key = 'irrelevant information'

        class TestStatusModuleFails(StatusModule):
            source_name = 'failure'
            headings = ['xname', bad_key]

            @property
            def rows(self):
                raise StatusModuleException('Information is irrelevant!')

        with self.assertLogs(level='WARNING'):
            rows = StatusModule.get_populated_rows(primary_key='xname', session=MagicMock())

        for row in rows:
            for heading, value in row.items():
                if heading == bad_key:
                    self.assertEqual(value, MISSING_VALUE)
                else:
                    self.assertNotEqual(value, MISSING_VALUE)

    def test_getting_populated_rows_subset_of_modules(self):
        """Test that rows can be retrieved with a subset of modules"""
        rows = StatusModule.get_populated_rows(primary_key='xname', session=MagicMock(),
                                               limit_modules=[self.TestStatusModuleOne])
        for populated_row, original_row in zip(rows, self.all_rows):
            for heading in self.TestStatusModuleOne.headings:
                self.assertEqual(populated_row[heading], original_row[heading])
            self.assertNotIn('config', populated_row)

    def test_missing_column(self):
        """Test that rows with missing input fields output the value 'MISSING' in those fields"""
        missing_state_xname = 'x3000c0s1b0n2'
        self.all_rows.append(
            {
                'xname': missing_state_xname,
                'config': 'yet_another_config',
            }
        )
        rows = StatusModule.get_populated_rows(primary_key='xname', session=MagicMock(),
                                               limit_modules=[self.TestStatusModuleOne])

        row_had_missing_state = False
        for row in rows:
            if row['xname'] == missing_state_xname:
                self.assertEqual(row['state'], MISSING_VALUE)
                row_had_missing_state = True

        if not row_had_missing_state:
            self.fail('Rows with missing "state" field were omitted')

    def test_row_missing_from_module(self):
        """Test that a module's fields are marked as MISSING if their primary key is missing in that module"""
        missing_module_two_xname = 'x3000c0s1b0n1'
        self.test_module_two_rows.remove(missing_module_two_xname)

        rows = StatusModule.get_populated_rows(primary_key='xname', session=MagicMock())
        row_had_missing_config = False
        for row in rows:
            if row['xname'] == missing_module_two_xname:
                self.assertEqual(row['config'], MISSING_VALUE)
                row_had_missing_config = True

        if not row_had_missing_config:
            self.fail('Rows with missing "state" field were omitted')


class TestBOSStatusModule(BaseStatusModuleTestCase):
    """Tests for the BOSStatusModule class"""

    def setUp(self):
        super().setUp()

        self.xname = 'x1000c0s0b1n0'
        self.img_id = '12345678-abcd-efef-abcd-1234567890ab'
        self.img_name = 'some-image'
        self.bos_session = 'abcdef01-abcd-abcd-abcd-12345abcdefa'
        self.bos_sessiontemplate = 'some-session-template'
        self.bos_component = {
            'actual_state': {
                'boot_artifacts': {
                    'initrd': f's3://boot-images/{self.img_id}/initrd',
                    'kernel': f's3://boot-images/{self.img_id}/kernel',
                    'kernel_parameters': 'console=ttyS0'
                },
                'configuration': '',
                'last_updated': '2022-01-01T00:00:00'
            },
            'desired_state': {
                'boot_artifacts': {
                    'initrd': 's3://boot-images/9c80b8fb-190c-4adc-bef6-895928f4f262/initrd',
                    'kernel': 's3://boot-images/9c80b8fb-190c-4adc-bef6-895928f4f262/kernel',
                    'kernel_parameters': 'console=ttyS0'
                },
                'configuration': '',
                'last_updated': '2022-01-01T00:00:00'
            },
            'enabled': False,
            'error': '',
            'id': self.xname,
            'last_action': {
                'action': 'powering_on',
                'last_updated': '2022-01-01T00:00:00',
                'num_attempts': 1
            },
            'session': self.bos_session,
            'staged_state': {
                'last_updated': '2022-01-01T00:00:00'
            },
            'status': {
                'phase': '',
                'status': 'stable',
                'status_override': ''
            }
        }

        self.mock_bos_client = MagicMock()
        self.mock_bos_client.get_session.return_value = {
            'components': self.xname,
            'limit': '',
            'name': self.bos_session,
            'operation': 'boot',
            'stage': False,
            'status': {
                'end_time': '2022-01-01T00:00:00',
                'error': None,
                'start_time': '2022-01-01T00:01:00',
                'status': 'complete',
            },
            'template_name': self.bos_sessiontemplate,
        }

        self.mock_bos_client.get_components.return_value = [self.bos_component]
        patch('sat.cli.status.status_module.BOSClientCommon.get_bos_client',
              return_value=self.mock_bos_client).start()

        self.mock_ims_client = MagicMock()
        self.mock_ims_client.get_image.return_value = {
            'created': '2022-01-01T00:00:00',
            'id': self.img_id,
            'link': {
                'etag': 'abcdef123456789abcdef12345678909',
                'path': f's3://boot-images/{self.img_id}/manifest.json',
                'type': 's3',
            },
            'name': self.img_name,
        }
        patch('sat.cli.status.status_module.IMSClient', return_value=self.mock_ims_client).start()

        self.session = MagicMock()

    def test_can_use_in_bos_v1(self):
        """Test checking if BOSStatusModule can be used with BOS v1"""
        self.mock_get_config_value.return_value = 'v1'
        can_use, err_msg = BOSStatusModule.can_use()
        self.assertFalse(can_use)
        self.assertIsInstance(err_msg, str)

    def test_can_use_in_bos_v2(self):
        """Test checking if BOSStatusModule can be used with BOS v2"""
        self.mock_get_config_value.return_value = 'v2'
        can_use, err_msg = BOSStatusModule.can_use()
        self.assertTrue(can_use)
        self.assertIsNone(err_msg)

    def test_retrieving_component_sessions_can_be_retrieved(self):
        """Test that component status can be retrieved from BOS v2"""
        rows = BOSStatusModule(session=self.session).rows

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], {
            'xname': self.xname,
            'Boot Status': 'stable',
            'Most Recent BOS Session': self.bos_session,
            'Most Recent Image': self.img_name,
            'Most Recent Session Template': self.bos_sessiontemplate,
        })

    def test_empty_session_for_component(self):
        """Test retrieving component status if session field is empty"""
        self.bos_component['session'] = ''
        rows = BOSStatusModule(session=self.session).rows

        self.assertEqual(rows[0], {
            'xname': self.xname,
            'Boot Status': 'stable',
            'Most Recent BOS Session': MISSING_VALUE,
            'Most Recent Image': self.img_name,
        })

    def test_no_session_key_for_component(self):
        """Test retrieving component status if there is no "session" key"""
        del self.bos_component['session']
        rows = BOSStatusModule(session=self.session).rows

        self.assertEqual(rows[0], {
            'xname': self.xname,
            'Boot Status': 'stable',
            'Most Recent BOS Session': MISSING_VALUE,
            'Most Recent Image': self.img_name,
        })

    def test_session_key_empty_string(self):
        """Test retrieving component status the "session" key is empty"""
        self.bos_component['session'] = ''
        rows = BOSStatusModule(session=self.session).rows
        self.assertEqual(rows[0], {
            'xname': self.xname,
            'Boot Status': 'stable',
            'Most Recent BOS Session': MISSING_VALUE,
            'Most Recent Image': self.img_name,
        })

    def test_get_session_apierror(self):
        """Test retrieving component boot status when no session is found"""
        self.mock_bos_client.get_session.side_effect = APIError
        rows = BOSStatusModule(session=self.session).rows

        self.assertEqual(rows[0], {
            'xname': self.xname,
            'Boot Status': 'stable',
            'Most Recent BOS Session': self.bos_session,
            'Most Recent Image': self.img_name,
        })

    def test_get_session_missing_template_name(self):
        """Test retrieving component status when the session template is missing from the session"""
        del self.mock_bos_client.get_session.return_value['template_name']
        with self.assertLogs(level=logging.WARNING) as logs_cm:
            rows = BOSStatusModule(session=self.session).rows

        self.assertEqual(len(logs_cm.records), 1)
        self.assertRegex(logs_cm.records[0].message,
                         "Unable to determine session template .* due to missing 'template_name' key")

        self.assertEqual(len(rows), 1)
        self.assertEqual(rows[0], {
            'xname': self.xname,
            'Boot Status': 'stable',
            'Most Recent BOS Session': self.bos_session,
            'Most Recent Image': self.img_name,
        })
