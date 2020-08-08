"""
Common code for waiting for a condition.

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

import abc
import logging
from threading import Thread
import time

LOGGER = logging.getLogger(__file__)


class Waiter(metaclass=abc.ABCMeta):
    """Waits for a single condition to occur.

    Attributes:
        timeout (int): the timeout, in seconds, for the wait operation
        poll_interval (int): the interval, in seconds, between polls for
            completion.
        completed (bool): True if the condition has been met, False otherwise.
    """
    def __init__(self, timeout, poll_interval=1):
        self.timeout = timeout
        self.poll_interval = poll_interval
        self.completed = False
        self._waiter_thread = None

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

    def wait_for_completion(self):
        """Wait for the condition to be achieved or for timeout.

        Returns:
            bool: True if condition succeeded, False if timed out.
        """
        self.pre_wait_action()

        start_time = time.monotonic()

        while time.monotonic() - start_time < self.timeout:
            # Store value in case we want to use it in post_wait_action.
            self.completed = self.has_completed()
            if self.completed:
                break

            time.sleep(self.poll_interval)

        self.post_wait_action()

        if not self.completed:
            LOGGER.error('Waiting for condition "%s" timed out after %d seconds',
                         self.condition_name(), self.timeout)

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

    def __enter__(self):
        self.wait_for_completion_async()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.wait_for_completion_await()


class GroupWaiter(Waiter):
    """Waits for a all members of some group to reach some state.

    Attributes:
        members (set): a set of members of an arbitrary type to wait for.
        timeout (int): the timeout, in seconds, for the wait operation
        poll_interval (int): the interval, in seconds, between polls for
            completion.
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

    def on_check_action(self):
        """Perform some action each polling cycle before checking.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.

        Args: None.
        Returns: None.
        """

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

        while self.pending and time.monotonic() - start_time < self.timeout:
            completed = set()
            self.on_check_action()
            for member in self.pending:
                if self.member_has_completed(member):
                    completed.add(member)

            self.pending -= completed

            time.sleep(self.poll_interval)

        # At this point we've either completed all members or there
        # are some still pending which have timed out.
        if self.pending:
            LOGGER.error('Waiting for condition "%s" timed out after %d seconds',
                         self.condition_name(), self.timeout)

        self.post_wait_action()
        return self.pending
