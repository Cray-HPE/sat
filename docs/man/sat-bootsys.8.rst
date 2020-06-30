=============
 SAT-BOOTSYS
=============

-----------------------------------------------------
Shut down or boot the entire system gracefully.
-----------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **bootsys** ACTION [options]

DESCRIPTION
===========
The bootsys command boots or shuts down the entire system, including the compute
nodes, user access nodes, and non-compute nodes running the management software.

The shutdown action is currently only partially implemented. It automates the
process of checking for any active sessions across multiple different services
in the system, including the Boot Orchestration Service (BOS), the Configuration
Framework Service (CFS), the Compute Rolling Upgrade Service (CRUS), the
Firmware Action Service (FAS) or the Firmware Update Service (FUS), and the Node
Memory Dump (NMD) service. If any active sessions are found, it will print
information about those sessions and exit with exit code 1. If it does not find
any active sessions, it will print messages to that effect and exit with exit
code 0. In the future, the command will continue with the remainder of the
shutdown procedure.

The boot action is not currently implemented and will exit with a non-zero exit
code and an error message.

ARGUMENTS
=========

**ACTION**
        Specify the action. This should be either ``shutdown`` or ``boot``. The
        ``shutdown`` action is only partially implemented, and the ``boot``
        operation is not implemented yet.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat bootsys'.

SHUTDOWN OPTIONS
----------------
These options apply to the ``shutdown`` action.

**-i, --ignore-failures**
        Same as setting --ignore-pod-failures and --ignore-service-failures.

**--ignore-pod-failures**
        Disregard any failures associated with storing pod state while
        shutting down.

**--ignore-service-failures**
        If specified, do not fail to shut down if failures are encountered while
        querying services for active sessions. This will still log warnings
        about these failures, but it will continue with the shutdown. Currently,
        there are no additional steps implemented, so it doesn't make much
        difference.

**--pod-state-file**
        Specify a custom file to write pod-state. Default is
        /var/sat/podstates/pod-state.json.


EXAMPLES
========

Shut down the entire system:

::

        # sat bootsys shutdown

Shut down the entire system, ignoring any failures encountered while querying
services for active sessions:

::

        # sat bootsys shutdown --ignore-service-failures

SEE ALSO
========

sat(8)

.. include:: _notice.rst
