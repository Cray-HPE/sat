=============
 SAT-BOOTSYS
=============

-------------------------------------------------------
Perform boot, shutdown, or reboot actions on the system
-------------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020-2023 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **bootsys** ACTION [options]

DESCRIPTION
===========

The bootsys command can be used to boot or shut down part or all of the system,
including compute nodes, user access nodes, and non-compute nodes running the
management software.

SHUTDOWN ACTION
---------------

The shutdown action consists of the following stages. Each stage automates a
specific portion of the system shutdown procedure.

In the ``capture-state`` stage, ``sat bootsys`` saves the state of all
Kubernetes pods to a file in an S3 bucket. This file can be used when the system
is booted to verify all pods are in the states they were in before the shutdown.
The S3 bucket must be configured in the ``s3`` section of the SAT configuration
file.

In the ``session-checks`` stage, it checks for any active sessions across
multiple different services in the system, including the Boot Orchestration
Service (BOS), the Configuration Framework Service (CFS), the Compute Rolling
Upgrade Service (CRUS), the Firmware Action Service (FAS), the Node Memory Dump
(NMD) service, and the System Dump Utility (SDU). If any active sessions are
found, it will print information about those sessions and exit with exit code 1.
If it does not find any active sessions, it will print messages to that effect
and proceed with the next stage of the shutdown.

In the ``bos-operations`` stage, it uses the Boot Orchestration Service (BOS)
to shut down the nodes specified by one or more BOS session templates, for
instance the compute nodes and User Access Nodes (UANs). It attempts to check
whether the nodes are already in an "Off" state in the Hardware State Manager
before attempting to shut them down with BOS.

In the ``cabinet-power`` stage, it suspends the ``hms-discovery`` Kubernetes
cron job and uses the Cray Advanced Platform Monitoring and Control (CAPMC)
service to power off all liquid-cooled and air-cooled compute node cabinet and
non-management NCN cabinets. It then waits for all components in those cabinets
to reach the power "Off" state.

In the ``platform-services`` stage, it stops all management services on the
non-compute nodes (NCNs). This includes backing up and stopping the etcd
cluster, stopping the kubelet service on each node, freezing ceph, and stopping
all containers running in containerd.

In the ``ncn-power`` stage, it shuts down Linux on all management NCNs
simultaneously, powers them off, and creates screen sessions to monitor console
logs using ``ipmitool``. Once this has completed, and it is safe to shutdown
and power off ncn-m001 where this command was run.

BOOT ACTION
-----------

The boot action consists of the following stages. Similar to the shutdown
action, each stage automates a specific portion of the system boot procedure.

In the ``ncn-power`` stage, ``sat bootsys`` powers on all mangagement NCNs in
stages. It first boots the master nodes and waits for them to become accessible
over the network, and then repeats for the storage nodes, then the worker
nodes.

In the ``platform-services`` stage, it ensures that containerd and etcd are are
running and enabled on all Kubernetes NCNs, then starts Ceph services, unfreezes
Ceph, and waits for Ceph to become healthy. After this, it starts and enables
kubelet on all Kubernetes NCNs.

In the ``k8s-check`` stage, it waits for the Kubernetes cluster to become
available and for the Kubernetes pods to become healthy. Specifically, it waits
for each pod that was running prior to shutdown to have a similarly-named pod
after boot, and any new pods are expected to be in the "Running" or "Succeeded"
states. Note that this stage may not work as expected since Kubernetes will
re-create the pods with arbitrary names which may not match those saved prior
to shutdown.

In the ``cabinet-power`` stage, it enables the ``hms-discovery`` Kubernetes cron
job and uses the Cray Advanced Platform Monitoring and Control (CAPMC) service
to power on all liquid-cooled and air-cooled compute node cabinets and
non-management NCN cabinets. It then waits for all components in those cabinets
to reach the power "On" state.

In the ``bos-operations`` stage, it uses the Boot Orchestration Service (BOS)
to boot the nodes specified by one or more BOS session templates, for instance
the compute nodes and User Access Nodes (UANs). It attempts to check whether
the nodes are already in an "On" state in the Hardware State Manager before
attempting to shut them down with BOS.

