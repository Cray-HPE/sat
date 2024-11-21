#
# MIT License
#
# (C) Copyright 2024 Hewlett Packard Enterprise Development LP
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
Class for representing a semver version
"""
from semver import Version


class LooseVersion:
    """A LooseVersion representing a version that may be semver or may not.

    This class is used to compare versions that may or may not comply with the
    semver format. If the version does not comply with the semver format, then
    the MAX_VERSION is used as the comparison version, which results in the
    version being considered greater than any other version.

    Args:
        version_str (str): The string representation of the version.

    Attributes:
        version_str (str): The string representation of the version.
        comparison_version (semver.version.Version): The semver.version.Version
            object of either the version_str or the MAX_VERSION if semver fails to
            parse the version
    """

    MAX_VERSION = "99999999999.99999999999.99999999999"

    def __init__(self, version_str):
        """Creates a new LooseVersion object from the given product_version string.

        Args:
            version_str (str): The string representation of the version.
        """
        self.version_str = version_str
        self.comparison_version = self.parse_version(version_str)

    def __str__(self):
        return f'{self.version_str}'

    def __repr__(self):
        return f"{self.__class__.__name__}('{self.version_str}')"

    def __lt__(self, other):
        return self.comparison_version < other.comparison_version

    def __le__(self, other):
        return self.comparison_version <= other.comparison_version

    def __eq__(self, other):
        return (isinstance(self, type(other)) and
                self.comparison_version == other.comparison_version)

    def __gt__(self, other):
        return self.comparison_version > other.comparison_version

    def __ge__(self, other):
        return self.comparison_version >= other.comparison_version

    def parse_version(self, version_str):
        """Parse the version string into a semver.version.Version object if possible.

        Args:
            version_str (str): The string representation of the version.

        Returns:
            semver.version.Version: The semver.version.Version object of either
                the version_str or the MAX_VERSION if semver fails to parse the
                version
        """

        try:
            parsed_version = Version.parse(version_str)
        except ValueError:
            parsed_version = Version.parse(self.MAX_VERSION)

        return parsed_version
