"""
Unit tests for the sat.sat.cli.linkhealth.main functions.

Copyright 2019 Cray Inc. All Rights Reserved.
"""


import json
import os
import unittest
from unittest import mock

import sat.cli.linkhealth.main


class FakeRequest:
    """Used for mocking the return from HSMClient.get, which is a Request.
    """

    def json(self):
        endpoints = [
            {'ID': 'x1000c1'},
            {'ID': 'x2000c2'},
            {'ID': 'x3000c3'},
            {'ID': 'x4000c4'},
        ]
        return {'RedfishEndpoints': endpoints}


class TestLinkhealthGetRouterXnames(unittest.TestCase):
    """Test the get_router_names method in linkhealth.

    These tests have more to do with outlining the expected elements
    returned by the functions that get_router_xnames relies on.
    """
    @mock.patch('sat.cli.linkhealth.main.HSMClient.get', return_value=FakeRequest())
    def test_get_xnames_router_bmc(self, get_mocker):
        """It should filter its results using a RouterBMC filter.

        A sat.apiclient.HSMClient instance is responsible for this - and this
        test cements the arguments provided to that call.
        """
        xnames = sat.cli.linkhealth.main.get_router_xnames()
        get_mocker.assert_called_once_with('Inventory', 'RedfishEndpoints', params={'type': 'RouterBMC'})

    @mock.patch('sat.cli.linkhealth.main.HSMClient.get', return_value=FakeRequest())
    @mock.patch(__name__ + '.FakeRequest.json', return_value={'RedfishEndpoints': [{'Not ID': None}]})
    def test_get_xnames_no_ids(self, get_mocker, json_mocker):
        """It should not return RedfishEndpoints that don't have an ID key.
        """
        xnames = sat.cli.linkhealth.main.get_router_xnames()
        get_mocker.assert_called_once()
        json_mocker.assert_called_once()

        self.assertEqual(0, len(xnames))

    @mock.patch('sat.cli.linkhealth.main.HSMClient.get', side_effect=sat.apiclient.APIError)
    def test_api_error(self, get_mocker):
        """It should raise an APIError if the client's get raises an APIError.
        """
        with self.assertRaises(sat.apiclient.APIError):
            xnames = sat.cli.linkhealth.main.get_router_xnames()
        get_mocker.assert_called_once()

    @mock.patch('sat.cli.linkhealth.main.HSMClient.get', return_value=FakeRequest())
    @mock.patch(__name__ + '.FakeRequest.json', return_value={'Not RedfishEndpoints': None})
    def test_incorrect_result(self, get_mocker, json_mocker):
        """It should raise a KeyError if the JSON contains unexpected entries.

        More specifically, the JSON needs to be a dictionary whose top level
        contains entries under a key called 'RedfishEndpoints'.
        """
        with self.assertRaises(KeyError):
            xnames = sat.cli.linkhealth.main.get_router_xnames()

        get_mocker.assert_called_once()
        json_mocker.assert_called_once()

    @mock.patch('sat.cli.linkhealth.main.HSMClient.get', return_value=FakeRequest())
    @mock.patch(__name__ + '.FakeRequest.json', side_effect=ValueError)
    def test_invalid_json(self, get_mocker, json_mocker):
        """It should raise a ValueError if the result is not valid JSON.

        The client.get(...).json() will raise a ValueError if its payload
        was invalid json. In this case, the get_router_xnames should just
        bucket brigade with a custom message.
        """
        with self.assertRaises(ValueError):
            xnames = sat.cli.linkhealth.main.get_router_xnames()
        get_mocker.assert_called_once()
        json_mocker.assert_called_once()


class TestLinkhealthGetMatches(unittest.TestCase):

    def test_get_matches_exact(self):
        """Basic positive test case for get_matches.
        """
        filters = ['hello', 'not here']
        elems = ['hello', 'there']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual({'hello'}, used)
        self.assertEqual({'not here'}, unused)
        self.assertEqual({'hello'}, matches)
        self.assertEqual({'there'}, no_matches)

    def test_get_matches_sub(self):
        """Elements should match if they contain a filter.
        """
        filters = ['hello']
        elems = ['hellosers']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual({'hello'}, used)
        self.assertEqual(set(), unused)
        self.assertEqual({'hellosers'}, matches)
        self.assertEqual(set(), no_matches)

    def test_get_matches_empty_filters(self):
        """It should return empty matches if no filters present.
        """
        filters = []
        elems = ['hello', 'there']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual(set(), used)
        self.assertEqual(set(), unused)
        self.assertEqual(set(), matches)
        self.assertEqual(set(elems), no_matches)

    def test_get_matches_empty_elems(self):
        """It should not fail if provided empty elems.
        """
        filters = ['hello']
        elems = []
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)
        self.assertEqual(set(), used)
        self.assertEqual(set(filters), unused)
        self.assertEqual(set(), matches)
        self.assertEqual(set(), no_matches)

    def test_get_matches_unique_answers(self):
        """The returned values should only contain unique entries.
        """
        filters = ['hello', 'hello', 'there', 'there', 'unused', 'unused']
        elems = ['hello', 'hello']
        used, unused, matches, no_matches = sat.cli.linkhealth.main.get_matches(filters, elems)

        self.assertEqual(1, len(used))
        self.assertEqual(2, len(unused))
        self.assertEqual(1, len(matches))
        self.assertEqual(0, len(no_matches))


if __name__ == '__main__':
    unittest.main()
