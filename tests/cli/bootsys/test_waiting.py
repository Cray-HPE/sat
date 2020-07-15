"""
Unit tests for the sat.cli.bootsys.waiting module.

(C) Copyright 2020 Hewlett Packard Enterprise Development LP.

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

import itertools
import unittest
from unittest.mock import MagicMock, patch

from sat.cli.bootsys.waiting import GroupWaiter


def get_mock_group_waiter(member_complete_behavior):
    """Get a GroupWaiter class which mocks out completion checking.

    This is a simple helper function for creating classes to test the
    GroupWaiter.wait_for_completion method.

    Args:
        member_complete_behavior (bool|str -> bool):
            if boolean, member_has_completed always return this value.
            if a function, return the result of calling that function
                against the given member.
    """

    class MockGroupWaiter(GroupWaiter):
        def member_has_completed(self, member):
            if callable(member_complete_behavior):
                return member_complete_behavior(member)
            else:
                return bool(member_complete_behavior)

        def condition_name(self):
            return 'Testing GroupWaiter'

    return MockGroupWaiter


class TestGroupWaiter(unittest.TestCase):
    """Test the abstract GroupWaiter class."""

    def setUp(self):
        self.mock_time_monotonic = patch('sat.cli.bootsys.waiting.time.monotonic',
                                         side_effect=itertools.count(0, 1)).start()
        self.mock_time_sleep = patch('sat.cli.bootsys.waiting.time.sleep').start()
        self.mock_thread = patch('sat.cli.bootsys.waiting.Thread').start()

        self.members = ['foo', 'bar', 'baz']

    def tearDown(self):
        patch.stopall()

    def test_wait_for_completion_all_successful(self):
        """Test generic waiting for completion when all members succeed"""
        SuccessfulWaiter = get_mock_group_waiter(True)
        instance = SuccessfulWaiter(self.members, 10)

        self.assertEqual(len(instance.wait_for_completion()), 0)
        self.mock_time_sleep.assert_called()

    def test_wait_for_completion_all_fail(self):
        """Test generic waiting for completion when all members succeed"""
        FailingWaiter = get_mock_group_waiter(False)
        instance = FailingWaiter(self.members, 10)
        self.assertEqual(len(self.members), len(instance.wait_for_completion()))

    def test_wait_for_completion_some_fail(self):
        """Test generic waiting for completion when only some members fail"""
        SometimesFailingWaiter = get_mock_group_waiter(lambda m: m != 'baz')
        instance = SometimesFailingWaiter(self.members, 10)
        self.assertEqual(len(instance.wait_for_completion()), 1)

    @patch('sat.cli.bootsys.waiting.GroupWaiter.pre_wait_action')
    @patch('sat.cli.bootsys.waiting.GroupWaiter.post_wait_action')
    @patch('sat.cli.bootsys.waiting.GroupWaiter.on_check_action')
    def test_hooks_are_called(self, mock_on_check, mock_post_wait, mock_pre_wait):
        """Check that all user-defined hooks are always called"""
        SuccessfulWaiter = get_mock_group_waiter(True)
        instance = SuccessfulWaiter(self.members, 10)
        instance.wait_for_completion()

        mock_on_check.assert_called_once()
        mock_pre_wait.assert_called_once()
        mock_post_wait.assert_called_once()

    def test_wait_async_launch_thread(self):
        """Test that a thread is created when waiting asynchronously"""
        SuccessfulWaiter = get_mock_group_waiter(True)
        instance = SuccessfulWaiter(self.members, 10)
        instance.wait_for_completion_async()

        self.mock_thread.assert_called_once_with(target=instance.wait_for_completion)
        self.mock_thread.return_value.start.assert_called_once()

    def test_wait_await_join_thread(self):
        """Test that the waiting thread is joined when wait_..._await called"""
        SuccessfulWaiter = get_mock_group_waiter(True)
        instance = SuccessfulWaiter(self.members, 10)

        instance.wait_for_completion_async()
        instance.pending = set() # This would happen during wait_for_completion
        instance.wait_for_completion_await()

        self.mock_thread.return_value.join.assert_called()

    def test_wait_context_manager_works(self):
        """Test that the GroupWaiter context manager waits in background"""
        SuccessfulWaiter = get_mock_group_waiter(True)

        with SuccessfulWaiter(self.members, 10) as instance:
            instance.pending = set() # This would happen during wait_for_completion

        self.mock_thread.assert_called_once_with(target=instance.wait_for_completion)
        self.mock_thread.return_value.start.assert_called_once()
        self.mock_thread.return_value.join.assert_called()
