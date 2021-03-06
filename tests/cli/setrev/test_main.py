#
# MIT License
#
# (C) Copyright 2019-2021 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.cli.setrev.main module.
"""


from argparse import Namespace
from datetime import datetime
import logging
import os
import os.path
import unittest
from unittest import mock

from boto3.exceptions import Boto3Error

import sat.cli.setrev.main


samples = os.path.join(os.path.dirname(__file__), 'samples')


EXAMPLE_SITE_DATA = {
    'Serial number': '1234',
    'Site name': 'site name',
    'System name': 'system name',
    'System install date': '1993-05-07',
    'System type': 'EX-1C'
}


class TestSetrevMain(unittest.TestCase):

    def setUp(self):
        """Sets up patches."""
        self.mock_s3 = mock.patch('sat.cli.setrev.main.get_s3_resource').start().return_value
        self.s3_bucket = 'sat'
        self.mock_get_config_value = mock.patch('sat.cli.setrev.main.get_config_value',
                                                return_value=self.s3_bucket).start()

        # Create a list of mock objects matching what SITE_FIELDS would look like
        self.mock_site_fields = mock.patch(
            'sat.cli.setrev.main.SITE_FIELDS',
            [self._mock_with_name(fld) for fld in EXAMPLE_SITE_DATA]
        ).start()

    def tearDown(self):
        """Stops all patches."""
        mock.patch.stopall()

    @staticmethod
    def _mock_with_name(name):
        """Return a mock.Mock() with its 'name' attribute set"""
        # you can't create a mock.Mock and specify its 'name' attribute in the constructor
        mock_object = mock.Mock()
        mock_object.name = name
        return mock_object

    def set_up_mock_yaml_load(self):
        """Patch the yaml.safe_load method"""
        self.mock_yaml_load = mock.patch('sat.cli.setrev.main.yaml.safe_load',
                                         return_value=EXAMPLE_SITE_DATA).start()

    def test_get_site_data_good_file(self):
        """get_site_data should return a dict after reading valid yaml.
        """
        path = '{}/good.yml'.format(samples)
        d = sat.cli.setrev.main.get_site_data(path)

        self.assertEqual(d['Serial number'], '12345shasdf')
        self.assertEqual(d['Site name'], 'site-name-with-spaces')
        self.assertEqual(d['System name'], 'my-sys')
        self.assertEqual(d['System install date'], '2019-10-08')
        self.assertEqual(d['System type'], 'fire-type')

    def test_get_site_data_only_strings(self):
        """The dict returned by get_site_data should only contain str types.
        """
        path = '{}/good.yml'.format(samples)
        d = sat.cli.setrev.main.get_site_data(path)

        for key, value in d.items():
            self.assertEqual(type(value), str)

    def test_get_site_data_file_not_found(self):
        """get_site_data should return empty dict if file doesn't exist.
        """
        path = 'idontexist.yml'
        d = sat.cli.setrev.main.get_site_data(path)
        self.assertEqual(d, {})

    @mock.patch('sat.cli.setrev.main.open', side_effect=PermissionError)
    def test_get_site_data_permission_error(self, mockopen):
        """get_site_data should throw permission error if file had bad perms.
        """
        path = '{}/good.yml'.format(samples)
        with self.assertRaises(PermissionError):
            d = sat.cli.setrev.main.get_site_data(path)

    def test_get_site_data_empty_file(self):
        """get_site_data should return empty dict if file was empty
        """
        path = '{}/empty'.format(samples)
        d = sat.cli.setrev.main.get_site_data(path)
        self.assertEqual(d, {})

    def test_get_site_data_non_yaml(self):
        """get_site_data should return empty dict if the file was non-yaml.
        """
        path = '{}/non-yaml.yml'.format(samples)
        d = sat.cli.setrev.main.get_site_data(path)
        self.assertEqual(d, {})

    def test_input_site_data(self):
        """Test input_site_data modifies data in place."""
        data_to_modify = {}

        sat.cli.setrev.main.input_site_data(data_to_modify)
        for mock_site_field in self.mock_site_fields:
            mock_site_field.prompt.assert_called_once_with(data_to_modify)

        self.assertEqual(
            data_to_modify,
            {fld.name: fld.prompt.return_value for fld in self.mock_site_fields}
        )

    def test_input_site_data_with_existing_data(self):
        """Test input_site_data replaces old data and adds new fields."""
        data_to_modify = {
            'Serial number': '567890'
        }

        sat.cli.setrev.main.input_site_data(data_to_modify)
        for mock_site_field in self.mock_site_fields:
            mock_site_field.prompt.assert_called_once_with(data_to_modify)

        self.assertEqual(
            data_to_modify,
            {fld.name: fld.prompt.return_value for fld in self.mock_site_fields}
        )

    def test_write_site_data_newfile(self):
        """write_site_data should create the file if it doesn't exist.
        """
        sitefile = '{}/path/to/not/exist'.format(samples)
        d1 = {}

        m = mock.mock_open()
        with mock.patch('sat.cli.setrev.main.open', m):
            sat.cli.setrev.main.write_site_data(sitefile, d1)

        m.assert_called_once_with(sitefile, 'w')

    def test_write_site_data_readback(self):
        """write_site_data should read identically from data it's written.
        """
        try:
            sitefile = '{}/sitefile1.yml'.format(samples)

            if os.path.exists(sitefile):
                os.remove(sitefile)

            # test that data is read the same as it is written
            sat.cli.setrev.main.write_site_data(sitefile, EXAMPLE_SITE_DATA)
            loaded_data = sat.cli.setrev.main.get_site_data(sitefile)

            self.assertEqual(EXAMPLE_SITE_DATA, loaded_data)
        finally:
            if os.path.exists(sitefile):
                os.remove(sitefile)

    def test_write_site_data_overwrite(self):
        """write_site_data should overwrite existing entries
        """

        try:
            sitefile = '{}/sitefile1.yml'.format(samples)
            sat.cli.setrev.main.write_site_data(sitefile, EXAMPLE_SITE_DATA)
            sat.cli.setrev.main.write_site_data(sitefile, {})

            empty = {}
            result = sat.cli.setrev.main.get_site_data(sitefile)

            self.assertEqual(empty, empty)
        finally:
            if os.path.exists(sitefile):
                os.remove(sitefile)

    def test_get_site_data_s3(self):
        """When reading site data, download from S3."""
        self.set_up_mock_yaml_load()
        sitefile = '/opt/cray/etc/site_info.yml'
        with mock.patch('builtins.open') as mock_open:
            sat.cli.setrev.main.get_site_data(sitefile)

        self.mock_s3.Object.assert_called_once_with(self.s3_bucket, sitefile)
        self.mock_s3.Object.return_value.download_file.assert_called_once_with(sitefile)
        self.mock_yaml_load.assert_called_once_with(
            mock_open.return_value.__enter__.return_value.read.return_value
        )

    def test_get_site_data_no_s3(self):
        """When reading site data, if S3 is not available fall back on a local file."""
        self.set_up_mock_yaml_load()
        self.mock_s3.Object.return_value.upload_file.side_effect = Boto3Error
        sitefile = '/opt/cray/etc/site_info.yml'
        with mock.patch('builtins.open') as mock_open:
            sat.cli.setrev.main.get_site_data(sitefile)

        self.mock_s3.Object.assert_called_once_with(self.s3_bucket, sitefile)
        self.mock_s3.Object.return_value.download_file.assert_called_once_with(sitefile)
        self.mock_yaml_load.assert_called_once_with(
            mock_open.return_value.__enter__.return_value.read.return_value
        )

    def test_write_site_data_s3(self):
        """write_site_data should upload to S3"""
        self.set_up_mock_yaml_load()
        sitefile = '/opt/cray/etc/site_info.yml'
        with mock.patch('builtins.open') as mock_open:
            sat.cli.setrev.main.write_site_data(sitefile, EXAMPLE_SITE_DATA)

        mock_open.assert_called_once_with(sitefile, 'w')
        # Just assert file was written; assume the other tests test the writing behavior
        mock_open.return_value.__enter__.return_value.write.assert_called()
        self.mock_s3.Object.assert_called_once_with(self.s3_bucket, sitefile)
        self.mock_s3.Object.return_value.upload_file.assert_called_once_with(sitefile)

    def test_write_site_data_no_s3(self):
        """When S3 is not working, a local file should be written and an error logged."""
        self.set_up_mock_yaml_load()
        sitefile = '/opt/cray/etc/site_info.yml'
        self.mock_s3.Object.return_value.upload_file.side_effect = Boto3Error
        with mock.patch('builtins.open') as mock_open:
            with self.assertLogs(level=logging.ERROR):
                sat.cli.setrev.main.write_site_data(sitefile, EXAMPLE_SITE_DATA)

        mock_open.assert_called_once_with(sitefile, 'w')
        # Just assert file was written; assume the other tests test the writing behavior
        mock_open.return_value.__enter__.return_value.write.assert_called()
        self.mock_s3.Object.assert_called_once_with(self.s3_bucket, sitefile)
        self.mock_s3.Object.return_value.upload_file.assert_called_once_with(sitefile)


def set_options(namespace):
    """Set default options for Namespace."""
    namespace.sitefile = '/sol/saturn/tethys_info.yml'
    namespace.no_borders = True
    namespace.no_headings = False
    namespace.format = 'pretty'
    namespace.reverse = object()
    namespace.sort_by = object()
    namespace.filter_strs = object()


class FakeStream:
    """Used for mocking the return from open."""
    def close(self):
        pass


class TestDoSetrev(unittest.TestCase):
    """Unit test for Setrev do_setrev()."""

    def setUp(self):
        """Mock functions called by do_setrev."""

        # Mock get_site_data to return site data. If a test wishes to
        # change the mock_site_data, the test should do something like:
        #     self.mock_site_data.return_value = {...}

        # The data returned by get_site_data:
        self.mock_site_data = {
            'Serial number': '2-4-8-16-32-64',
            'Site name': 'Saturn',
            'System name': 'Tethys',
            'System install': '',
            'System install date': datetime.today().strftime('%Y-%m-%d'),
            'System type': 'moon'
        }
        self.mock_get_site_data = mock.patch('sat.cli.setrev.main.get_site_data',
                                             return_value=self.mock_site_data,
                                             autospec=True).start()

        self.mock_input_site_data = mock.patch('sat.cli.setrev.main.input_site_data',
                                               autospec=True).start()
        self.mock_write_site_data = mock.patch('sat.cli.setrev.main.write_site_data',
                                               autospec=True).start()

        self.mock_get_config_value = mock.patch('sat.cli.setrev.main.get_config_value',
                                                return_value='/opt/cray/etc/site_info.yml',
                                                autospec=True).start()

        self.mock_os_path_dirname = mock.patch('os.path.dirname',
                                               return_value='/sol/saturn').start()
        self.mock_os_path_exists = mock.patch('os.path.exists',
                                              return_value=False).start()
        self.mock_os_makedirs = mock.patch('os.makedirs').start()

        self.mock_open = mock.patch('builtins.open', return_value=FakeStream(),
                                    autospec=True).start()

        self.parsed = Namespace()
        set_options(self.parsed)

    def tearDown(self):
        mock.patch.stopall()

    def test_opt_dir_missing(self):
        """Test setrev: do_setrev() option sitefile directory missing """
        sat.cli.setrev.main.do_setrev(self.parsed)
        self.mock_get_config_value.assert_not_called()
        self.mock_os_path_dirname.assert_called_once_with('/sol/saturn/tethys_info.yml')
        self.mock_os_path_exists.assert_called_once_with('/sol/saturn')
        self.mock_os_makedirs.assert_called_once_with('/sol/saturn')
        self.mock_open.assert_called_once_with('/sol/saturn/tethys_info.yml', 'a')

    def test_opt_dir_exists(self):
        """Test setrev: do_setrev() option sitefile directory exists """
        self.mock_os_path_exists.return_value = True
        sat.cli.setrev.main.do_setrev(self.parsed)
        self.mock_get_config_value.assert_not_called()
        self.mock_os_path_dirname.assert_called_once_with('/sol/saturn/tethys_info.yml')
        self.mock_os_path_exists.assert_called_once_with('/sol/saturn')
        self.mock_os_makedirs.assert_not_called()
        self.mock_open.assert_called_once_with('/sol/saturn/tethys_info.yml', 'a')

    def test_conf_dir_missing(self):
        """Test setrev: do_setrev() config sitefile directory missing """
        self.parsed.sitefile = None
        self.mock_os_path_dirname.return_value = '/opt/cray/etc'
        sat.cli.setrev.main.do_setrev(self.parsed)
        self.mock_get_config_value.assert_called_once()
        self.mock_os_path_dirname.assert_called_once_with('/opt/cray/etc/site_info.yml')
        self.mock_os_path_exists.assert_called_once_with('/opt/cray/etc')
        self.mock_os_makedirs.assert_called_once_with('/opt/cray/etc')
        self.mock_open.assert_called_once_with('/opt/cray/etc/site_info.yml', 'a')

    def test_conf_dir_exists(self):
        """Test setrev: do_setrev() config sitefile directory exists """
        self.parsed.sitefile = None
        self.mock_os_path_dirname.return_value = '/opt/cray/etc'
        self.mock_os_path_exists.return_value = True
        sat.cli.setrev.main.do_setrev(self.parsed)
        self.mock_get_config_value.assert_called_once()
        self.mock_os_path_dirname.assert_called_once_with('/opt/cray/etc/site_info.yml')
        self.mock_os_path_exists.assert_called_once_with('/opt/cray/etc')
        self.mock_os_makedirs.assert_not_called()
        self.mock_open.assert_called_once_with('/opt/cray/etc/site_info.yml', 'a')

    def test_no_sitefile_specified(self):
        """Test setrev: do_setrev() no sitefile specified """
        self.parsed.sitefile = None
        self.mock_get_config_value.return_value = {}
        with self.assertRaises(SystemExit):
            sat.cli.setrev.main.do_setrev(self.parsed)
        self.mock_get_config_value.assert_called_once()

    def test_file_permission_error(self):
        """Test setrev: do_setrev() sitefile permission error"""
        self.mock_os_path_exists.return_value = True
        self.mock_open.side_effect = PermissionError
        with self.assertRaises(SystemExit):
            sat.cli.setrev.main.do_setrev(self.parsed)
        self.mock_get_config_value.assert_not_called()
        self.mock_os_path_dirname.assert_called_once_with('/sol/saturn/tethys_info.yml')
        self.mock_os_path_exists.assert_called_once_with('/sol/saturn')
        self.mock_os_makedirs.assert_not_called()
        self.mock_open.assert_called_once_with('/sol/saturn/tethys_info.yml', 'a')


if __name__ == '__main__':
    unittest.main()
