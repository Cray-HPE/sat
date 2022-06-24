#
# MIT License
#
# (C) Copyright 2019-2020 Hewlett Packard Enterprise Development LP
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
Defines a decorator that creates a property that caches itself upon first access.
"""


class cached_property:
    """A decorator to create a read-only property that caches itself upon first access."""

    def __init__(self, func):
        """Create a cached_property that implements the descriptor protocol.

        Args:
            func: The function to decorate.
        """
        self.func = func

    def __get__(self, obj, cls):
        """Gets and caches the result of `self.func`.

        The result is cached in an attribute of the same name as the function
        but with a leading underscore.
        """

        if obj is None:
            return self

        cached_attr_name = '_{}'.format(self.func.__name__)
        if not hasattr(obj, cached_attr_name):
            setattr(obj, cached_attr_name, self.func(obj))
        return getattr(obj, cached_attr_name)
