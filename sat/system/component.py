"""
Class to define a generic component obtained from Hardware State Manager (HSM).

Copyright 2019 Cray Inc. All Rights Reserved.
"""
from collections import defaultdict
import logging

from inflect import engine

from sat.cached_property import cached_property
from sat.system.constants import MISSING_VALUE, EMPTY_VALUE
from sat.system.field import ComponentField
from sat.xname import XName

LOGGER = logging.getLogger(__name__)


class ComponentDataDict(dict):
    """A subclass of dict that holds raw data for a component.

    The differences between this and a regular dict are as follows:

    * If the value for a key is the empty string, it will instead return the
      value EMPTY_VALUE
    * If the key is missing, it will return the value MISSING_VALUE.
    """
    def __getitem__(self, key):
        try:
            val = super().__getitem__(key)
        except KeyError:
            return MISSING_VALUE
        if isinstance(val, str):
            stripped_val = val.strip()
            if not stripped_val:
                return EMPTY_VALUE
            else:
                return stripped_val
        elif isinstance(val, dict):
            # Keep the key access working the same way on dicts within this dict
            return ComponentDataDict(val)
        else:
            return val


class BaseComponent:
    """A base class for components in HSM inventory."""
    inflector = engine()

    # The value of the 'Type' field in HSM API output corresponding to a
    # component of this type.
    hsm_type = ''

    # The name of the component for reference in command options
    arg_name = ''

    # The pretty name of the component for output
    pretty_name = ''

    # The list of fields supported by the component. Subclasses can override or add.
    fields = [
        ComponentField('xname'),
        ComponentField('Manufacturer'),
        ComponentField('Model'),
        ComponentField('Part Number'),
        ComponentField('SKU'),
        ComponentField('Serial Number')
    ]

    def __init__(self, raw_data):
        """The raw data for this object as obtained from HSM.

        Args:
            raw_data (dict): Raw data obtained from HSM.
        """
        self.raw_data = raw_data
        # Subclasses can set this instance variable to a dict which maps from
        # child object type to an instance variable of type dict to hold the
        # child objects if they support children of certain types.
        self.children_by_type = {}
        # A cache to store values from children objects so that we don't need
        # to iterate over them multiple times.
        self._child_vals_cache = defaultdict(dict)

    @classmethod
    def plural_pretty_name(cls):
        """Gets the plural form of the pretty name.

        Returns:
            The plural form of the pretty_name class variable.
        """
        return cls.inflector.plural(cls.pretty_name)

    def add_child_object(self, child_object):
        """Add the given child object to this object's appropriate children dict.

        Args:
            child_object (sat.system.component.BaseComponent): The child object

        Returns:
            None
        """
        for child_type, child_dict in self.children_by_type.items():
            if isinstance(child_object, child_type):
                child_dict[child_object.xname] = child_object
                break
        else:
            LOGGER.warning("Received unknown object '%s' "
                           "to add as child of object '%s'.",
                           child_object, self)

    def get_child_vals(self, child_type, field_name):
        """Gets the values of the given `field_name` from the children.

        Args:
            child_type (type): The type of the children from which to get values
            field_name (str): The name of the field to get from children.

        Returns:
            A list of the values for the given field_name from all children.
        """
        if not self.children_by_type.get(child_type):
            return []

        if not self._child_vals_cache[child_type].get(field_name):
            child_vals = [getattr(child, field_name)
                          for child in self.children_by_type[child_type].values()]
            self._child_vals_cache[child_type][field_name] = child_vals
        return self._child_vals_cache[child_type][field_name]

    def get_unique_child_vals(self, child_type, field_name):
        """Gets the unique values of the given `field_name` from the children.

        Args:
            child_type (type): The type of the children from which to get values
            field_name (str): The name of the field to get from children.

        Returns:
            A set of unique values for the given field_name.
        """
        return set(self.get_child_vals(child_type, field_name))

    def get_unique_child_vals_str(self, child_type, field_name):
        """Gets the unique values of the given `field_name` from the children.

        Args:
            child_type (type): The type of the children from which to get values
            field_name (str): The name of the field to get from children.

        Returns:
            A comma-separate string of unique values for the given field_name
            or the EMPTY_VALUE string if there are no children of this type.
        """
        unique_child_vals = self.get_unique_child_vals(child_type, field_name)
        return EMPTY_VALUE if not unique_child_vals else ', '.join(unique_child_vals)

    @cached_property
    def type(self):
        """str: The HSM type of the component."""
        return self.raw_data['Type']

    @cached_property
    def xname(self):
        """sat.xname.XName: The xname of the component."""
        return XName(self.raw_data['ID'])

    @cached_property
    def fru_info(self):
        """ComponentDataDict: The FRU info stored in the raw data.
        """
        fru_info_key = '{}FRUInfo'.format(self.type)
        return ComponentDataDict(self.raw_data['PopulatedFRU'][fru_info_key])

    @cached_property
    def location_info(self):
        """dict: The location info stored in the raw data."""
        location_info_key = '{}LocationInfo'.format(self.type)
        return self.raw_data[location_info_key]

    @cached_property
    def manufacturer(self):
        """str: The manufacturer of the component."""
        return self.fru_info['Manufacturer']

    @cached_property
    def model(self):
        """str: The model of the component."""
        return self.fru_info['Model']

    @cached_property
    def part_number(self):
        """str: The part number of the component."""
        return self.fru_info['PartNumber']

    @cached_property
    def sku(self):
        """str: The SKU of the component."""
        return self.fru_info['SKU']

    @cached_property
    def serial_number(self):
        """str: The serial number of the component."""
        return self.fru_info['SerialNumber']

    @classmethod
    def get_summary_fields(cls, filters=None):
        """Gets a filtered list of fields to use to summarize the component.

        Args:
            filters (Iterable): The list of field names to filter the
                summarizable fields by.

        Returns:
            A list of ComponentField objects that should be used to summarize
            the component.
        """
        return cls.filter_fields('summarizable', filters)

    @classmethod
    def get_listable_fields(cls, filters=None):
        """Gets a filtered list of fields to use in a listing of the component.

        Args:
            filters (Iterable): The list of field names to filter the listable
                fields by.

        Returns:
            A list of ComponentField objects that should be used in a listing
            of the component.
        """
        return cls.filter_fields('listable', filters)

    @classmethod
    def filter_fields(cls, field_type, filters):
        """Gets a filtered list of fields of the given type.

        Args:
            field_type (str): The name of a bool attribute on a ComponentField
                to filter fields on. Currently this is just 'summarizable' or
                'listable'.
            filters (Iterable): The list of field names to filter the listable
                fields by.

        Returns:
            A list of ComponentField objects matching the given `field_type` and
            `filters`.
        """
        fields = [field for field in cls.fields if getattr(field, field_type)]

        if not filters:
            return fields

        filtered_fields = []
        seen_fields = set()
        for filter_str in filters:
            matching_fields = [field for field in fields
                               if field.matches(filter_str)]
            if not matching_fields:
                LOGGER.warning("Given field filter '%s' does not match any "
                               "%s fields of '%s' component type. Ignoring.",
                               filter_str, field_type, cls.pretty_name)

            for matching_field in matching_fields:
                if matching_field not in seen_fields:
                    seen_fields.add(matching_field)
                    filtered_fields.append(matching_field)

        if not filtered_fields:
            LOGGER.warning("No fields matched given filters. Defaulting to "
                           "displaying all fields.")
            return fields

        return filtered_fields

    def get_dict(self, fields):
        """Gets a dict representation of this component with the given fields.

        Args:
            fields (Iterable): An Iterable of ComponentField objects to get the
                values of from this component.

        Returns:
            A dict mapping from the given field to the values of those fields
            for this component.
        """
        return {field.canonical_name: getattr(self, field.property_name)
                for field in fields}

    def get_table_row(self, fields):
        """Gets a table row for this component.

        Args:
            fields (Iterable): An Iterable of ComponentField objects to get the
                values of from this component.

        Returns:
            A list of the requested fields from this object.
        """
        return [getattr(self, field.property_name) for field in fields]

    def __str__(self):
        """Just use the xname as the string representation of a component."""
        return str(self.xname)
