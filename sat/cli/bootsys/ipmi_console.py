"""
IPMI console logging support.

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

import logging
from subprocess import run, CalledProcessError, DEVNULL, PIPE


LOGGER = logging.getLogger(__name__)


class IPMIConsoleLogger:
    """A context manager that starts/stops IPMI console logging when entering/exiting."""

    def __init__(self, hosts, always_cleanup=False):
        """Create an IPMIConsoleLogger.

        Args:
            hosts: ([str]): A list of hostnames for which to start console
                logging (not BMC hostnames).
            always_cleanup (bool): if True, stop console logging even when
                handling an exception.
        """
        self.hosts = hosts
        self.always_cleanup = always_cleanup

    def __enter__(self):
        """Start console logging using /root/bin/ipmi_console_start.sh"""
        LOGGER.info(f'Starting console logging on {",".join(self.hosts)}.')
        for host in self.hosts:
            bmc = f'{host}-mgmt'
            cmd = ['/root/bin/ipmi_console_start.sh', bmc]
            try:
                # SAT-621: can't capture stderr due to issue with underlying process
                run(cmd, check=True, stdout=PIPE, stderr=DEVNULL)
            except OSError as err:
                LOGGER.warning(f'Failed to start console logging for {host}: {err}')
            except CalledProcessError as err:
                LOGGER.warning(f'Failed to start console logging for {host}.  Stdout: "{err.stdout}"')

    def __exit__(self, exc_type, exc_value, exc_tb):
        """Stop console logging using /root/bin/ipmi_console_stop.sh"""
        # Only stop console logging if not handling an exception.  That way, if
        # 'sat bootsys' fails console logging will continue so that the user
        # may debug or investigate.
        # Note: a Ctrl-C will still send SIGINT to the underlying
        # ipmitool processes (SAT-622).
        if exc_type is None or self.always_cleanup:
            LOGGER.info(f'Stopping console logging on {",".join(self.hosts)}.')
            cmd = ['/root/bin/ipmi_console_stop.sh']
            try:
                run(cmd, check=True, stdout=PIPE, stderr=PIPE)
            except OSError as err:
                LOGGER.warning(f'Failed to stop console logging: {err}')
            except CalledProcessError as err:
                LOGGER.warning(f'Failed to stop console logging.  Stdout: "{err.stdout}".  Stderr: "{err.stderr}"')
