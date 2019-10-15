"""
Defines a decorator that creates a property that caches itself upon first access.

Copyright 2019 Cray Inc. All Rights Reserved.
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
