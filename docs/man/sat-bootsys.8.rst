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

SHUTDOWN AND BOOT OPTIONS
-------------------------
These options apply to both the ``shutdown`` and ``boot`` actions.

**--stage** *STAGE*
        The stage of the boot or shutdown to execute. See ``--list-stages``
        to see the list of stages available for each action.

**--list-stages**
        List the stages that can be run for the given action.

**--cle-bos-template** *CLE_BOS_TEMPLATE*
        The name of the BOS session template for shutdown or boot of CLE compute
        nodes. Defaults to a template matching the pattern "cle-X.Y.X" where
        "X", "Y", and "Z" are integer version numbers. This overrides the option
        ``bootsys.cle_bos_template`` in the config file.

**--uan-bos-template** *UAN_BOS_TEMPLATE*
        The name of the BOS session template for shutdown or boot of user
        access nodes (UANs). Defaults to "uan". If the empty string is
        specified, no UAN shutdown will be performed. This overrides the option
        ``bootsys.uan_bos_template`` in the config file.

SHUTDOWN TIMEOUT OPTIONS
------------------------

These options set the timeouts of various parts of the stages of the
``shutdown`` action.

**--capmc-timeout** *CAPMC_TIMEOUT*
        Timeout, in seconds, to wait until components reach
        powered off state after they are shutdown with CAPMC.
        Defaults to 120. Overrides the option
        bootsys.capmc_timeout in the config file.

**--ipmi-timeout** *IPMI_TIMEOUT*
        Timeout, in seconds, to wait until management NCNs
        reach the desired power state after IPMI power
        commands are issued. Defaults to 60. Overrides the
        option bootsys.ipmi_timeout in the config file.

**--bgp-timeout** *BGP_TIMEOUT*
        Timeout, in seconds, to wait until BGP routes report
        that they are established on management switches.
        Defaults to 600. Overrides the option
        bootsys.bgp_timeout in the config file.

**--bos-shutdown-timeout** *BOS_SHUTDOWN_TIMEOUT*
        Timeout, in seconds, to wait until compute and
        application nodes have completed their BOS shutdown.
        Defaults to 600. Overrides the option
        bootsys.bos_shutdown_timeout in the config file.

**--ncn-shutdown-timeout** *NCN_SHUTDOWN_TIMEOUT*
        Timeout, in seconds, to wait until management NCNs
        have completed a graceful shutdown and have reached the
        powered off state according to IMPI. Defaults to 300.
        Overrides the option bootsys.ncn_shutdown_timeout in
        the config file.

BOOT TIMEOUT OPTIONS
--------------------

These options set the timeouts of various parts of the stages of the
``boot`` action.

**--discovery-timeout** *DISCOVERY_TIMEOUT*
        Timeout, in seconds, to wait until node controllers
        (NodeBMCs) reach the powered on state after the HMS
        Discovery cronjob is resumed. Defaults to 600.
        Overrides the option bootsys.discovery_timeout in the
        config file.
**--ipmi-timeout** *IPMI_TIMEOUT*
        Timeout, in seconds, to wait until management NCNs
        reach the desired power state after IPMI power
        commands are issued. Defaults to 60. Overrides the
        option bootsys.ipmi_timeout in the config file.
**--ncn-boot-timeout** *NCN_BOOT_TIMEOUT*
        Timeout, in seconds, to wait until management nodes
        are reachable via SSH after boot. Defaults to 300.
        Overrides the option bootsys.ncn_boot_timeout in the
        config file.
**--k8s-timeout** *K8S_TIMEOUT*
        Timeout, in seconds, to wait until Kubernetes pods
        have returned to their pre-shutdown state. Defaults to
        600. Overrides the option bootsys.k8s_timeout in the
        config file.
**--ceph-timeout** *CEPH_TIMEOUT*
        Timeout, in seconds, to wait until ceph has returned
        to a healthy state. Defaults to 600. Overrides the
        option bootsys.ceph_timeout in the config file.
**--bgp-timeout** *BGP_TIMEOUT*
        Timeout, in seconds, to wait until BGP routes report
        that they are established on management switches.
        Defaults to 600. Overrides the option
        bootsys.bgp_timeout in the config file.
**--hsn-timeout** *HSN_TIMEOUT*
        Timeout, in seconds, to wait until the high-speed
        network (HSN) has returned to its pre-shutdown state.
        Defaults to 300. Overrides the option
        bootsys.hsn_timeout in the config file.
**--bos-boot-timeout** *BOS_BOOT_TIMEOUT*
        Timeout, in seconds, to wait until compute and
        application nodes have completed their BOS boot.
        Defaults to 900. Overrides the option
        bootsys.bos_boot_timeout in the config file.


EXAMPLES
========

List the stages available under the shutdown action:

::

        # sat bootsys shutdown --list-stages

List the stages available under the boot action:

::

        # sat bootsys boot --list-stages

Capture the state of the system prior to beginning the shutdown as part of the
system shutdown procedure:

::

        # sat bootsys shutdown --stage capture-state

Run the service activity checks during the beginning of the system shutdown
procedure:

::

        # sat bootsys shutdown --stage session-checks

Shut down the computes and UANs as part of the system shutdown procedure, using
a non-default timeout of 5 minutes for the BOS shutdown to complete:

::

        # sat bootsys shutdown --stage bos-operations --bos-shutdown-timeout 300

Shut down and power off the management NCNs (other than ncn-w001), using
non-default timeouts of 10 minutes for the NCN graceful shutdown and 2 minutes
for the IPMI power off of those NCNs:

::

        # sat bootsys shutdown --stage ncn-power --ncn-shutdown-timeout 600 --ipmi-timeout 120

Boot the computes and UANs as part of the system boot procedure:

::

        # sat bootsys boot --stage bos-operations


SEE ALSO
========

sat(8)

.. include:: _notice.rst
