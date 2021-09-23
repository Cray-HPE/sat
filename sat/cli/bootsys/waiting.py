"""
Common code for waiting for a condition.

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

import abc
import logging
from threading import Thread
import time

import inflect


inf = inflect.engine()
LOGGER = logging.getLogger(__file__)


class WaitingFailure(Exception):
    """Represents an error which prevents the awaited state from occurring.

    One example of this would be an IPMI waiter failing due to the `ipmitool`
    command not working."""


class Waiter(metaclass=abc.ABCMeta):
    """Waits for a single condition to occur.

    Conceptually, there are four states a Waiter can be in: waiting, failed,
    timed-out, or completed. When a Waiter is first instantiated, and when its
    wait_for_completion() method is first called, it is in the waiting state,
    i.e. it is possible to wait for the condition, the awaited condition has not
    been reached yet, and waiting for it has not finished. If for some reason it
    is impossible to check whether the condition will be reached, or it is known
    that the given condition will never be reached, then the Waiter is in the
    failed state. If it was possible for the awaited condition to be waited for,
    but it did not reach that condition within the given timeframe after calling
    wait_for_completion(), then the Waiter is in the timed-out state. Finally,
    if the condition was reached and wait_for_completion() has been called, then
    the Waiter is in the completed state. These states are not reified directly
    in the code, though understanding what different states the Waiter can be in
    can help understand how the class works internally.

    Attributes:
        timeout (int): the timeout, in seconds, for the wait operation
        poll_interval (int): the interval, in seconds, between polls for
            completion.
        completed (bool): True if the condition has been met, False otherwise.
        retries (int): the number of times waiting may be retried. By default,
            this is 0, meaning the wait will only occur once.
        failed (bool): True if there was an irrecoverable failure waiting
            for the condition, False if waiting did not have issues.
    """
    def __init__(self, timeout, poll_interval=1, retries=0):
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.completed = False
        self.failed = False
        self._waiter_thread = None

        if retries < 0:
            raise ValueError("Retries cannot be less than zero.")
        self.retries_remaining = retries

    @abc.abstractmethod
    def condition_name(self):
        """The name of the condition being waited for.

        Returns:
            str: the name of the "completed" condition
        """
        raise NotImplementedError('{}.condition_name'.format(self.__class__.__name__))

    @abc.abstractmethod
    def has_completed(self):
        """Check if the condition has occurred.

        Returns:
            True if the condition has occurred, and False otherwise.
        """
        raise NotImplementedError('{}.has_completed'.format(self.__class__.__name__))

    def pre_wait_action(self):
        """Perform some action before waiting.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.
        """

    def post_wait_action(self):
        """Perform some action after waiting.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.
        """

    def on_check_action(self):
        """Perform some action each polling cycle before checking.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.
        """

    def on_retry_action(self):
        """Perform some action between retries.

        If retries is set to zero for a Waiter instance, this
        function will never be called.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.
        """

    def wait_for_completion(self):
        """Wait for the condition to be achieved or for timeout.

        Returns:
            bool: True if condition succeeded, False if timed out.
        """
        self.pre_wait_action()

        # Allow pre_wait_action() to set self.completed to prevent needless waiting.
        if self.completed:
            return True

        try:
            while not self.completed:
                start_time = time.monotonic()
                while time.monotonic() - start_time < self.timeout:
                    self.on_check_action()

                    # Store value in case we want to use it in post_wait_action.
                    self.completed = self.has_completed()

                    if self.completed:
                        break

                    time.sleep(self.poll_interval)

                if not self.completed:
                    LOGGER.error('Waiting for condition "%s" timed out after %d seconds',
                                 self.condition_name(), self.timeout)

                    if self.retries_remaining:
                        LOGGER.info('Retrying waiting for condition "%s". (%d %s remaining)',
                                    self.condition_name(), self.retries_remaining,
                                    inf.plural_noun('retry', self.retries_remaining))
                        self.retries_remaining -= 1
                        self.on_retry_action()
                    else:
                        # Waiting failed, and there are no more retries left.
                        break
        except WaitingFailure as err:
            self.failed = True
            LOGGER.error('Could not wait for condition "%s": %s', self.condition_name(), err)

        self.post_wait_action()

        return self.completed

    def wait_for_completion_async(self):
        """Begin waiting for the completion condition.

        This will spawn a new thread which will run Waiter.wait_for_completion
        in another thread, and will immediately yield control back to the
        calling thread. To clean up the thread, the method
        Waiter.wait_for_completion_await should be called.

        Returns:
            None
        """
        self._waiter_thread = Thread(target=self.wait_for_completion)
        self._waiter_thread.start()

    def wait_for_completion_await(self):
        """Clean up waiting thread.

        This will join the waiting thread. This expects the method
        Waiter.wait_for_completion_async to have been called previously.

        Returns:
            None.
        """
        if self._waiter_thread is None:
            raise RuntimeError('wait_for_completion_async must be called before '
                               'wait_for_completion_await.')
        self._waiter_thread.join()

    def is_waiting_async(self):
        """Check if this waiter is currently waiting asynchronously.

        If wait_for_completion_async() has been called and the waiter
        thread has not finished, this returns True. Otherwise, this
        returns False.
        """
        return (self._waiter_thread is not None
                and self._waiter_thread.is_alive())

    def __enter__(self):
        self.wait_for_completion_async()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.wait_for_completion_await()


class SimultaneousWaiter(Waiter):
    """Waits for multiple conditions concurrently.

    This class can be used to synthesize multiple waiters into a
    single waiter; this essentially combines multiple awaited
    conditions with a logical "and", and waits for the combined
    conditions concurrently.
    """

    def __init__(self, waiter_classes, timeout, poll_interval=1, **kwargs):
        """Construct a new SimultaneousWaiter.

        Args:
            waiter_classes ([type]): classes of Waiters to wait for.
            timeout (int): timeout waiting for all conditions.
            poll_interval (int): the interval, in seconds, at which to
               poll for completion.
        """
        self._subwaiters = []
        for WaiterClass in waiter_classes:
            if not issubclass(WaiterClass, Waiter):
                raise TypeError(f'All classes must be subclasses of Waiter. '
                                '({WaiterClass.__name__})')
            self._subwaiters.append(WaiterClass(timeout, poll_interval=poll_interval))

        super().__init__(timeout, poll_interval=poll_interval)

    def condition_name(self):
        conditions = ', '.join(waiter.condition_name() for waiter in self._subwaiters)
        return f"Simultaneous conditions: {conditions}"

    def pre_wait_action(self):
        for waiter in self._subwaiters:
            waiter.wait_for_completion_async()

    def has_completed(self):
        return all(waiter.completed for waiter in self._subwaiters)

    def post_wait_action(self):
        for waiter in self._subwaiters:
            waiter.wait_for_completion_await()


class GroupWaiter(Waiter):
    """Waits for a all members of some group to reach some state.

    Attributes:
        members (set): a set of members of an arbitrary type to wait for.
        timeout (int): the timeout, in seconds, for the wait operation
        poll_interval (int): the interval, in seconds, between polls for
            completion.
        retries (int): the number of times waiting may be retried. By default,
            this is 0, meaning the wait will only occur once.
        failed (set): contains members which cannot be waited for, or
            which it is known will never complete.
    """

    def __init__(self, members, timeout, poll_interval=1):
        self.members = set(members)
        self.pending = set(self.members)

        super().__init__(timeout, poll_interval)

    @abc.abstractmethod
    def member_has_completed(self, member):
        """Check whether or not a given member has completed.

        Args:
            member: which member to check.

        Returns:
            True if completed, False if not.
        """
        raise NotImplementedError('{}.member_has_completed'.format(self.__class__.__name__))

    def has_completed(self):
        """Check if every member has completed.

        Args: None.
        Returns: True if every member has reached its completed state,
            and False otherwise.
        """
        return all(self.member_has_completed(member)
                   for member in self.members)

    def wait_for_completion(self):
        """Wait until all members have completed, or timeout is reached.

        Returns:
            set: A set of members which did not complete if the timeout was
                reached, or the empty set if all members complete.
        """
        self.pre_wait_action()

        start_time = time.monotonic()

        # Ensure we set this to a set of all members before starting to wait
        # because children classes may set `self.members` after `__init__`.
        self.pending = set(self.members)

        while self.pending and time.monotonic() - start_time < self.timeout:
            completed = set()
            failed = set()

            self.on_check_action()
            for member in self.pending:
                try:
                    if self.member_has_completed(member):
                        completed.add(member)
                except WaitingFailure:
                    failed.add(member)

            self.pending -= (completed | failed)

            time.sleep(self.poll_interval)

        # At this point we've either completed all members or there
        # are some still pending which have timed out.
        if self.pending:
            LOGGER.error('Waiting for condition "%s" timed out after %d seconds',
                         self.condition_name(), self.timeout)

        self.post_wait_action()
        return self.pending
