"""
Unit tests for sat.system.component.

Copyright 2019 Cray Inc. All Rights Reserved.
"""
import logging
import unittest
from unittest import mock

from sat.system.component import BaseComponent, ComponentDataDict, LOGGER
from sat.constants import MISSING_VALUE, EMPTY_VALUE
from sat.system.field import ComponentField
from tests.common import ExtendedTestCase
from tests.system.component_data import DEFAULT_HSM_TYPE, DEFAULT_XNAME, DEFAULT_SERIAL_NUMBER, \
    DEFAULT_PART_NUMBER, DEFAULT_SKU, DEFAULT_MODEL, DEFAULT_MANUFACTURER, get_component_raw_data


class SampleComponent(BaseComponent):
    """A subclass of the BaseComponent to test the class."""
    hsm_type = 'Sample'
    arg_name = 'sample'
    pretty_name = 'Sample'
    default_show_xnames = True
    # Use default `fields` set up in BaseComponent

    def __init__(self, raw_data):
        """Set up self.children_by_type to support testing children."""
        super().__init__(raw_data)
        self.children = {}
        self.children_by_type = {
            ChildComponent: self.children
        }


class ChildComponent(BaseComponent):
    """A subclass of BaseComponent to use as children of the SampleComponent."""
    hsm_type = 'Child'
    arg_name = 'child'
    pretty_name = 'Child'
    # Use default `fields` set up in BaseComponent


class CustomFieldsComponent(BaseComponent):
    """A subclass of BaseComponent to test getting listable and summarizable fields."""
    hsm_type = 'Custom'
    arg_name = 'custom'
    pretty_name = 'Custom'
    fields = [
        ComponentField('xname'),
        ComponentField('Party Favors', summarizable=True),
        ComponentField('Manufacturer'),
        ComponentField('Model'),
        ComponentField('Part Number'),
        ComponentField('Woman of the Year', summarizable=True),
        ComponentField('SKU'),
        ComponentField('Serial Number'),
        ComponentField('Serial Podcast', summarizable=True)
    ]


class TestComponentDataDict(unittest.TestCase):
    """Test the ComponentDataDict class."""

    def setUp(self):
        """Set up a dictionary to use in all test cases."""
        self.original_dict = {
            'foo': 'bar',
            'baz': {
                'nested': 'eggs',
                'empty': ''
            },
            'top_empty': ''

        }
        self.cdd = ComponentDataDict(self.original_dict)

    def test_present_key(self):
        self.assertEqual(self.original_dict['foo'], self.cdd['foo'])

    def test_missing_key(self):
        self.assertEqual(MISSING_VALUE, self.cdd['missing'])

    def test_empty_value(self):
        self.assertEqual(EMPTY_VALUE, self.cdd['top_empty'])

    def test_nested_value(self):
        self.assertEqual(self.original_dict['baz']['nested'],
                         self.cdd['baz']['nested'])

    def test_nested_missing_value(self):
        self.assertEqual(MISSING_VALUE, self.cdd['baz']['missing'])

    def test_nested_empty_value(self):
        self.assertEqual(EMPTY_VALUE, self.cdd['baz']['empty'])


class TestBaseComponentClass(unittest.TestCase):
    """Test class methods on the BaseComponent class."""

    def test_plural_pretty_name(self):
        """Test the plural_pretty_name class method."""
        self.assertEqual(SampleComponent.plural_pretty_name(), "Samples")

    def test_get_listable_fields(self):
        """Test get_listable_fields without filters."""
        matching_fields = CustomFieldsComponent.get_listable_fields()
        self.assertEqual(matching_fields, CustomFieldsComponent.fields)

    def test_get_summarizable_fields(self):
        """Test get_summarizable_fields without filters."""
        matching_fields = CustomFieldsComponent.get_summary_fields()
        expected_fields = [CustomFieldsComponent.fields[1],
                           CustomFieldsComponent.fields[5],
                           CustomFieldsComponent.fields[8]]
        self.assertEqual(matching_fields, expected_fields)

    def test_get_listable_fields_with_filter(self):
        """Test get_listable_fields with a filter matching only one field."""
        matching_fields = CustomFieldsComponent.get_listable_fields(['model'])
        self.assertEqual(matching_fields, [ComponentField('Model')])

    def test_get_listable_fields_with_multiple_filters(self):
        """Test get_listable_fields with filters matching two fields."""
        matching_fields = CustomFieldsComponent.get_listable_fields(['manufacture',
                                                                     'woman of the year'])
        expected_fields = [CustomFieldsComponent.fields[2],
                           CustomFieldsComponent.fields[5]]
        print(matching_fields)
        print(expected_fields)
        self.assertEqual(matching_fields, expected_fields)

    def test_get_listable_fields_with_subsequence_filter(self):
        """Test get_listable_fields with multiple filters, one being a subsequence."""
        matching_fields = CustomFieldsComponent.get_listable_fields(['xname', 'sernum'])
        expected_fields = [ComponentField('xname'),
                           ComponentField('Serial Number')]
        self.assertEqual(matching_fields, expected_fields)

    def test_get_listable_fields_non_matching_filter(self):
        """Test get_listable_fields with a filter that doesn't match."""
        matching_fields = CustomFieldsComponent.get_listable_fields(['some-ridiculous-filter'])
        # It should default to showing all fields if none of the fields match.
        self.assertEqual(matching_fields, CustomFieldsComponent.fields)

    def test_get_list_title_pretty(self):
        """Test get_list_title in pretty format."""
        self.assertEqual(CustomFieldsComponent.get_list_title('pretty'),
                         'Listing of all Customs')

    def test_get_list_title_yaml(self):
        """Test get_list_title in yaml format."""
        self.assertEqual(CustomFieldsComponent.get_list_title('yaml'),
                         'custom_list')

    def test_get_list_title_other(self):
        """Test get_list_title in some other format."""
        self.assertEqual(CustomFieldsComponent.get_list_title('json'),
                         'custom_list')


