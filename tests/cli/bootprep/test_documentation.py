"""
Tests for the sat.cli.bootprep.documentation module.

(C) Copyright 2021 Hewlett Packard Enterprise Development LP.

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

import os
import shlex
import unittest
from unittest.mock import patch

from sat.cli.bootprep.documentation import (
    BootPrepDocsError,
    DEFAULT_TAR_MODE,
    display_schema,
    generate_docs_tarball,
)
from sat.cli.bootprep.constants import DOCS_ARCHIVE_FILE_NAME, DOCS_ARCHIVE_NAME


class TestGenerateTarball(unittest.TestCase):
    """Tests for the generate_docs_tarball() function"""
    def setUp(self):
        self.schema_path = 'path/to/schema'
        self.output_dir = '/some/output/dir'
        self.output_path = os.path.join(self.output_dir, DOCS_ARCHIVE_FILE_NAME)
        self.temp_dir = '/some/tmp/dir'

        self.mock_cwd = patch('sat.cli.bootprep.documentation.cwd').start()
        self.mock_mkdir = patch('sat.cli.bootprep.documentation.os.mkdir').start()
        self.mock_temp_dir = patch('sat.cli.bootprep.documentation.tempfile.TemporaryDirectory').start()
        self.mock_temp_dir.return_value.__enter__.return_value = self.temp_dir

        self.mock_generate = patch('sat.cli.bootprep.documentation.generate_from_filename').start()
        self.mock_tar_file = patch('sat.cli.bootprep.documentation.tarfile.TarFile',
                                   autospec=True).start()
        self.mock_tar_file.name = self.output_path
        self.mock_tar_open = patch('sat.cli.bootprep.documentation.tarfile.open').start()
        self.mock_tar_open.return_value.__enter__.return_value = self.mock_tar_file

    def tearDown(self):
        patch.stopall()

    def test_generate_tarball_successful(self):
        """Test successfully generating a documentation tarball"""
        generate_docs_tarball(self.schema_path, self.output_dir)
        self.mock_generate.assert_called_once()
        self.mock_tar_open.assert_called_once_with(name=self.output_path, mode=DEFAULT_TAR_MODE)
        self.mock_tar_file.add.assert_called_once_with(self.temp_dir, arcname=DOCS_ARCHIVE_NAME)

    def test_generate_tarball_no_tmp_dir(self):
        """Test generating docs tarball when no temp dir can be created"""
        self.mock_temp_dir.return_value.__enter__.side_effect = OSError
        with self.assertRaises(BootPrepDocsError):
            generate_docs_tarball(self.schema_path, self.output_dir)

    def test_generate_tarball_os_error(self):
        """Test generating docs tarball when there is an OSError during creation"""
        self.mock_tar_file.add.side_effect = OSError
        with self.assertRaises(BootPrepDocsError):
            generate_docs_tarball(self.schema_path, self.output_dir)


class TestDisplaySchema(unittest.TestCase):
    """Tests for the display_schema() function"""
    def setUp(self):
        self.contents = b'schema file goes here'
        self.mock_run = patch('sat.cli.bootprep.documentation.subprocess.run').start()
        self.mock_getenv = patch('sat.cli.bootprep.documentation.os.getenv',
                                 return_value='').start()

    def tearDown(self):
        patch.stopall()

    def test_displaying_schema(self):
        """Test that schema is written to stdout when no pager set"""
        with patch('builtins.print') as mock_print:
            display_schema(self.contents)
            mock_print.assert_called_once_with(self.contents.decode('utf-8'))

    def test_displaying_schema_with_other_pager(self):
        """Test that schema is displayed in a non-default pager"""
        new_pager = '/usr/bin/some_other_pager --with --some --arguments'
        self.mock_getenv.return_value = new_pager
        display_schema(self.contents)
        self.mock_run.assert_called_once_with(shlex.split(new_pager), input=self.contents)

    def test_no_such_pager(self):
        """Test that an error is printed if the user-specified pager does not exist"""
        self.mock_getenv.return_value = '/usr/bin/some_pager_that_doesnt_exist'
        self.mock_run.side_effect = FileNotFoundError
        with self.assertRaises(BootPrepDocsError):
            display_schema(self.contents)
