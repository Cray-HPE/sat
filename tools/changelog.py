#!/usr/bin/env python3
#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
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
# Extract the latest version number from a CHANGLOG.md file that follows the
# format proposed by the "Keep a Changelog" project.

import argparse
import logging
import re
import sys

VERSION_HEADER_RE = re.compile(
    r'^## \[(?P<version>\d+\.\d+\.\d+)\]\s-\s(?P<date>\d{4}-\d{2}-\d{2})$'
)


def create_parser():
    """Creates the ArgumentParser for this program.

    Returns:
        The argparse.ArgumentParser object to parse arguments for this script.
    """
    parser = argparse.ArgumentParser(
        description='Extract the latest version number from a CHANGELOG.md'
    )

    parser.add_argument(
        'changelog_file',
        help='The path to the CHANGELOG.md file in the format described by '
             '"Keep a Changelog"'
    )

    return parser


def get_version_from_line(line):
    """Gets the version from a line if it's a version line.

    Args:
        line (str): The line to attempt to extract the version from

    Returns:
        A tuple of the version number string and date string if the line is a
        version header line, otherwise None.
    """
    match = VERSION_HEADER_RE.match(line)
    if match:
        return match.group('version'), match.group('date')
    return None


def get_latest_version_from_file(file_path):
    """Gets the latest version from a CHANGELOG.md file.

    Args:
        file_path(str): The file path to open and parse.

    Returns:
        The latest (i.e. first) version number in the changelog file or None
        if one isn't found.
    """
    with open(file_path, 'r') as f:
        lines = f.readlines()
        for line in lines:
            version_and_date = get_version_from_line(line)
            if version_and_date:
                return version_and_date[0]

        logging.error("No latest version number found in changelog '%s'",
                      parsed.changelog_file)


if __name__ == '__main__':

    parser = create_parser()
    parsed = parser.parse_args()

    try:
        latest_version = get_latest_version_from_file(parsed.changelog_file)
        if latest_version:
            print(latest_version)
        else:
            sys.exit(1)
    except IOError as err:
        logging.error("Failed to open changelog file '%s'",
                      parsed.changelog_file)
        sys.exit(1)
