"""
Defines base classes for objects defined in the input file.

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
from abc import ABC, abstractmethod
from collections import Counter
import logging

from inflect import engine

from sat.cached_property import cached_property
from sat.cli.bootprep.errors import InputItemCreateError, InputItemValidateError, UserAbortException
from sat.util import pester_choices

LOGGER = logging.getLogger(__name__)


class Validatable:
    """A base class for something that can be validated"""

    VAL_METHOD_ATTR = 'is_validation_method'

    @staticmethod
    def validation_method(method):
        """Mark a method as a validation method.

        Args:
            method: the method on which to set the attribute
                Validatable.VAL_METHOD_ATTR to True
        """
        setattr(method, Validatable.VAL_METHOD_ATTR, True)
        return method

    def attr_is_validation_method(self, attr_name):
        """Returns whether the method is a validation method of this class

        Checks whether the given `attr` is a callable and whether it has the
        Validatable.VAL_METHOD_ATTR attribute set to True. Attributes which
        exist on the class object as a property or cached_property are ignored
        to avoid any side effects (e.g. raised Exceptions) that may result from
        accessing them.

        Args:
            attr_name (str): the name of the attribute

        Returns:
            bool: True if it is a validation method, False otherwise.
        """
        # Avoid calling the getter of property or cachedproperty
        if isinstance(getattr(type(self), attr_name, None), (property, cached_property)):
            return False

        attr = getattr(self, attr_name)
        return callable(attr) and getattr(attr, self.VAL_METHOD_ATTR, False)

    @property
    def validation_methods(self):
        """list of callable: all the methods tagged as validation methods"""
        return [getattr(self, attr_name) for attr_name in dir(self)
                if self.attr_is_validation_method(attr_name)]

    def validate(self, **kwargs):
        """Validate this object by calling all of its validation methods.

        For each validation method that fails, an error message is logged, and
        at the end a new `InputItemValidateError` is raised.

        Raises:
            InputItemValidateError: if any validation methods fail, i.e. raise
                an InputItemValidateError
        """
        valid = True
        for val_method in self.validation_methods:
            try:
                val_method(**kwargs)
            except InputItemValidateError as err:
                LOGGER.error(str(err))
                valid = False

        if not valid:
            raise InputItemValidateError(f'The {self} is not valid. See errors above.')


class BaseInputItem(Validatable, ABC):
    """Abstract base class for items defined in the input file.

    Attributes:
        data (dict): the data defining the item from the input file, already
            validated by the bootprep schema
        instance (sat.cli.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
        items_to_delete (list): the items that should be overwritten by this
            item
    """
    # The description for the input item, to be overridden by each subclass
    description = 'base input item'

    def __init__(self, data, instance, **kwargs):
        """Create a new BaseInputItem.

        Args:
            data (dict): the data defining the item from the input file, already
                validated by the bootprep schema
            instance (sat.cli.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
        """
        self.data = data
        self.instance = instance
        self.items_to_delete = []

    @property
    def name(self):
        """str: the name of this input item that is to be created"""
        # The 'name' property is required by the schema for all types of input
        # items that inherit from BaseInputItem.
        return self.data['name']

    def __str__(self):
        return f'{self.description} named {self.name}'

    def add_items_to_delete(self, delete_list):
        """Add a list of items that should be deleted after this item is created.

        This adds the items from `delete_list` to `self.items_to_delete`

        Args:
            delete_list (list): the list of items to delete

        Returns:
            None
        """
        self.items_to_delete.extend(delete_list)

    def add_item_to_delete(self, delete_item):
        """Add a single item that should be deleted after this item is created.

        This adds the item, `delete_item` to `self.items_to_delete`

        Args:
            delete_item: the item to delete

        Returns:
            None
        """
        self.items_to_delete.append(delete_item)

    def delete_overwritten_items(self):
        """Delete the items that are supposed to be overwritten by this item.

        The default implementation does nothing.
        """
        pass

    @abstractmethod
    def create(self):
        """Create the item.

        Raises:
            InputItemCreateError: if there is a failure to create the item
        """
        pass


class BaseInputItemCollection(ABC, Validatable):
    """An abstract base class for a collection of items defined in the input file.

    Attributes:
        item_class: the class to use to create each item from the raw input data
        items (list of BaseInputItem): the input items
        instance (sat.cli.bootprep.input.InputInstance): a reference to the
            full instance loaded from the config file
        items_to_create (list of BaseInputItem): the input items
            that should be created
        skipped_items (list of BaseInputItem): the input items that
            should be skipped
    """
    inflector = engine()
    item_class = BaseInputItem

    def __init__(self, items_data, instance, **kwargs):
        """Create a new BaseInputItemCollection.

        Args:
            items_data (list of dict): list of data defining items in the
                input file, already validated by the schema
            instance (sat.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
            **kwargs: additional keyword arguments which are passed through to
                the constructor of the class defined in the class attribute
                `item_class`
        """
        self.items = [self.item_class(item_data, instance, **kwargs) for item_data in items_data]
        self.instance = instance
        self.items_to_create = []
        self.skipped_items = []

    def __str__(self):
        return f'collection of {self.inflector.plural(self.item_class.description)}'

    def item_count_string(self, count):
        """Get a string describing the given `count` of items.

        Args:
            count (int): the number of items to get a descriptor for
        """
        return f'{count} {self.inflector.plural(self.item_class.description, count)}'

    @Validatable.validation_method
    def validate_items(self, **kwargs):
        """Validate all items within this collection.

        If an item's `validate` method raises an `InputItemValidateError`, an
        error will be logged, and once all items are validated, this will raise
        a new `InputItemValidateError`.

        Raises:
            InputItemValidateError: if any item is invalid
        """
        valid = True
        for item in self.items_to_create:
            try:
                item.validate(**kwargs)
            except InputItemValidateError as err:
                LOGGER.error(str(err))
                valid = False

        if not valid:
            raise InputItemValidateError(f'One or more items is not valid in {self}')

    @Validatable.validation_method
    def validate_unique_names(self, **_):
        """Validate that all items in collection have unique names.

        Raises:
            InputItemValidateError: if there are any items with the same name
        """
        counts_by_name = Counter(item.name for item in self.items)
        non_unique_names = [name for name, count in counts_by_name.items() if count > 1]
        if non_unique_names:
            raise InputItemValidateError(
                f'Names of {self.inflector.plural(self.item_class.description)} '
                f'must be unique. Non-unique {self.inflector.plural("name", len(non_unique_names))}: '
                f'{", ".join(non_unique_names)}'
            )

    def handle_existing_items(self, overwrite_all, skip_all, dry_run):
        """Handle any existing items that have the same name as this item.

        Sets `self.skipped_items` to the list of items that should be skipped
        and `self.items_to_create` to the list of items that should be created.

        Args:
            overwrite_all (bool): if True, all existing items should be
                overwritten
            skip_all (bool): if True, all existing items should be skipped
            dry_run (bool): whether this is a dry-run or not

        Returns:
            None

        Raises:
            InputItemCreateError: if there is a failure to get existing items
            UserAbortException: if the user chooses to abort at any point
        """
        existing_items_by_name = self.get_existing_items_by_name()

        existing_input_items = [input_item for input_item in self.items
                                if input_item.name in existing_items_by_name]
        new_input_items = [input_item for input_item in self.items
                           if input_item.name not in existing_items_by_name]
        self.items_to_create = new_input_items

        if not existing_input_items:
            LOGGER.debug(f'Found no conflicting items in {self}')
            return

        verb = ('will be', 'would be')[dry_run]

        for item in existing_input_items:
            conflicting_items = existing_items_by_name.get(item.name, [])
            count = len(conflicting_items)
            conflict_msg = (f'{count} {self.inflector.plural(self.item_class.description, count)} '
                            f'already {self.inflector.plural_verb("exists", count)} with the name {item.name}')

            overwrite = overwrite_all
            skip = skip_all

            if not overwrite and not skip:
                choices = ('skip', 'overwrite', 'abort')
                answer = pester_choices(f'{conflict_msg}. Would you like to '
                                        f'{self.inflector.join(choices, conj="or")}?', choices)
                if answer == 'abort':
                    raise UserAbortException()

                skip = answer == 'skip'
                overwrite = answer == 'overwrite'

            msg_template = f'{conflict_msg} and {verb} %(action)s.'

            if overwrite:
                self.items_to_create.append(item)
                item.add_items_to_delete(conflicting_items)
                LOGGER.info(msg_template, {'action': 'overwritten'})
            elif skip:
                self.skipped_items.append(item)
                LOGGER.info(msg_template, {'action': 'skipped'})

    @abstractmethod
    def get_existing_items_by_name(self):
        """Get the list of existing items by name.

        Returns:
            dict: a dictionary mapping from the names of the existing items
                to a list of the API data for the item(s) with those names

        Raises:
            InputItemCreateError: if there is a failure to get existing items
        """
        pass

    def create_items(self):
        """Create the items in this collection of items.

        Raises:
            InputItemCreateError: if there is a failure to create one or more items
        """
        if not self.items_to_create:
            LOGGER.info(f'Nothing to create in {self}')
            return

        LOGGER.info(f'Creating {self.item_count_string(len(self.items_to_create))}')

        failed_items = []
        for item in self.items_to_create:
            try:
                item.create()
            except InputItemCreateError as err:
                failed_items.append(item)
                LOGGER.error(f'Failed to create {item}: {err}')

        if failed_items:
            raise InputItemCreateError(
                f'Failed to create {self.item_count_string(len(failed_items))}'
            )
