#
# MIT License
#
# (C) Copyright 2020 Hewlett Packard Enterprise Development LP
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
Unit tests for the sat.waiting module.
"""

import itertools
from unittest.mock import Mock, patch

from sat.waiting import (
    DependencyCycleError,
    DependencyGroupMember,
    DependencyGroupWaiter,
    GroupWaiter,
    SimultaneousWaiter,
    Waiter,
    WaitingFailure,
)
from tests.common import ExtendedTestCase


def get_mock_waiter(complete_behavior):
    """Get a Waiter class which mocks out completion checking.

    This is a simple helper function for creating classes to test the
    GroupWaiter.wait_for_completion method.

    Args:
        complete_behavior (bool|[Any]|Exception):
            if boolean, has_completed always return this value.
            if iterable, has_completed will return the members of the iterable
                in order of calls.
            if an Exception type, then throw that exception when has_completed()
                is called.
    """
    try:
        return_vals = iter(complete_behavior)
    except TypeError:
        pass

    class MockWaiter(Waiter):
        def has_completed(self):
            if 'return_vals' in locals():
                try:
                    return bool(next(return_vals))
                except StopIteration:
                    return True
            elif isinstance(complete_behavior, Exception):
                raise complete_behavior
            else:
                return bool(complete_behavior)

        def condition_name(self):
            return 'Testing Waiter'

    return MockWaiter


def get_mock_group_waiter(member_complete_behavior, parent_cls=GroupWaiter):
    """Get a GroupWaiter class or a subclass thereof which mocks out completion checking.

    This is a simple helper function for creating classes to test the
    GroupWaiter.wait_for_completion method.

    Args:
        member_complete_behavior (bool|str -> bool):
            if boolean, member_has_completed always return this value.
            if a function, return the result of calling that function
                against the given member.
    """
    assert issubclass(parent_cls, GroupWaiter)

    class MockGroupWaiter(parent_cls):
        def member_has_completed(self, member):
            if callable(member_complete_behavior):
                return member_complete_behavior(member)
            else:
                return bool(member_complete_behavior)

        def condition_name(self):
            return 'Testing GroupWaiter'

    return MockGroupWaiter


SuccessfulWaiter = get_mock_waiter(True)


class WaiterTestCase(ExtendedTestCase):
    """Common test class for (Group)Waiter classes."""
    def setUp(self):
        self.mock_time_monotonic = patch('sat.waiting.time.monotonic',
                                         side_effect=itertools.count(0, 1)).start()
        self.mock_time_sleep = patch('sat.waiting.time.sleep').start()

        self.mock_thread_patcher = patch('sat.waiting.Thread')
        self.mock_thread = self.mock_thread_patcher.start()
        self.mock_thread.return_value.is_alive.side_effect = [True, False]

    def tearDown(self):
        patch.stopall()


class TestWaiter(WaiterTestCase):
    """Test the abstract Waiter class."""

    def test_wait_for_completion_succeeds(self):
        """Test waiting for single condition that succeeds before timeout."""
        waiter = SuccessfulWaiter(10)
        self.assertTrue(waiter.wait_for_completion())

    def test_failed_is_false_on_success(self):
        """Test that the Waiter.failed attribute is False when a Waiter succeeds."""
        waiter = SuccessfulWaiter(10)
        waiter.wait_for_completion()
        self.assertFalse(waiter.failed)

    def test_wait_for_completion_times_out(self):
        """Test that a failing test times out."""
        TimeoutWaiter = get_mock_waiter(False)
        waiter = TimeoutWaiter(2)
        self.assertFalse(waiter.wait_for_completion())

    def test_no_negative_retries(self):
        """Test that the number of retries cannot be negative"""
        with self.assertRaises(ValueError):
            _ = SuccessfulWaiter(10, retries=-1)

    def test_raising_waitingfailure_sets_failed_attr(self):
        """Test that raising WaitingFailure in a Waiter sets the `failed` attribute"""
        FailingWaiter = get_mock_waiter(WaitingFailure())
        instance = FailingWaiter(10)
        instance.wait_for_completion()
        self.assertTrue(instance.failed)

    def test_raising_waitingfailure_propagates_err_msg(self):
        """Test that an error message is printed when a Waiter stops on failure"""
        errmsg = "something bad happened!"
        FailingWaiter = get_mock_waiter(WaitingFailure(errmsg))
        instance = FailingWaiter(10)
        with self.assertLogs(level='ERROR') as cm:
            instance.wait_for_completion()
        self.assert_in_element(errmsg, cm.output)

    @patch('sat.waiting.Waiter.on_retry_action')
    def test_raising_waitingfailure_prevents_retries(self, mock_on_retry_action):
        """Test that retries do not occur when a failure occurs"""
        # The fact that we pass a WaitingFailure instance to the mock waiter
        # isn't actually important. The has_completed() method will be patched
        # manually below.
        FailingWaiter = get_mock_waiter(WaitingFailure())
        instance = FailingWaiter(10, retries=10)

        with patch.object(instance, 'has_completed', side_effect=WaitingFailure) as mock_has_completed:
            instance.wait_for_completion()
            mock_on_retry_action.assert_not_called()
            mock_has_completed.assert_called_once()

    @patch('sat.waiting.Waiter.pre_wait_action')
    @patch('sat.waiting.Waiter.post_wait_action')
    @patch('sat.waiting.Waiter.on_retry_action')
    def test_pre_post_hooks_are_called(self, mock_on_retry, mock_post_wait, mock_pre_wait):
        """Check that user-defined pre/post hooks are always called"""
        instance = SuccessfulWaiter(10)
        instance.wait_for_completion()

        mock_pre_wait.assert_called_once()
        mock_post_wait.assert_called_once()
        mock_on_retry.assert_not_called()

    @patch('sat.waiting.Waiter.pre_wait_action')
    @patch('sat.waiting.Waiter.post_wait_action')
    @patch('sat.waiting.Waiter.on_retry_action')
    def test_on_retry_hooks_are_called(self, mock_on_retry, mock_post_wait, mock_pre_wait):
        """Check that user-defined on-retry hook is called on retry"""
        NotQuiteReadyWaiter = get_mock_waiter([False, True])
        instance = NotQuiteReadyWaiter(0.5, retries=1)
        instance.wait_for_completion()

        mock_pre_wait.assert_called_once()
        mock_post_wait.assert_called_once()
        mock_on_retry.assert_called_once()

    def test_wait_async_launch_thread(self):
        """Test that a thread is created when waiting asynchronously"""
        instance = SuccessfulWaiter(10)
        instance.wait_for_completion_async()

        self.mock_thread.assert_called_once_with(target=instance.wait_for_completion)
        self.mock_thread.return_value.start.assert_called_once()

    def test_wait_await_join_thread(self):
        """Test that the waiting thread is joined when wait_..._await called"""
        instance = SuccessfulWaiter(10)

        instance.wait_for_completion_async()
        instance.wait_for_completion_await()

        self.mock_thread.return_value.join.assert_called()

    def test_wait_context_manager_works(self):
        """Test that the GroupWaiter context manager waits in background"""

        with SuccessfulWaiter(10) as instance:
            pass

        self.mock_thread.assert_called_once_with(target=instance.wait_for_completion)
        self.mock_thread.return_value.start.assert_called_once()
        self.mock_thread.return_value.join.assert_called()

    def test_is_waiting_async(self):
        """Test if an async waiter is waiting"""
        instance = SuccessfulWaiter(10)
        self.assertFalse(instance.is_waiting_async())
        instance.wait_for_completion_async()
        self.assertTrue(instance.is_waiting_async())
        self.assertFalse(instance.is_waiting_async())


class TestSimulWaiter(WaiterTestCase):
    """Test the abstract SimultaneousWaiter class."""
    def setUp(self):
        super().setUp()

    def test_init_with_bad_class(self):
        """Test the SimultaneousWaiter only accepts Waiter subclasses"""
        with self.assertRaises(TypeError):
            SimultaneousWaiter(Mock())

    def test_starts_threads(self):
        """Test the SimultaneousWaiter starts and cleans up threads"""
        sw = SimultaneousWaiter([SuccessfulWaiter], 10)
        sw.wait_for_completion()
        self.mock_thread.assert_called_once()
        self.mock_thread.return_value.join.assert_called()

    def test_simul_waiter_completed(self):
        """Test waiting for multiple conditions"""
        self.mock_thread_patcher.stop()

        EventualWaiter = get_mock_waiter([False, True])
        sw = SimultaneousWaiter([EventualWaiter, SuccessfulWaiter], 5)
        self.assertTrue(sw.wait_for_completion())

    def test_simul_waiter_failed(self):
        """Test failing to wait for one of multiple simultaneous conditions."""
        self.mock_thread_patcher.stop()

        NotFastEnoughWaiter = get_mock_waiter([False, True])
        sw = SimultaneousWaiter([NotFastEnoughWaiter, SuccessfulWaiter], 2)
        self.assertFalse(sw.wait_for_completion())


class GroupWaiterTestCase(WaiterTestCase):
    """Test case for testing GroupWaiters."""
    def setUp(self):
        super().setUp()
        self.members = ['foo', 'bar', 'baz']


class TestGroupWaiter(GroupWaiterTestCase):
    """Test the abstract GroupWaiter class."""

    def test_wait_for_completion_all_successful(self):
        """Test generic waiting for completion when all members succeed"""
        SuccessfulWaiter = get_mock_group_waiter(True)
        instance = SuccessfulWaiter(self.members, 10)

        self.assertEqual(len(instance.wait_for_completion()), 0)
        self.mock_time_sleep.assert_called()

    def test_wait_for_completion_all_time_out(self):
        """Test generic waiting for completion when all members time out"""
        FailingWaiter = get_mock_group_waiter(False)
        instance = FailingWaiter(self.members, 10)
        self.assertEqual(len(self.members), len(instance.wait_for_completion()))

    def test_wait_for_completion_some_fail(self):
        """Test generic waiting for completion when only some members time out"""
        SometimesFailingWaiter = get_mock_group_waiter(lambda m: m != 'baz')
        instance = SometimesFailingWaiter(self.members, 10)
        self.assertEqual(len(instance.wait_for_completion()), 1)

    @patch('sat.waiting.GroupWaiter.pre_wait_action')
    @patch('sat.waiting.GroupWaiter.post_wait_action')
    @patch('sat.waiting.GroupWaiter.on_check_action')
    @patch('sat.waiting.GroupWaiter.on_retry_action')
    def test_hooks_are_called(self, mock_on_retry, mock_on_check, mock_post_wait, mock_pre_wait):
        """Check that all user-defined hooks are always called"""
        SuccessfulWaiter = get_mock_group_waiter(True)
        instance = SuccessfulWaiter(self.members, 10)
        instance.wait_for_completion()

        mock_on_check.assert_called_once()
        mock_pre_wait.assert_called_once()
        mock_post_wait.assert_called_once()
        mock_on_retry.assert_not_called()

    @patch('sat.waiting.GroupWaiter.on_retry_action')
    def test_on_retry_hook_is_called(self, mock_on_retry):
        """Check that waiting is retried if some members time out"""
        TimeoutWaiter = get_mock_group_waiter(False)
        instance = TimeoutWaiter(self.members, 10, retries=1)
        instance.wait_for_completion()
        mock_on_retry.assert_called_once()


class TestFailingGroupWaiter(GroupWaiterTestCase):
    """Tests for GroupWaiter when some members fail"""
    def setUp(self):
        super().setUp()
        self.failed_members = set(self.members[:2])

        def member_has_completed(member):
            if member in self.failed_members:
                raise WaitingFailure('something is wrong')
            return False
        self.CatastrophicWaiter = get_mock_group_waiter(member_has_completed)

    def test_wait_for_completion_failing_nodes_recorded(self):
        """Test that the members which failed are recorded in the `failed` attribute"""
        instance = self.CatastrophicWaiter(self.members, 10)
        instance.wait_for_completion()
        self.assertEqual(self.failed_members, instance.failed)

    def test_wait_for_completion_failing_nodes_not_returned(self):
        """Test that failed members are not returned by wait_for_completion()"""
        instance = self.CatastrophicWaiter(self.members, 10)
        self.assertFalse(set(instance.wait_for_completion()).intersection(self.failed_members))


class DependentTestMember(DependencyGroupMember):
    def __init__(self, name, *, test_case):
        super().__init__()
        self.name = name

        self.begin_calls = 0
        self.test_case = test_case

    def begin(self):
        self.begin_calls += 1
        self.test_case.begun_members.append(self)

    def __repr__(self):
        return f'<test dependent item: {self.name}>'


class DependencyGroupTestCase(WaiterTestCase):
    """Scaffolding for dependency group tests"""
    def setUp(self):
        super().setUp()
        first = DependentTestMember('first', test_case=self)
        second_1 = DependentTestMember('second_1', test_case=self)
        second_2 = DependentTestMember('second_2', test_case=self)
        third = DependentTestMember('third', test_case=self)

        # Diamond dependency graph
        second_1.add_dependency(first)
        second_2.add_dependency(first)
        third.add_dependency(second_1)
        third.add_dependency(second_2)

        self.members = [first, second_1, second_2, third]


class TestDependencyGroupMember(DependencyGroupTestCase):
    def test_full_dependencies(self):
        """Test finding the full set of dependencies of an item"""
        closure = self.members[-1].full_dependencies()
        for member in self.members[:-1]:
            with self.subTest(member=member):
                self.assertIn(member, closure)
        with self.subTest(member=self.members[-1]):
            self.assertNotIn(self.members[-1], closure)

    def test_cannot_create_dep_cycles(self):
        """Test that adding cyclic dependencies is disallowed"""
        n_members = 5
        members = [DependentTestMember(f'member {n}', test_case=self)
                   for n in range(n_members)]
        with self.assertRaises(DependencyCycleError):
            for idx, member in enumerate(members):
                # Treat the member list like a ring buffer and make each member
                # depend on the next member. This forms a simple circular
                # dependency structure.
                member.add_dependency(members[(idx + 1) % n_members])

    def test_dep_chain(self):
        """Test building a simple chain of dependencies"""
        first = DependentTestMember('first', test_case=self)
        second = DependentTestMember('second', test_case=self)
        third = DependentTestMember('third', test_case=self)
        second.add_dependency(first)
        third.add_dependency(second)

        self.assertEqual(third.depends_on(first), [third, second, first])

    def test_dep_chain_when_no_chain_exists(self):
        """Test that no dependencies are returned when no relationship exists"""
        self.assertEqual(self.members[0].depends_on(self.members[-1]), [])

    def test_complex_dep_chain(self):
        """Test dependency chain with a more complex setup"""
        chain = self.members[-1].depends_on(self.members[0])
        for idx, member in enumerate(chain):
            if idx - 1 > 0:
                self.assertIn(member, chain[idx - 1].dependencies)


class DependencyGroupWaiterTestCase(DependencyGroupTestCase):
    def setUp(self):
        super().setUp()
        self.begun_members = []


class TestSuccessfulDependencyGroupWaiter(DependencyGroupWaiterTestCase):
    def setUp(self):
        self.SuccessfulDepWaiter = get_mock_group_waiter(True, parent_cls=DependencyGroupWaiter)
        super().setUp()

    def test_all_members_are_awaited(self):
        """Test that all dependent members are awaited in the successful case"""
        self.SuccessfulDepWaiter(self.members, 10).wait_for_completion()
        for member in self.members:
            with self.subTest(member=member):
                self.assertEqual(member.begin_calls, 1)

    def test_members_awaited_in_correct_order(self):
        """Test that dependent waiters are waited for in the proper order"""
        self.SuccessfulDepWaiter(self.members, 10).wait_for_completion()

        # To test that dependencies are started in the proper order, make sure
        # that the index of each member recorded after start is strictly greater
        # than that of each of its dependencies. This checks for topological
        # sorting.
        for member in self.members:
            with self.subTest(member=member):
                for dep in member.dependencies:
                    self.assertGreater(self.begun_members.index(member), self.begun_members.index(dep))

    def test_members_must_be_dep_group_member_subclasses(self):
        """Test that all dependent group members subclass DependencyGroupMember"""
        with self.assertRaises(TypeError):
            _ = self.SuccessfulDepWaiter([object()], 10)


class TestFailingDependencyGroupWaiter(DependencyGroupWaiterTestCase):
    def setUp(self):
        super().setUp()

        def fail_conditionally(member):
            if getattr(member, 'should_fail', False):
                raise WaitingFailure('failed!')
            return True

        self.FailingDepWaiter = get_mock_group_waiter(fail_conditionally, parent_cls=DependencyGroupWaiter)

    def test_members_not_started_after_dep_fails(self):
        """Test that a failing dependency prevents beginning another member"""
        self.members[1].should_fail = True
        self.FailingDepWaiter(self.members, 10).wait_for_completion()
        for member in self.members:
            with self.subTest(member=member):
                if any(getattr(dep, 'should_fail', False) for dep in member.full_dependencies()):
                    self.assertNotIn(member, self.begun_members)
                else:
                    self.assertIn(member, self.begun_members)

    def test_failing_members_started_only_once_on_retry(self):
        """Test DependencyGroupWaiter only starts members once when retries >= 1"""
        self.members[1].should_fail = True
        self.FailingDepWaiter(self.members, 10, retries=2).wait_for_completion()
        for member in self.members:
            with self.subTest(member=member):
                if any(getattr(dep, 'should_fail', False) for dep in member.full_dependencies()):
                    self.assertEqual(member.begin_calls, 0)
                else:
                    self.assertEqual(member.begin_calls, 1)