class TestBaseComponentProperties(unittest.TestCase):

    def setUp(self):
        """Set up a component to test against."""
        self.raw_data = get_component_raw_data()
        self.component = SampleComponent(self.raw_data)

    def test_init(self):
        """Create an instance of BaseComponent."""
        self.assertEqual(self.component.raw_data, self.raw_data)

    def test_type(self):
        """Test the type property."""
        self.assertEqual(self.component.type, DEFAULT_HSM_TYPE)

    @mock.patch('sat.system.component.XName', side_effect=lambda s: s)
    def test_xname(self, _):
        """Test the xname property."""
        self.assertEqual(self.component.xname, DEFAULT_XNAME)

    def test_fru_info(self):
        """Test the fru_info property."""
        raw_fru_info = self.raw_data['PopulatedFRU']['{}FRUInfo'.format(DEFAULT_HSM_TYPE)]
        expected_value = ComponentDataDict(raw_fru_info)
        self.assertEqual(self.component.fru_info, expected_value)

    def test_location_info(self):
        """Test the location_info property."""
        expected_value = self.raw_data['{}LocationInfo'.format(DEFAULT_HSM_TYPE)]
        self.assertEqual(self.component.location_info, expected_value)

    def test_manufacturer(self):
        """Test the manufacturer property."""
        self.assertEqual(self.component.manufacturer, DEFAULT_MANUFACTURER)

    def test_model(self):
        """Test the model property."""
        self.assertEqual(self.component.model, DEFAULT_MODEL)

    def test_part_number(self):
        """Test the part_number property."""
        self.assertEqual(self.component.part_number, DEFAULT_PART_NUMBER)

    def test_sku(self):
        """Test the sku property."""
        self.assertEqual(self.component.sku, DEFAULT_SKU)

    def test_serial_number(self):
        """Test the serial_number property."""
        self.assertEqual(self.component.serial_number, DEFAULT_SERIAL_NUMBER)

    @mock.patch('sat.system.component.XName', side_effect=lambda s: s)
    def test_get_dict_pretty(self, _):
        """Test the get_dict method."""
        expected_dict = {
            'xname': DEFAULT_XNAME,
            'Manufacturer': DEFAULT_MANUFACTURER,
            'Model': DEFAULT_MODEL,
            'Part Number': DEFAULT_PART_NUMBER,
            'SKU': DEFAULT_SKU,
            'Serial Number': DEFAULT_SERIAL_NUMBER
        }
        self.assertEqual(self.component.get_dict(BaseComponent.fields,
                                                 'pretty_name'),
                         expected_dict)

    @mock.patch('sat.system.component.XName', side_effect=lambda s: s)
    def test_get_dict_canonical(self, _):
        """Test the get_dict method with the canonical field names."""
        expected_dict = {
            'xname': DEFAULT_XNAME,
            'manufacturer': DEFAULT_MANUFACTURER,
            'model': DEFAULT_MODEL,
            'part_number': DEFAULT_PART_NUMBER,
            'sku': DEFAULT_SKU,
            'serial_number': DEFAULT_SERIAL_NUMBER
        }
        self.assertEqual(self.component.get_dict(BaseComponent.fields,
                                                 'canonical_name'),
                         expected_dict)

    def test_str(self):
        """Test the string representation of a component."""
        self.assertEqual(DEFAULT_XNAME, str(self.component))


