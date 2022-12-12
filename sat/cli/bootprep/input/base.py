#
# MIT License
#
# (C) Copyright 2021-2023 Hewlett Packard Enterprise Development LP
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
Defines base classes for objects defined in the input file.
"""
from abc import ABC, abstractmethod
from collections import Counter
import functools
import logging

from inflect import engine
from jinja2 import TemplateError
from jinja2.sandbox import SecurityError

from sat.cached_property import cached_property
from sat.cli.bootprep.errors import InputItemCreateError, InputItemValidateError, UserAbortException
from sat.util import pester_choices

LOGGER = logging.getLogger(__name__)
inflector = engine()


def provides_context(context_var=None):
    """Get decorator for instance methods which provide Jinja2 context.

    This should be used to decorate instance methods which provide additional
    context which should be used when rendering Jinja2 templates with the
    jinja_rendered decorator defined below.

    Note that the context provided by the instance method decorated with this
    decorator will not be available until that method is called.

    This decorator requires that the instance has the following attribute:

        jinja_context (dict): additional context to use when rendering the
            result of the method as a Jinja2 template. Defaults to the empty
            dict if not set.
    """
    def decorator(func):
        @functools.wraps(func)
        def wrapper(self, *args, **kwargs):
            result = func(self, *args, **kwargs)
            self.jinja_context[context_var or func.__name__] = result
            return result

        return wrapper

    return decorator


def jinja_rendered(func):
    """Decorator for instance methods which return Jinja2 templates.

    This should be used to decorate instance methods which return content from
    the InputInstance that supports rendering as a Jinja2 template. If the
    `func` returns `None`, this wrapper will as well.

    This decorator requires the instance has the following attribute:

        jinja_env (jinja2.Environment): the Jinja2 environment to use to get
            Template objects to be rendered. Variables to use as context are
            expected to already be set in the `globals` attribute.

    This decorator uses the following additional optional attributes of the instance:

        create_error_cls: the exception class that should be raised if there is
            an issue rendering the template. Defaults to InputItemValidateError
            if not set.

        jinja_context (dict): additional context to use when rendering the
            result of the method as a Jinja2 template. Defaults to the empty
            dict if not set.
    """
    @functools.wraps(func)
    def wrapper(self, *args, **kwargs):
        # First call the wrapped method and get its result
        unrendered_result = func(self, *args, **kwargs)

        # If value not specified in input file, the `func` may return `None`
        if unrendered_result is None:
            return unrendered_result

        # Default to InputItemCreateError if no error class is specified
        error_cls = getattr(self, 'create_error_cls', InputItemValidateError)

        # Default to no additional context if not set
        context = getattr(self, 'jinja_context', {})

        try:
            return self.jinja_env.from_string(unrendered_result).render(context)
        except SecurityError as err:
            raise error_cls(f'Jinja2 template {unrendered_result} for value '
                            f'{func.__name__} tried to access unsafe attributes.') from err
        except TemplateError as err:
            raise error_cls(f'Failed to render Jinja2 template {unrendered_result} '
                            f'for value {func.__name__}: {err}') from err

    return wrapper


class Validatable:
    """A base class for something that can be validated"""

    VAL_METHOD_ATTR = 'is_validation_method'
    VAL_METHOD_ORDINAL_ATTR = 'validation_method_ordinal'
    # The default value for a validation method's ordinal value
    DEFAULT_ORDINAL = 1

    @staticmethod
    def validation_method(ordinal=DEFAULT_ORDINAL):
        """Return a decorator to mark a method as a validation method.

        Args:
            ordinal (int): the priority of the validation method. Validation
                methods will be called in priority order
        """
        def decorator(method):
            setattr(method, Validatable.VAL_METHOD_ATTR, True)
            setattr(method, Validatable.VAL_METHOD_ORDINAL_ATTR, ordinal)
            return method

        return decorator

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
        """list of callable: all the methods tagged as validation methods in ordinal order"""
        return sorted(
            [getattr(self, attr_name) for attr_name in dir(self)
             if self.attr_is_validation_method(attr_name)],
            key=lambda m: getattr(m, self.VAL_METHOD_ORDINAL_ATTR, self.DEFAULT_ORDINAL)
        )

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

    create_error_cls = InputItemValidateError

    def __init__(self, data, instance, index, jinja_env, **_):
        """Create a new BaseInputItem.

        Args:
            data (dict): the data defining the item from the input file, already
                validated by the bootprep schema
            instance (sat.cli.bootprep.input.instance.InputInstance): a reference
                to the full instance loaded from the input file
            index (int): the index of the item in the collection in the instance
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
        """
        self.data = data
        self.instance = instance
        self.index = index
        self.jinja_env = jinja_env
        self.items_to_delete = []

    @property
    @jinja_rendered
    def name(self):
        """str: the rendered name of this input item that is to be created"""
        # The 'name' property is required by the schema for all types of input
        # items that inherit from BaseInputItem.
        return self.data['name']

    def __str__(self):
        # Since the name can be rendered, and when unrendered, it does not need
        # to be unique, just refer to this item by its index in the instance.
        return f'{self.description} at index {self.index}'

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
    def get_create_item_data(self):
        """Get the data needed to create the item.

        Raises:
            InputItemCreateError: if there is a failure to get the data
        """
        pass

    @abstractmethod
    def create(self, payload):
        """Create the item.

        Args:
            payload (dict): the data to be passed to the API to create the item

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
    item_class = BaseInputItem

    def __init__(self, items_data, instance, jinja_env, request_dumper, **kwargs):
        """Create a new BaseInputItemCollection.

        Args:
            items_data (list of dict): list of data defining items in the
                input file, already validated by the schema
            instance (sat.bootprep.input.InputInstance): a reference to the
                full instance loaded from the config file
            jinja_env (jinja2.Environment): the Jinja2 environment in which
                fields supporting Jinja2 templating should be rendered.
            request_dumper (sat.cli.bootprep.output.RequestDumper): the dumper
                for dumping request data to files.
            **kwargs: additional keyword arguments which are passed through to
                the constructor of the class defined in the class attribute
                `item_class`
        """
        constructor = self.item_class
        if hasattr(self.item_class, 'get_item'):
            constructor = self.item_class.get_item
        self.items = [constructor(item_data, instance, index, jinja_env, **kwargs)
                      for index, item_data in enumerate(items_data)]
        self.instance = instance
        self.request_dumper = request_dumper
        self.items_to_create = []
        self.skipped_items = []

    def __str__(self):
        return f'collection of {inflector.plural(self.item_class.description)}'

    def item_count_string(self, count):
        """Get a string describing the given `count` of items.

        Args:
            count (int): the number of items to get a descriptor for
        """
        return f'{count} {inflector.plural(self.item_class.description, count)}'

    # Item validation should occur before name validation because validating an
    # item ensures its name can be rendered.
    @Validatable.validation_method(ordinal=0)
    def validate_items(self, **kwargs):
        """Validate all items within this collection.

        If an item's `validate` method raises an `InputItemValidateError`, an
        error will be logged, and once all items are validated, this will raise
        a new `InputItemValidateError`.

        Raises:
            InputItemValidateError: if any item is invalid
        """
        valid = True
        for item in self.items:
            try:
                item.validate(**kwargs)
            except InputItemValidateError as err:
                LOGGER.error(str(err))
                valid = False

        if not valid:
            raise InputItemValidateError(f'One or more items is not valid in {self}')

    # Validation of unique names must occur after item validation because item
    # validation will render names using Jinja2 templates.
    @Validatable.validation_method(ordinal=1)
    def validate_unique_names(self, **_):
        """Validate that all items in collection have unique names.

        Raises:
            InputItemValidateError: if there are any items with the same name
        """
        counts_by_name = Counter()

        failed_name_renders = 0
        for item in self.items:
            try:
                counts_by_name[item.name] += 1
            except self.item_class.create_error_cls as err:
                failed_name_renders += 1
                LOGGER.error(f'Failed to render name of {item}: {err}')

        if failed_name_renders:
            raise InputItemValidateError(
                f'Failed to render name of {failed_name_renders} '
                f'{inflector.plural(self.item_class.description, failed_name_renders)}'
            )

        non_unique_names = [name for name, count in counts_by_name.items() if count > 1]
        if non_unique_names:
            raise InputItemValidateError(
                f'Names of {inflector.plural(self.item_class.description)} '
                f'must be unique. Non-unique {inflector.plural("name", len(non_unique_names))}: '
                f'{", ".join(non_unique_names)}'
            )

    def handle_existing_items(self, overwrite_all, skip_all):
        """Handle any existing items that have the same name as this item.

        Sets `self.skipped_items` to the list of items that should be skipped
        and `self.items_to_create` to the list of items that should be created.

        Args:
            overwrite_all (bool): if True, all existing items should be
                overwritten
            skip_all (bool): if True, all existing items should be skipped

        Returns:
            None

        Raises:
            InputItemCreateError: if there is a failure to get existing items
            UserAbortException: if the user chooses to abort at any point
        """
        if not self.items:
            return

        existing_items_by_name = self.get_existing_items_by_name()

        existing_input_items = [input_item for input_item in self.items
                                if input_item.name in existing_items_by_name]
        new_input_items = [input_item for input_item in self.items
                           if input_item.name not in existing_items_by_name]
        self.items_to_create = new_input_items

        if not existing_input_items:
            LOGGER.debug(f'Found no conflicting items in {self}')
            return

        verb = ('will be', 'would be')[self.instance.dry_run]

        for item in existing_input_items:
            conflicting_items = existing_items_by_name.get(item.name, [])
            count = len(conflicting_items)
            conflict_msg = (f'{count} {inflector.plural(self.item_class.description, count)} '
                            f'already {inflector.plural_verb("exists", count)} with the name {item.name}')

            overwrite = overwrite_all
            skip = skip_all

            if not overwrite and not skip:
                choices = ('skip', 'overwrite', 'abort')
                answer = pester_choices(f'{conflict_msg}. Would you like to '
                                        f'{inflector.join(choices, conj="or")}?', choices)
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

        create_verb = ('Creating', 'Would create')[self.instance.dry_run]

        LOGGER.info(f'{create_verb} {self.item_count_string(len(self.items_to_create))}')

        failed_items = []
        for item in self.items_to_create:
            # The 'name' attribute is rendered during validation, so it's safe to use here
            item_description = f'{item} with name={item.name}'
            LOGGER.info(f'{create_verb} {item_description}')
            try:
                item_data = item.get_create_item_data()
            except InputItemCreateError as err:
                failed_items.append(item)
                LOGGER.error(f'Failed to create {item_description}: {err}')
                continue
            self.request_dumper.write_request_body(type(item).description, item.name, item_data)

            if not self.instance.dry_run:
                try:
                    item.create(item_data)
                except InputItemCreateError as err:
                    failed_items.append(item)
                    LOGGER.error(f'Failed to create {item_description}: {err}')
                else:
                    LOGGER.info(f'Successfully created {item_description}')

        if failed_items:
            raise InputItemCreateError(
                f'Failed to create {self.item_count_string(len(failed_items))}'
            )
