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

SHUTDOWN ACTION
---------------

The shutdown action consists of the following phases, some of which are not yet
implemented.

In the first phase, it saves the state of all kubernetes pods to a file. This
file will be used when the system is booted to verify all pods are in the states
they were in before the shutdown.

In the second phase, it checks for any active sessions across multiple different
services in the system, including the Boot Orchestration Service (BOS), the
Configuration Framework Service (CFS), the Compute Rolling Upgrade Service
(CRUS), the Firmware Action Service (FAS) or the Firmware Update Service (FUS),
and the Node Memory Dump (NMD) service. If any active sessions are found, it
will print information about those sessions and exit with exit code 1. If it
does not find any active sessions, it will print messages to that effect and
proceed with the next phase of the shutdown.

In the third phase, it uses the Boot Orchestration Service (BOS) to shut down
the compute nodes and User Access Nodes (UANs). It attempts to check whether the
nodes are already in an "Off" state in the Hardware State Manager before
attempting to shut them down with BOS. If it encounters an error while checking
on node state, the shutdown operation will terminate by default, but this
behavior can be changed with the ``--state-check-fail-action`` option. Once the
BOS shutdowns have completed, it will proceed to the next phase of the shutdown.

The remaining phases are described below, but they are not yet implemented.

In the fourth phase, it stops all management services on the non-compute nodes
(NCNs). This includes backing up and stopping the etcd cluster, stopping the
kubelet service on each node, freezing ceph, and stopping all containers running
in containerd. This ansible playbook is known to experience a problem that
results in it hanging when stopping containers in containerd, so if this occurs,
a workaround will automatically be executed that kills hanging processes on each
node where it is necessary. Once the playbook has completed, it will move on to
the next phase.

In the final phase, it will shut down linux on all NCNs, and it will power them
off using IPMI. Once this has completed, the command will return, and it wil be
safe to shutdown and power off ncn-w001 where this command was run.

BOOT ACTION
-----------

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

**--state-check-fail-action**
        Action to take if a failure occurs when checking whether a BOS session
        template needs an operation applied based on current node state in HSM.
        The choices and their meanings are as follows:

        ::

                abort: Abort the entire shutdown operation. This is the default.
                skip: Skip performing an operation against the session template(s).
                prompt: Prompt user whether to abort, skip, or force.
                force: Do the operation against this session template anyway.

EXAMPLES
========

Shut down the entire system:

::

        # sat bootsys shutdown

Shut down the entire system, ignoring any failures encountered while querying
services for active sessions:

::

        # sat bootsys shutdown --ignore-service-failures

Shut down the entire system, and force a shutdown operation to be performed
against the session template(s) even if we fail to query the current state of
the nodes included in the boot sets of the session template(s):

::

        # sat bootsys shutdown --state-check-fail-action force

SEE ALSO
========

sat(8)

.. include:: _notice.rst
