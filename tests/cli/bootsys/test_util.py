"""
Tests for common bootsys code.

(C) Copyright 2020-2021 Hewlett Packard Enterprise Development LP.

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
import logging
from textwrap import dedent
import unittest
from unittest.mock import call, mock_open, patch, Mock

from sat.cli.bootsys.util import (
    get_mgmt_ncn_hostnames,
    get_and_verify_ncn_groups,
    get_mgmt_ncn_groups,
    get_ssh_client,
    prompt_for_ncn_verification,
    FatalBootsysError
)


class TestGetNcns(unittest.TestCase):

    def setUp(self):
        """Set up a mock open function for the hosts file."""
        self.hosts_file_contents = dedent("""\
            10.252.2.14     ncn-s003 ncn-s003.local ncn-s003.nmn
            10.252.2.13     ncn-s002 ncn-s002.local ncn-s002.nmn
            10.252.2.12     ncn-s001 ncn-s001.local ncn-s001.nmn
            10.252.2.18     ncn-w003 ncn-w003.local ncn-w003.nmn
            10.252.2.9      ncn-w002 ncn-w002.local ncn-w002.nmn
            10.252.2.8      ncn-w001 ncn-w001.local ncn-w001.nmn
            10.252.2.15     ncn-m003 ncn-m003.local ncn-m003.nmn
            10.252.2.16     ncn-m002 ncn-m002.local ncn-m002.nmn
            #10.252.2.19     ncn-m001 ncn-m001.local ncn-m001.nmn
            10.252.2.20     uan01 uan01.nmn  # Repurposed ncn-w004
            10.252.2.100    rgw-vip rgw-vip.local rgw-vip.nmn rgw rgw.local
        """)
        patch('builtins.open', mock_open(read_data=self.hosts_file_contents)).start()

    def tearDown(self):
        """Stop the patches."""
        patch.stopall()

    def test_get_managers(self):
        """Test getting hostnames of all managers."""
        # Note that ncn-m001 is commented out
        expected = {'ncn-m002', 'ncn-m003'}
        actual = get_mgmt_ncn_hostnames(['managers'])
        self.assertEqual(expected, actual)

    def test_get_workers(self):
        """Test getting hostnames of all workers."""
        expected = {'ncn-w001', 'ncn-w002', 'ncn-w003'}
        actual = get_mgmt_ncn_hostnames(['workers'])
        self.assertEqual(expected, actual)

    def test_get_storage(self):
        """Test getting hostnames of all storage nodes."""
        expected = {'ncn-s001', 'ncn-s002', 'ncn-s003'}
        actual = get_mgmt_ncn_hostnames(['storage'])
        self.assertEqual(expected, actual)

    def test_get_all_ncns(self):
        """Test getting hostnames of all managers, workers, and storage nodes."""
        # Note that ncn-m001 is commented out
        expected = {'ncn-m002', 'ncn-m003',
                    'ncn-w001', 'ncn-w002', 'ncn-w003',
                    'ncn-s001', 'ncn-s002', 'ncn-s003'}
        actual = get_mgmt_ncn_hostnames(['managers', 'workers', 'storage'])
        self.assertEqual(expected, actual)

    def test_get_invalid_subrole(self):
        """Test getting hostnames with an invalid subrole included."""
        subroles = ['managers', 'impostors', 'workers']
        with self.assertRaisesRegex(ValueError, r'Invalid subroles given: impostors'):
            get_mgmt_ncn_hostnames(subroles)

    def test_get_invalid_subroles(self):
        """Test getting hostnames with multiple invalid subroles included."""
        subroles = ['managers', 'impostors', 'workers', 'crewmates']
        with self.assertRaisesRegex(ValueError, r'Invalid subroles given: impostors, crewmates'):
            get_mgmt_ncn_hostnames(subroles)

    def test_get_workers_substring(self):
        """Test getting worker NCN hostnames with tricky hostnames in the hosts file."""
        hosts_file_contents = dedent("""\
            10.252.2.7      not-ncn-w002 not-ncn-w002.local not-ncn-w002.nmn
            10.252.2.8      ncn-w001 ncn-w001.local ncn-w001.nmn
            10.252.3.8      ncn-w002.someothernet
        """)
        expected = {'ncn-w001'}
        with patch('builtins.open', mock_open(read_data=hosts_file_contents)):
            actual = get_mgmt_ncn_hostnames(['workers'])
        self.assertEqual(expected, actual)

    def test_get_workers_no_newline(self):
        """Test getting worker NCN hostname from last line without trailing whitespace."""
        hosts_file_contents = dedent("""\
            10.252.2.7      ncn-w001
            10.252.2.8      ncn-w002
            10.252.2.9      ncn-w003""")
        expected = {'ncn-w001', 'ncn-w002', 'ncn-w003'}
        with patch('builtins.open', mock_open(read_data=hosts_file_contents)):
            actual = get_mgmt_ncn_hostnames(['workers'])
        self.assertEqual(expected, actual)

    @patch('builtins.open', side_effect=FileNotFoundError('dne'))
    def test_get_ncns_hosts_file_error(self, _):
        """Test getting NCNs when hosts file cannot be opened."""
        with self.assertLogs(level=logging.ERROR) as cm:
            actual = get_mgmt_ncn_hostnames(['managers'])
        self.assertEqual(cm.records[0].message, 'Unable to read /etc/hosts to obtain '
                                                'management NCN hostnames: dne')
        self.assertEqual(set(), actual)


class TestGetNCNGroups(unittest.TestCase):
    """Tests for the get_mgmt_ncn_groups function."""

    def setUp(self):
        """Set up mocks."""
        self.mock_managers = ['ncn-m001', 'ncn-m002', 'ncn-m003']
        self.mock_workers = ['ncn-w001', 'ncn-w002', 'ncn-w003']
        self.mock_storage = ['ncn-s001', 'ncn-s002', 'ncn-s003']

        def mock_get_hostnames(subroles):
            if subroles == ['managers']:
                return set(self.mock_managers)
            elif subroles == ['workers']:
                return set(self.mock_workers)
            elif subroles == ['managers', 'workers']:
                return set(self.mock_managers + self.mock_workers)
            elif subroles == ['storage']:
                return set(self.mock_storage)
            else:
                return set()

        self.mock_get_hostnames = patch(
            'sat.cli.bootsys.util.get_mgmt_ncn_hostnames', mock_get_hostnames).start()

    def tearDown(self):
        patch.stopall()

    def test_no_exclusions(self):
        """Test get_mgmt_ncn_groups with no exclusions."""
        expected = (
            {
                'managers': self.mock_managers,
                'workers': self.mock_workers,
                'storage': self.mock_storage
            },
            {
                'managers': [],
                'workers': [],
                'storage': []
            }
        )
        actual = get_mgmt_ncn_groups()
        self.assertEqual(expected, actual)

    def test_one_exclusion_each(self):
        excluded = {self.mock_managers[0], self.mock_workers[1], self.mock_storage[2]}
        expected = (
            {
                'managers': self.mock_managers[1:],
                'workers': [self.mock_workers[0], self.mock_workers[2]],
                'storage': self.mock_storage[:2]
            },
            {
                'managers': [self.mock_managers[0]],
                'workers': [self.mock_workers[1]],
                'storage': [self.mock_storage[2]]
            }
        )
        actual = get_mgmt_ncn_groups(excluded)
        self.assertEqual(expected, actual)

    @staticmethod
    def get_empty_group_message(group_names):
        """Helper to get a message for the empty group(s)

        Args:
            group_names (list of str): The list of empty group names.
        """
        return f'Failed to identify members of the following NCN subrole(s): {group_names}'

    def test_empty_managers(self):
        """Test with no managers identified."""
        self.mock_managers = []
        with self.assertRaises(FatalBootsysError) as err:
            get_mgmt_ncn_groups()
        self.assertEqual(self.get_empty_group_message(['managers']), str(err.exception))

    def test_empty_workers(self):
        """Test with no workers identified."""
        self.mock_workers = []
        with self.assertRaises(FatalBootsysError) as err:
            get_mgmt_ncn_groups()
        self.assertEqual(self.get_empty_group_message(['workers']), str(err.exception))

    def test_empty_storage(self):
        """Test with no storage nodes identified."""
        self.mock_storage = []
        with self.assertRaises(FatalBootsysError) as err:
            get_mgmt_ncn_groups()
        self.assertEqual(self.get_empty_group_message(['storage']), str(err.exception))

    def test_all_empty(self):
        """Test with no NCNs of any category identified."""
        self.mock_managers = []
        self.mock_workers = []
        self.mock_storage = []
        with self.assertRaises(FatalBootsysError) as err:
            get_mgmt_ncn_groups()
        self.assertEqual(self.get_empty_group_message(['managers', 'workers', 'storage']),
                         str(err.exception))


class TestPromptForNCNVerification(unittest.TestCase):
    """Tests for prompt_for_ncn_verification function."""

    def setUp(self):
        """Set up mocks."""
        self.mock_print = patch('builtins.print').start()
        self.mock_yaml_dump = patch('yaml.dump').start()

        self.mock_incl_ncns = {
            'managers': ['ncn-m002', 'ncn-m003'],
            'workers': ['ncn-w001', 'ncn-w002'],
            'storage': ['ncn-s001', 'ncn-s003']
        }
        self.mock_excl_ncns = {
            'managers': ['ncn-m001'],
            'workers': ['ncn-w003'],
            'storage': ['ncn-s002']
        }

        self.mock_pester_choices = patch(
            'sat.cli.bootsys.util.pester_choices').start()

    def tearDown(self):
        patch.stopall()

    def assert_printed_messages(self, has_exclusions=False):
        """Helper function to assert proper messages printed.

        Args:
            has_exclusions (bool): If true, then assert that excluded nodes are printed.
        """
        expected_print_calls = [
            call('The following Non-compute Nodes (NCNs) will be included in this operation:'),
            call(self.mock_yaml_dump.return_value)
        ]
        expected_yaml_calls = [
            call(self.mock_incl_ncns)
        ]

        if has_exclusions:
            expected_print_calls.extend([
                call('The following Non-compute Nodes (NCNs) will be excluded from this operation:'),
                call(self.mock_yaml_dump.return_value),
            ])
            pester_prompt = 'Are the above NCN groupings and exclusions correct?'
            expected_yaml_calls.append(call(self.mock_excl_ncns))
        else:
            pester_prompt = 'Are the above NCN groupings correct?'

        self.mock_print.assert_has_calls(expected_print_calls)
        self.mock_yaml_dump.assert_has_calls(expected_yaml_calls)
        self.mock_pester_choices.assert_called_once_with(pester_prompt, ('yes', 'no'))

    def test_groups_confirmed(self):
        """Test with user confirming the identified groups."""
        self.mock_pester_choices.return_value = 'yes'
        prompt_for_ncn_verification(self.mock_incl_ncns, self.mock_excl_ncns)
        self.assert_printed_messages(has_exclusions=True)

    def test_groups_denied(self):
        """Test with user denying the identified groups."""
        self.mock_pester_choices.return_value = 'no'
        err_regex = 'User indicated NCN groups are incorrect'
        with self.assertRaisesRegex(FatalBootsysError, err_regex):
            prompt_for_ncn_verification(self.mock_incl_ncns, self.mock_excl_ncns)
        self.assert_printed_messages(has_exclusions=True)

    def test_no_exclusions(self):
        """Test with no exclusions."""
        self.mock_pester_choices.return_value = 'yes'

        # Make a new included NCNs mapping that includes all the NCNs
        self.mock_incl_ncns = {group: self.mock_incl_ncns[group] + self.mock_excl_ncns[group]
                               for group in ('managers', 'workers', 'storage')}
        # Make a new excluded NCN mapping that includes none of the NCNs
        self.mock_excl_ncns = {group: [] for group in ('managers', 'workers', 'storage')}

        prompt_for_ncn_verification(self.mock_incl_ncns, self.mock_excl_ncns)

        self.assert_printed_messages(has_exclusions=False)


class TestGetAndVerifyNCNs(unittest.TestCase):
    """Test the get_and_verify_ncns function."""

    def setUp(self):
        """Set up mocks."""
        self.mock_get_ncn_groups = patch('sat.cli.bootsys.util.get_mgmt_ncn_groups').start()

        self.mock_get_ncn_groups.return_value = (
            {'managers': [f'ncn-m00{idx}' for idx in range(4)],
             'workers': [f'ncn-w00{idx}' for idx in range(6)],
             'storage': [f'ncn-s00{idx}' for idx in range(4)]},
            {'managers': [], 'workers': [], 'storage': []}
        )

        self.mock_prompt_for_ncn_verification = patch(
            'sat.cli.bootsys.util.prompt_for_ncn_verification').start()

    def tearDown(self):
        patch.stopall()

    def test_kubernetes_group_creation(self):
        """Test that get_and_verify_ncns adds a 'kubernetes' group."""
        mock_excl = Mock()

        result = get_and_verify_ncn_groups(mock_excl)

        self.mock_get_ncn_groups.assert_called_once_with(mock_excl)
        self.assertIn('kubernetes', result)
        self.assertEqual(result['kubernetes'],
                         self.mock_get_ncn_groups.return_value[0]['managers'] +
                         self.mock_get_ncn_groups.return_value[0]['workers'])


class TestGetSSHClient(unittest.TestCase):
    """Tests for get_ssh_client function."""

    def setUp(self):
        """Set up mocks of paramiko SSHClient and WarningPolicy."""
        self.mock_ssh_client_cls = patch('sat.cli.bootsys.util.SSHClient').start()
        self.mock_ssh_client = self.mock_ssh_client_cls.return_value
        self.mock_warning_policy = patch('sat.cli.bootsys.util.WarningPolicy').start()

    def tearDown(self):
        patch.stopall()

    def test_get_ssh_client(self):
        """Test get_ssh_client function."""
        ssh_client = get_ssh_client()

        self.mock_ssh_client_cls.assert_called_once_with()
        self.mock_ssh_client.load_system_host_keys.assert_called_once_with()
        self.mock_ssh_client.set_missing_host_key_policy.assert_called_once_with(
            self.mock_warning_policy
        )