class TestBaseComponentChildren(ExtendedTestCase):

    def setUp(self):
        """Set up a parent component and add children components."""
        self.raw_data = get_component_raw_data()
        self.component = SampleComponent(self.raw_data)

        self.children_model = 'ABC123'
        # Set one of the values to a non-string value to test behavior of
        # get_unique_values_str with non-string values.
        self.children_sku = 12345
        self.children_xnames = [DEFAULT_XNAME + 'd{}'.format(index)
                                for index in range(5)]
        self.children_ser_nums = [str(ser_num) for ser_num in range(1000, 1005)]

        self.children_raw_data = [
            get_component_raw_data(hsm_type=ChildComponent.hsm_type,
                                   model=self.children_model,
                                   xname=xname, serial_number=ser_num,
                                   sku=self.children_sku)
            for xname, ser_num in zip(self.children_xnames, self.children_ser_nums)
            ]
        self.children_components = [ChildComponent(raw_data)
                                    for raw_data in self.children_raw_data]

        for child in self.children_components:
            self.component.add_child_object(child)

    def test_add_valid_children(self):
        """Test valid children have been added in setUp."""
        expected_value = {child.xname: child
                          for child in self.children_components}
        self.assertEqual(self.component.children_by_type[ChildComponent],
                         expected_value)

    def test_add_invalid_children(self):
        """Test that adding invalid children results in a log message."""
        invalid_children = [None, 1, 'something', {'foo': 'bar'}]
        with self.assertLogs(LOGGER, logging.WARNING) as cm:
            for child in invalid_children:
                self.component.add_child_object(child)
            for child in invalid_children:
                self.assert_in_element(
                    "Received unknown object '{}' "
                    "to add as child of object '{}'".format(child, self.component),
                    cm.output)

    def test_get_child_vals_unique(self):
        """Test get_child_vals on serial numbers, which are unique."""
        expected_vals = self.children_ser_nums
        actual_vals = self.component.get_child_vals(ChildComponent, 'serial_number')
        self.assertEqual(actual_vals, expected_vals)

    def test_get_child_vals_all_same(self):
        """Test get_child_vals on models, which are all the same."""
        expected_vals = [self.children_model] * len(self.children_components)
        actual_vals = self.component.get_child_vals(ChildComponent, 'model')
        self.assertEqual(actual_vals, expected_vals)

    def test_get_child_vals_unknown(self):
        """Test get_child_vals on an unknown child type."""
        # The SampleComponent type does not have any children of type SampleComponent
        actual_vals = self.component.get_child_vals(SampleComponent, 'xname')
        self.assertEqual(actual_vals, [])

    def test_get_unique_child_vals_unique(self):
        """Test get_unique_child_vals on serial numbers, which are unique."""
        expected_vals = set(self.children_ser_nums)
        actual_vals = self.component.get_unique_child_vals(ChildComponent, 'serial_number')
        self.assertEqual(actual_vals, expected_vals)

    def test_get_unique_child_vals_all_same(self):
        """Test get_unique_child_vals on models, which are all the same."""
        expected_vals = {self.children_model}
        actual_vals = self.component.get_unique_child_vals(ChildComponent, 'model')
        self.assertEqual(actual_vals, expected_vals)

    def test_get_unique_child_vals_unknown(self):
        """Test get_child_vals on an unknown child type."""
        # The SampleComponent type does not have any children of type SampleComponent
        actual_vals = self.component.get_unique_child_vals(SampleComponent, 'xname')
        self.assertEqual(actual_vals, set())

    def test_get_unique_child_vals_str_unique(self):
        actual_str = self.component.get_unique_child_vals_str(ChildComponent,
                                                              'serial_number')
        self.assertEqual(sorted(actual_str.split(', ')), self.children_ser_nums)

    def test_get_unique_child_vals_str_all_same(self):
        expected_str = self.children_model
        actual_str = self.component.get_unique_child_vals_str(ChildComponent,
                                                              'model')
        self.assertEqual(actual_str, expected_str)

    def test_get_unique_child_vals_str_int_val(self):
        expected_str = str(self.children_sku)
        actual_str = self.component.get_unique_child_vals_str(ChildComponent,
                                                              'sku')
        self.assertEqual(actual_str, expected_str)

    def test_get_unique_child_vals_str_unknown(self):
        """Test get_child_vals on an unknown child type."""
        # The SampleComponent type does not have any children of type SampleComponent
        actual_vals = self.component.get_unique_child_vals_str(SampleComponent, 'xname')
        self.assertEqual(actual_vals, EMPTY_VALUE)


if __name__ == '__main__':
    unittest.main()
