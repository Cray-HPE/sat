#
# MIT License
#
# (C) Copyright 2021-2022 Hewlett Packard Enterprise Development LP
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
Constant values used in sat.cli.bootprep
"""
import os

DEFAULT_PUBLIC_KEY_FILE = '~/.ssh/id_rsa.pub'
DEFAULT_PUBLIC_KEY_FILE_EXPANDED = os.path.expanduser(DEFAULT_PUBLIC_KEY_FILE)

# Name of the top-level directory within the docs tarball generated by 'sat bootprep generate-docs'
DOCS_ARCHIVE_NAME = 'bootprep-schema-docs'
# Name of archive generated by 'sat bootprep generate-docs'
DOCS_ARCHIVE_FILE_NAME = f'{DOCS_ARCHIVE_NAME}.tar.gz'

# Example file name generated by 'sat bootprep generate-example'
EXAMPLE_FILE_NAME = 'example-bootprep-input.yaml'

# Special value used to indicate the latest version (e.g. of a product or the recipe)
LATEST_VERSION_VALUE = 'latest'
