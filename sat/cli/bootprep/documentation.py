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
Functions to generate and display documentation for the bootprep schema.
"""

import contextlib
import logging
import os
import shlex
import subprocess
import sys
import tarfile
import tempfile

from json_schema_for_humans.generate import generate_from_filename

from sat.cli.bootprep.constants import DOCS_ARCHIVE_FILE_NAME, DOCS_ARCHIVE_NAME
from sat.cli.bootprep.errors import BootPrepDocsError


LOGGER = logging.getLogger(__name__)
DEFAULT_HTML_INDEX = 'index.html'
DEFAULT_TAR_MODE = 'w:gz'  # Writable archive with transparent gzip


@contextlib.contextmanager
def silence():
    """Redirect stdout/stderr to /dev/null in the context.

    Args:
        None.

    Returns:
        None.
    """
    with open('/dev/null', 'w') as dev_null:
        stdout = sys.stdout
        stderr = sys.stderr

        try:
            sys.stdout = sys.stderr = dev_null
            yield
        finally:
            sys.stdout = stdout
            sys.stderr = stderr


@contextlib.contextmanager
def cwd(path):
    """Change directories to a given path in the context.

    Args:
        path (str): the path to change directories to.

    Raises:
        OSError: if the path does not exist or there are permissions issues.
    """
    currdir = os.getcwd()
    try:
        os.chdir(path)
        yield
    finally:
        os.chdir(currdir)


def resource_absolute_path(resource_relative_path):
    """Get the absolute path to a resource in the SAT package.

    Args:
        resource_relative_path (str): the relative path to the resource from the
            sat package root on the filesystem.

    Returns:
        str: the absolute path on the filesystem of the file referenced by the
            relative path
    """
    from sat import __file__ as sat_toplevel_package_path
    sat_root = os.path.dirname(sat_toplevel_package_path)
    return os.path.join(sat_root, resource_relative_path)


def generate_docs_tarball(schema_path, output_dir):
    """Generate documentation and write to a tarball.

    Args:
        schema_path (str): the path to the schema file from which to generate
            documentation.
        output_dir (path-like object): the path to the directory in which the documentation
            tarball should be created.

    Returns:
        None.
    """
    try:
        with tempfile.TemporaryDirectory() as tempdir:
            with cwd(tempdir), silence():
                docs_output_path = os.path.join(tempdir, DEFAULT_HTML_INDEX)
                generate_from_filename(schema_path, docs_output_path)

            tarball_output_path = os.path.join(output_dir, DOCS_ARCHIVE_FILE_NAME)
            with tarfile.open(name=tarball_output_path, mode=DEFAULT_TAR_MODE) as output_tar:
                output_tar.add(tempdir, arcname=DOCS_ARCHIVE_NAME)
    except OSError as err:
        raise BootPrepDocsError(f'Could not create documentation tarball: {err}') from err

    LOGGER.info('Wrote input schema documentation to %s', tarball_output_path)


def display_schema(schema_contents):
    """Open schema file in pager.

    Args:
        schema_contents (bytes): the binary contents of the schema file.

    Returns:
        None.

    Raises:
        BootPrepDocsError: if the executable specified by PAGER does not exist.
    """
    pager = os.getenv('SAT_PAGER', '')
    pager_argv = shlex.split(pager)

    if pager and pager_argv:
        try:
            subprocess.run(pager_argv, input=schema_contents)
        except FileNotFoundError:
            raise BootPrepDocsError(f'No executable "{pager_argv[0]}" found.')
    else:
        print(schema_contents.decode('utf-8'))
