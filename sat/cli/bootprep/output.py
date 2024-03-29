#
# MIT License
#
# (C) Copyright 2022-2023 Hewlett Packard Enterprise Development LP
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
Implements tooling for writing various bootprep-related output to disk.
"""

import json
import logging
import os
import re


DEFAULT_JSON_FORMAT_PARAMS = {'indent': 4}
LOGGER = logging.getLogger(__name__)


def ensure_output_directory(args):
    """Ensure the output directory exists if necessary.

    Args:
        args: The argparse.Namespace object containing the parsed arguments
            passed to this subcommand.

    Returns:
        None

    Raises:
        SystemExit: If a fatal error is encountered.
    """
    must_create_output_dir = (
        (args.action == 'run' and args.save_files
         or args.action in ('generate-docs', 'generate-example'))
        and args.output_dir != '.'
    )
    if must_create_output_dir:
        try:
            os.makedirs(args.output_dir, exist_ok=True)
        except OSError as err:
            LOGGER.error(f'Unable to ensure output directory {args.output_dir} '
                         f'exists: {err}')
            raise SystemExit(1)


class RequestDumper:
    """A helper class which dumps API payloads"""
    def __init__(self, save_files, output_dir, json_params=None):
        """Construct a new RequestDumper.

        If output_dir is specified in the args namespace, it is assumed that
        the directory exists and is writable.

        Args:
            save_files (bool): whether this dumper should save files at all
            output_dir (str): the directory in which files should be saved
            json_params (dict): kwargs to be passed to json.dump() to configure
                JSON dump formatting.
        """
        if json_params is None:
            json_params = DEFAULT_JSON_FORMAT_PARAMS

        self.json_params = json_params

        self.save_files = save_files
        self.output_dir = output_dir

    @staticmethod
    def canonicalize(name):
        """Canonicalize the given name by converting to lowercase and replacing chars.

        Removes parentheses. Removes leading and trailing whitespace, and
        replaces remaining whitespace and forward slashes with '-'.

        Args:
            name (str): some given name of an item.

        Returns:
            The canonical form of the given name.
        """
        return re.sub(r'[\s/]+', '-', re.sub(r'[()]', '', name.strip().lower()))

    def get_filename_for_request(self, item_type, item_name):
        """Helper function to get the full filename to dump the request body to.

        Args:
            item_type (str): the type of item being dumped
            item_name (str): the name of the item related to this request

        Returns:
            str: the full filename to write the request to
        """
        canonical_type = self.canonicalize(item_type)
        canonical_name = self.canonicalize(item_name)
        return os.path.join(self.output_dir, f'{canonical_type}-{canonical_name}.json')

    def write_request_body(self, item_type, item_name, request_body):
        """Write a JSON-formatted request body to a file.

        If save_files is set to False in the constructor, this method does
        nothing.

        Args:
            item_type (str): the type of the item associated with the request
                being dumps. (For instance, "CFS configuration")
            item_name (str): the name of the item associated with the request
                being dumped. (For instance, a CFS configuration name.)
            request_body (dict): payload to be used as the request body.
        """
        if not self.save_files:
            return

        output_path = self.get_filename_for_request(item_type, item_name)
        LOGGER.info(f'Saving {item_type} request body to {output_path}')
        try:
            with open(output_path, 'w') as f:
                json.dump(request_body, f, **self.json_params)
        except OSError as err:
            LOGGER.warning('Failed to write %s request body to %s: %s',
                           item_type, output_path, err)