REBOOT ACTION
-------------
The reboot action only supports the ``bos-operations`` stage.
In the ``bos-operations`` stage, ``sat bootsys`` uses the Boot Orchestration Service (BOS)
to reboot the nodes specified by one or more BOS session templates, for instance
the compute nodes and User Access Nodes (UANs). Regardless of node state (on, off),
(BOS) will perform a ``shutdown`` followed by a ``boot``. 


ARGUMENTS
=========

**ACTION**
        Specify the action. This should be either ``shutdown``, ``boot``, or ``reboot``.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat bootsys'.

SHUTDOWN AND BOOT OPTIONS
-------------------------
These options apply to both the ``shutdown`` and ``boot`` actions.

**--disruptive**
        Certain actions can be disruptive to the system, and so require
        interactive user confirmation to proceed. Using the ``--disruptive``
        option skips any interactive user prompts. If ``--disruptive`` is used
        with a stage which is not disruptive, it is ignored. The following
        shutdown stages are considered disruptive:

        * bos-operations
        * cabinet-power
        * platform-services
        * ncn-power

**--stage** *STAGE*
        The stage of the boot or shutdown to execute. See ``--list-stages``
        to see the list of stages available for each action.

**--list-stages**
        List the stages that can be run for the given action.

**--bos-templates** *BOS_TEMPLATES*
        A comma-separated list of BOS session templates for shutdown or boot of
        COS compute nodes or User Access Nodes (UANs). This parameter takes
        precedence over ``--cle-bos-template`` and ``--uan-bos-template``
        (below). This overrides the option ``bootsys.bos_templates`` in the
        config file.

**--bos-version BOS_VERSION**
        The version of the BOS API to use when launching BOS sessions.

**--cle-bos-template** *CLE_BOS_TEMPLATE*
        The name of the BOS session template for shutdown or boot of
        COS (formerly known as CLE) compute nodes. If not specified, no
        COS BOS template will be used. This overrides the option
        ``bootsys.cle_bos_template`` in the config file. This option is
        deprecated in favor of ``--bos-templates`` (above). If
        ``--bos-templates`` or its configuration-file equivalent is specified,
        then this option will be ignored.

**--uan-bos-template** *UAN_BOS_TEMPLATE*
        The name of the BOS session template for shutdown or boot of user
        access nodes (UANs). If not specified, no UAN BOS template will be
        used. This overrides the option ``bootsys.uan_bos_template`` in the
        config file. This option is deprecated in favor of ``--bos-templates``
        (above). If ``--bos-templates`` or its configuration-file equivalent is
        specified, then this option will be ignored.

**--bos-limit** *XNAMES*
        A comma-separated list of xnames, node groups, and roles which should be
        included in the shutdown or boot action. If not specified, all
        components in the specified BOS session template's boot sets will be
        used.

**--recursive**
        If specified, then the xnames listed in the limit string for
        ``--bos-limit`` will be expanded recursively into their constituent node
        xnames. For instance, if a slot xname is given as part of
        ``--bos-limit``, then that xname will be expanded into the node xnames
        for all nodes in that slot.

**--staged-session**
        If specified, then create a "staged" BOS session. A staged session
        differs from a normal BOS session in that a staged session does not
        automatically change the state of any components targeted by the session
        templates. Instead, a staged session will update components'
        "staged_state", which can later be applied through the command
        'cray bos v2 applystaged create', or through an API call to BOS. When
        using this option, the command will not wait for completion of BOS
        sessions. This option cannot be used with BOS v1.

**--excluded-ncns** *EXCLUDED_NCNS*
        A comma-separated list of NCN hostnames that should be excluded from the
        shutdown and boot operations. This option only applies to the ncn-power
        and platform-services stages. This option should only be used to exclude
        NCNs if they are inaccessible and already outside of the Kubernetes
        cluster. Using this option in other circumstances will cause serious
        problems when cleanly shutting down or booting the system.

        Note that ncn-m001 will always be excluded from the ncn-power stage
        because ncn-m001 is the node on which you are assumed to be running the
        command.

        The ncn-power and platform-services stages will both prompt the user to
        ensure that the correct list of NCNs are being targeted. NCN hostnames
        specified here that do not match any of the recognized NCN hostnames on
        the system are silently ignored.

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
        powered off state according to IPMI. Defaults to 300.
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
