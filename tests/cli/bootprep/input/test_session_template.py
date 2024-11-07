#
# MIT License
#
# (C) Copyright 2023-2024 Hewlett Packard Enterprise Development LP
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
Tests for functionality in the InputSessionTemplate class and subclasses
"""
from jinja2.sandbox import SandboxedEnvironment
import unittest
from unittest.mock import Mock

from sat.cli.bootprep.input.session_template import InputSessionTemplateV2
from sat.cli.bootprep.errors import InputItemValidateError


class TestInputSessionTemplateV2(unittest.TestCase):

    def setUp(self):
        self.input_instance = Mock()
        self.index = 0
        self.jinja_env = SandboxedEnvironment()
        self.jinja_env.globals = {
            'default': {
                'system_name': 'drax',
                'site_domain': 'example.com',
            }
        }
        self.bos_client = Mock()
        self.mock_base_boot_set_data = {
            'rootfs_provider': 'cpss3'
        }
        self.bos_client.get_base_boot_set_data.return_value = self.mock_base_boot_set_data
        self.cfs_client = Mock()
        self.ims_client = Mock()

        self.mock_image_id = '17b649e6-94b3-4ede-a179-d911a1c26468'
        self.mock_etag = '20dd8b6d42071198195134ef8e1619d8'
        self.mock_path = f's3://boot-images/{self.mock_image_id}/manifest.json'
        self.mock_image_type = 's3'
        self.mock_image_link = {
            'etag': self.mock_etag,
            'path': self.mock_path,
            'type': self.mock_image_type
        }
        test_self = self

        class SimplifiedInputSessionTemplateV2(InputSessionTemplateV2):
            """A simplified version of MockInputSessionTemplateV2.

            Useful for testing methods that use these methods without testing these methods.
            """

            def validate_image_exists(self, **_):
                """Simplified validation that only support IMS images by name"""
                if self.ims_image_name:
                    return {'name': self.ims_image_name}
                else:
                    raise InputItemValidateError(f'{self.__class__} only supports '
                                                 f'IMS images specified by name.')

            @property
            def image_record(self):
                """Simplified version that does not actually query IMS."""
                image_record = self.validate_image_exists()
                image_record['id'] = test_self.mock_image_id
                image_record['link'] = test_self.mock_image_link
                return image_record

        self.simplified_session_template_v2 = SimplifiedInputSessionTemplateV2

    def get_input_and_expected_bos_data(self, name='my-session-template',
                                        image_name='my-image', configuration='my-config',
                                        arch_by_bootset=None):
        """Get input data and the expected BOS request payload with given parameters"""
        if not arch_by_bootset:
            arch_by_bootset = {'compute': None}

        input_bootsets = {}
        bos_payload_bootsets = {}
        for boot_set_name, boot_set_arch in arch_by_bootset.items():
            input_bootsets[boot_set_name] = {
                'node_roles_groups': ['Compute'],
                'rootfs_provider': 'sbps',
                'rootfs_provider_passthrough': ('sbps:v1:iqn.2023-06.csm.iscsi:_sbps-hsn._tcp.'
                                                '{{default.system_name}}.{{default.site_domain}}:300')
            }
            bos_payload_bootsets[boot_set_name] = self.mock_base_boot_set_data.copy()
            bos_payload_bootsets[boot_set_name].update({
                'node_roles_groups': ['Compute'],
                'rootfs_provider': 'sbps',
                'rootfs_provider_passthrough': ('sbps:v1:iqn.2023-06.csm.iscsi:_sbps-hsn._tcp.'
                                                'drax.example.com:300'),
                'path': self.mock_path,
                'etag': self.mock_etag,
                'type': self.mock_image_type
            })
            if boot_set_arch:
                input_bootsets[boot_set_name]['arch'] = boot_set_arch
                bos_payload_bootsets[boot_set_name]['arch'] = boot_set_arch

        input_data = {
            'name': name,
            'image': {'ims': {'name': image_name}},
            'configuration': configuration,
            'bos_parameters': {
                'boot_sets': input_bootsets
            }
        }
        bos_payload = {
            'name': name,
            'cfs': {'configuration': configuration},
            'enable_cfs': True,
            'boot_sets': bos_payload_bootsets
        }

        return input_data, bos_payload

    def test_get_create_item_data_no_arch(self):
        """Test get_create_item_data method with no architecture specified"""
        input_data, expected_bos_data = self.get_input_and_expected_bos_data()

        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )

        self.assertEqual(expected_bos_data,
                         input_session_template.get_create_item_data())

    def test_get_create_item_data_arch_per_bootset(self):
        """Test get_create_item_data with a different arch per boot set"""
        input_data, expected_bos_data = self.get_input_and_expected_bos_data(
            arch_by_bootset={'compute_x86_64': 'x86_64',
                             'compute_aarch64': 'aarch64'}
        )

        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )

        self.assertEqual(expected_bos_data,
                         input_session_template.get_create_item_data())

    def test_validate_rootfs_provider_good(self):
        """Test that validate_rootfs_provider passes with good data"""
        input_data, _ = self.get_input_and_expected_bos_data()
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        input_session_template.validate_rootfs_provider_has_value()

    def test_validate_rootfs_provider_bad(self):
        """Test that validate_rootfs_provider fails with bad data"""
        input_data, _ = self.get_input_and_expected_bos_data()
        input_data['bos_parameters']['boot_sets']['compute']['rootfs_provider'] = ''
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        err_regex = 'The value of rootfs_provider for boot set compute cannot be an empty string'
        with self.assertRaisesRegex(InputItemValidateError, err_regex):
            input_session_template.validate_rootfs_provider_has_value()

    def test_validate_rootfs_provider_multiple_good(self):
        """Test that validate_rootfs_provider passes with good data in multiple boot sets"""
        input_data, _ = self.get_input_and_expected_bos_data()
        compute_boot_set = input_data['bos_parameters']['boot_sets']['compute']
        input_data['bos_parameters']['boot_sets']['compute_two'] = compute_boot_set
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        input_session_template.validate_rootfs_provider_has_value()

    def test_validate_rootfs_provider_multiple_bad(self):
        """Test that validate_rootfs_provider fails with bad data in multiple boot sets"""
        input_data, _ = self.get_input_and_expected_bos_data()
        input_data['bos_parameters']['boot_sets']['compute']['rootfs_provider'] = ''
        compute_boot_set = input_data['bos_parameters']['boot_sets']['compute']
        input_data['bos_parameters']['boot_sets']['compute_two'] = compute_boot_set
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        err_regex = 'The value of rootfs_provider for boot set compute cannot be an empty string'
        with self.assertRaisesRegex(InputItemValidateError, err_regex):
            input_session_template.validate_rootfs_provider_has_value()

    def test_validate_rootfs_provider_passthrough_good(self):
        """Test that validate_rootfs_provider_passthrough passes with good data"""
        input_data, _ = self.get_input_and_expected_bos_data()
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        input_session_template.validate_rootfs_provider_passthrough_has_value()

    def test_validate_rootfs_provider_passthrough_bad(self):
        """Test that validate_rootfs_provider_passthrough fails with bad data"""
        input_data, _ = self.get_input_and_expected_bos_data()
        input_data['bos_parameters']['boot_sets']['compute']['rootfs_provider_passthrough'] = ''
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        err_regex = 'The value of rootfs_provider_passthrough for boot set compute cannot be an empty string'
        with self.assertRaisesRegex(InputItemValidateError, err_regex):
            input_session_template.validate_rootfs_provider_passthrough_has_value()

    def test_validate_rootfs_provider_passthrough_multiple_good(self):
        """Test that validate_rootfs_provider_passthrough passes with good data in multiple boot sets"""
        input_data, _ = self.get_input_and_expected_bos_data()
        compute_boot_set = input_data['bos_parameters']['boot_sets']['compute']
        input_data['bos_parameters']['boot_sets']['compute_two'] = compute_boot_set
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        input_session_template.validate_rootfs_provider_passthrough_has_value()

    def test_validate_rootfs_provider_passthrough_multiple_bad(self):
        """Test that validate_rootfs_provider_passthrough fails with bad data in multiple boot sets"""
        input_data, _ = self.get_input_and_expected_bos_data()
        input_data['bos_parameters']['boot_sets']['compute']['rootfs_provider_passthrough'] = ''
        compute_boot_set = input_data['bos_parameters']['boot_sets']['compute']
        input_data['bos_parameters']['boot_sets']['compute_two'] = compute_boot_set
        input_session_template = self.simplified_session_template_v2(
            input_data, self.input_instance, 0, self.jinja_env,
            self.bos_client, self.cfs_client, self.ims_client
        )
        err_regex = 'The value of rootfs_provider_passthrough for boot set compute cannot be an empty string'
        with self.assertRaisesRegex(InputItemValidateError, err_regex):
            input_session_template.validate_rootfs_provider_passthrough_has_value()


if __name__ == '__main__':
    unittest.main()
