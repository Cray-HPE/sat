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

from sat.report import Report

LOGGER = logging.getLogger(__file__)


class GroupWaiter(metaclass=abc.ABCMeta):
    """Waits for a all members of some group to reach some state.

    Fields:
        members (set): a set of members of an arbitrary type to wait for.
        timeout (int): the interval after which the wait operation will timeout.
        poll_interval (int): the interval, in seconds, between polls for
            completion.
    """

    def __init__(self, members, timeout, poll_interval=1):
        self.members = set(members)

        self.timeout = timeout
        self.poll_interval = poll_interval

    @abc.abstractmethod
    def member_has_completed(self, member):
        """Check whether or not a given member has completed.

        Args:
            member: which member to check.

        Returns:
            True if completed, False if not.
        """
        raise NotImplementedError('{}.member_has_completed'.format(self.__class__.__name__))

    @abc.abstractmethod
    def condition_name(self):
        """The name of the condition being waited for.

        Returns: (str) the name of the "completed" condition
        """
        raise NotImplementedError('{}.task_name'.format(self.__class__.__name__))

    def pre_wait_action(self):
        """Perform some action before waiting.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.

        Args: None.
        Returns: None.
        """

    def post_wait_action(self):
        """Perform some action after waiting.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.

        Args: None.
        Returns: None.
        """

    def on_check_action(self):
        """Perform some action each polling cycle before checking.

        The default implementation does nothing. Implement custom
        behaviors by overriding this method.

        Args: None.
        Returns: None.
        """

    def wait_for_completion(self):
        """Wait until all members have completed, or timeout is reached."""
        self.pre_wait_action()

        start_time = time.monotonic()
        self.pending = set(self.members)

        while self.pending and time.monotonic() - start_time < self.timeout:
            completed = set()
            self.on_check_action()
            for member in self.pending:
                if self.member_has_completed(member):
                    completed.add(member)

            self.pending -= completed

            time.sleep(self.poll_interval)

        self.post_wait_action()

        # At this point we've either completed all members or there
        # are some still pending which have timed out.
        if self.pending:
            LOGGER.error('Waiting for condition "%s" timed out after %d seconds',
                         self.condition_name(), self.timeout)

        return self.pending

    def wait_for_completion_async(self):
        """Begin waiting for the completion condition.

        This will spawn a new thread which will run
        GroupWaiter.wait_for_completion in another thread, and will
        immediately yield control back to the calling thread. To clean
        up the thread, the method
        GroupWaiter.wait_for_completion_await should be called.

        Args: None.
        Returns: None.
        """
        self.waiter_thread = Thread(target=self.wait_for_completion)
        self.waiter_thread.start()

    def wait_for_completion_await(self):
        """Clean up waiting thread and return pending members.

        This will join the thread and return the still-pending members
        after the timeout (i.e., the return value from
        GroupWaiter.wait_for_completion).

        Note: this will fail if wait_for_completion_async was not
        called previously.

        Args: None.
        Returns: set of members which have not completed.

        """
        self.waiter_thread.join()
        return self.pending

    def __enter__(self):
        self.wait_for_completion_async()
        return self

    def __exit__(self, exc_type, exc_value, exc_tb):
        self.wait_for_completion_await()
