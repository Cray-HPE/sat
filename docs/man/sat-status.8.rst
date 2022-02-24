============
 SAT-STATUS
============

----------------
Show node status
----------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2022 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **status** [options]

DESCRIPTION
===========

The status subcommand reports the status of nodes in the system. Node status
is displayed in tabular format, with a row for each node, and columns
corresponding to the identities and conditions of the nodes.

OPTIONS
=======

These options must be specified after the subcommand.

**--types** *type [type]...*
        Specify a list of types to query. The default is for 'Node' only. 
        The types that may be specified are...

            all, Chassis, ChassisBMC, ComputeModule, HSNBoard, Node, NodeBMC,
            NodeEnclosure, RouterBMC, RouterModule

        If "all" is specified, then all types will be queried.

**--all-fields**
        Display all fields. This is the default behavior when no other
        --\*-fields options are specified.

**--hsm-fields**
        Only query and display information from HSM. The xname, Type, NID,
        State, Flag, Enabled, Arch, Class, Role, Subrole, and Net Type fields
        will be shown. May be combined with **--sls-fields** and
        **--config-fields**.

**--sls-fields**
        Only query and display information from SLS about node IDs. The xname
        and Aliases fields will be shown. May be combined with **--hsm-fields**
        and **--config-fields**.

**--cfs-fields**
        Only query and display information from CFS about node configuration
        status. The xname, Desired Config, Configuration Status, and Error
        Count fields will be shown. May be combined with **--hsm-fields** and
        **--sls-fields**.

.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Show status of all nodes in the system:

::

  # sat status
  +----------------+-----------+------+----------+---------+---------+---------+------+-------+-------------+---------+----------+---------------------+----------------------+-------------+
  | xname          | Aliases   | Type | NID      | State   | Flag    | Enabled | Arch | Class | Role        | Subrole | Net Type | Desired Config      | Configuration Status | Error Count |
  +----------------+-----------+------+----------+---------+---------+---------+------+-------+-------------+---------+----------+---------------------+----------------------+-------------+
  | x3000c0s1b0n0  | ncn-m001  | Node | 100001   | Ready   | OK      | True    | X86  | River | Management  | Master  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s3b0n0  | ncn-m002  | Node | 100002   | Ready   | OK      | True    | X86  | River | Management  | Master  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s5b0n0  | ncn-m003  | Node | 100003   | Ready   | Warning | True    | X86  | River | Management  | Master  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s7b0n0  | ncn-w001  | Node | 100004   | Ready   | OK      | True    | X86  | River | Management  | Worker  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s9b0n0  | ncn-w002  | Node | 100005   | Ready   | OK      | True    | X86  | River | Management  | Worker  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s11b0n0 | ncn-s001  | Node | 100006   | Ready   | OK      | True    | X86  | River | Management  | Storage | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s13b0n0 | ncn-s002  | Node | 100007   | Ready   | OK      | True    | X86  | River | Management  | Storage | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s15b0n0 | ncn-s003  | Node | 100008   | Ready   | Warning | True    | X86  | River | Management  | Storage | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s17b1n0 | nid000001 | Node | 1        | Ready   | Warning | True    | X86  | River | Compute     | None    | Sling    | cos-config-x.y      | configured           | 0           |
  | x3000c0s17b2n0 | nid000002 | Node | 2        | Ready   | OK      | True    | X86  | River | Compute     | None    | Sling    | cos-config-x.y      | configured           | 0           |
  | x3000c0s17b3n0 | nid000003 | Node | 3        | Ready   | OK      | True    | X86  | River | Compute     | None    | Sling    | cos-config-x.y      | configured           | 0           |
  | x3000c0s17b4n0 | nid000004 | Node | 4        | Ready   | Warning | True    | X86  | River | Compute     | None    | Sling    | cos-config-x.y      | configured           | 0           |
  | x3000c0s24b0n0 | ncn-w003  | Node | 100009   | Ready   | OK      | True    | X86  | River | Management  | Worker  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s26b0n0 | uan01     | Node | 49169216 | Standby | Alert   | True    | X86  | River | Application | UAN     | Sling    | uan-config-x.y      | configured           | 0           |
  +----------------+-----------+------+----------+---------+---------+---------+------+-------+-------------+---------+----------+---------------------+----------------------+-------------+

Show status of nid 1:

::

  # sat status --filter nid=1
  +----------------+-----------+------+-----+-------+---------+---------+------+-------+---------+---------+----------+---------------------+----------------------+-------------+
  | xname          | Aliases   | Type | NID | State | Flag    | Enabled | Arch | Class | Role    | Subrole | Net Type | Desired Config      | Configuration Status | Error Count |
  +----------------+-----------+------+-----+-------+---------+---------+------+-------+---------+---------+----------+---------------------+----------------------+-------------+
  | x3000c0s17b1n0 | nid000001 | Node | 1   | Ready | Warning | True    | X86  | River | Compute | None    | Sling    | cos-config-x.y      | configured           | 0           |
  +----------------+-----------+------+-----+-------+---------+---------+------+-------+---------+---------+----------+---------------------+----------------------+-------------+

Show status of the node with xname x3000c0s1b0n0:

::

  # sat status --filter xname=x3000c0s1b0n0
  +---------------+----------+------+--------+-------+------+---------+------+-------+------------+---------+----------+---------------------+----------------------+-------------+
  | xname         | Aliases  | Type | NID    | State | Flag | Enabled | Arch | Class | Role       | Subrole | Net Type | Desired Config      | Configuration Status | Error Count |
  +---------------+----------+------+--------+-------+------+---------+------+-------+------------+---------+----------+---------------------+----------------------+-------------+
  | x3000c0s1b0n0 | ncn-m001 | Node | 100001 | Ready | OK   | True    | X86  | River | Management | Master  | Sling    | ncn-personalization | configured           | 0           |
  +---------------+----------+------+--------+-------+------+---------+------+-------+------------+---------+----------+---------------------+----------------------+-------------+

Filters are case-insensitive as well:

::

  # sat status --filter role=compute
  +----------------+-----------+------+-----+-------+---------+---------+------+-------+---------+---------+----------+---------------------+----------------------+-------------+
  | xname          | Aliases   | Type | NID | State | Flag    | Enabled | Arch | Class | Role    | Subrole | Net Type | Desired Config      | Configuration Status | Error Count |
  +----------------+-----------+------+-----+-------+---------+---------+------+-------+---------+---------+----------+---------------------+----------------------+-------------+
  | x3000c0s17b1n0 | nid000001 | Node | 1   | Ready | Warning | True    | X86  | River | Compute | None    | Sling    | cos-config-x.y      | configured           | 0           |
  | x3000c0s17b2n0 | nid000002 | Node | 2   | Ready | OK      | True    | X86  | River | Compute | None    | Sling    | cos-config-x.y      | configured           | 0           |
  | x3000c0s17b3n0 | nid000003 | Node | 3   | Ready | OK      | True    | X86  | River | Compute | None    | Sling    | cos-config-x.y      | configured           | 0           |
  | x3000c0s17b4n0 | nid000004 | Node | 4   | Ready | Warning | True    | X86  | River | Compute | None    | Sling    | cos-config-x.y      | configured           | 0           |
  +----------------+-----------+------+-----+-------+---------+---------+------+-------+---------+---------+----------+---------------------+----------------------+-------------+

Query all types of components:

::

  # sat status --types all
  ################################################################################
  Node Status
  ################################################################################
  +----------------+-----------+----------+---------+-------+---------+------+-------+-------------+---------+----------+---------------------+----------------------+-------------+
  | xname          | Aliases   | NID      | State   | Flag  | Enabled | Arch | Class | Role        | Subrole | Net Type | Desired Config      | Configuration Status | Error Count |
  +----------------+-----------+----------+---------+-------+---------+------+-------+-------------+---------+----------+---------------------+----------------------+-------------+
  | x3000c0s1b0n0  | ncn-m001  | 100002   | Ready   | OK    | True    | X86  | River | Management  | Master  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s3b0n0  | ncn-m002  | 100003   | Ready   | OK    | True    | X86  | River | Management  | Master  | Sling    | ncn-personalization | configured           | 0           |
  | x3000c0s5b0n0  | ncn-m003  | 100004   | Ready   | OK    | True    | X86  | River | Management  | Master  | Sling    | ncn-personalization | configured           | 0           |
  ...

  ################################################################################
  NodeBMC Status
  ################################################################################
  +----------------+-------+------+---------+------+-------+----------+
  | xname          | State | Flag | Enabled | Arch | Class | Net Type |
  +----------------+-------+------+---------+------+-------+----------+
  | x3000c0s3b0    | Ready | OK   | True    | X86  | River | Sling    |
  | x3000c0s5b0    | Ready | OK   | True    | X86  | River | Sling    |
  | x3000c0s7b0    | Ready | OK   | True    | X86  | River | Sling    |

Possible Values
---------------

| *Type*
|
|   Chassis, ChassisBMC, ComputeModule, HSNBoard, Node, NodeBMC, NodeEnclosure, RouterBMC, RouterModule
| 
| *Flag*
|
|   OK, Warning, Alert
|
| *State*
|
|   Unknown
|    - Appears missing but has not been confirmed as empty.
|
|   Empty
|    - The location is not populated with a component.
|
|   Populated
|    - Present (not empty), but no further tracking can be or is being done.
|
|   Off
|    - Present but powered off.
|
|   On
|    - Powered on. If no heartbeat mechanism is available, its software state may be unknown.
|
|   Standby
|    - No longer Ready and presumed dead. It typically means the heartbeat has been lost (w/ alert).
|
|   Halt
|    - No longer Ready and halted. OS has been gracefully shutdown or panicked (w/ alert).
|
|   Ready
|    - Both On and Ready to provide its expected services, i.e. jobs.

SEE ALSO
========

sat(8)

.. include:: _notice.rst
