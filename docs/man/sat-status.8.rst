============
 SAT-STATUS
============

----------------
Show node status
----------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
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
        Specify the a list of types to query. The default is for 'Node' only. 
        The types that may be specified are...

            all, Chassis, ChassisBMC, ComputeModule, HSNBoard, Node, NodeBMC,
            NodeEnclosure, RouterBMC, RouterModule

        If "all" is specified, then all types will be queried.

.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Show status of all nodes in the system:

::

  # sat status
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+
  | xname          | Type | NID | State | Flag | Enabled | Arch | Class | Role       | Net Type |
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+
  | x3000c0s1b0n0  | Node | 100 | On    | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s3b0n0  | Node | 101 | On    | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s5b0n0  | Node | 102 | On    | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s9b0n0  | Node | 104 | Ready | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s11b0n0 | Node | 105 | Ready | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s13b0n0 | Node | 106 | On    | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s15b0n0 | Node | 107 | On    | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s17b0n0 | Node | 108 | On    | OK   | True    | X86  | River | Management | Sling    |
  | x3000c0s19b1n0 | Node | 1   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  | x3000c0s19b2n0 | Node | 2   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  | x3000c0s19b3n0 | Node | 3   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  | x3000c0s19b4n0 | Node | 4   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+


Show status of nid 1:

::

  # sat status --filter nid=1
  +----------------+------+-----+-------+------+---------+------+-------+---------+----------+
  | xname          | Type | NID | State | Flag | Enabled | Arch | Class | Role    | Net Type |
  +----------------+------+-----+-------+------+---------+------+-------+---------+----------+
  | x3000c0s19b1n0 | Node | 1   | Ready | OK   | True    | X86  | River | Compute | Sling    |
  +----------------+------+-----+-------+------+---------+------+-------+---------+----------+

Show status of the node with xname x3000c0s1b0n0:

::

  # sat status --filter xname=x3000c0s1b0n0
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+
  | xname          | Type | NID | State | Flag | Enabled | Arch | Class | Role       | Net Type |
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+
  | x3000c0s1b0n0  | Node | 100 | On    | OK   | True    | X86  | River | Management | Sling    |
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+

Filters are case-insensitive as well:

::

  # sat status --filter role=compute
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+
  | xname          | Type | NID | State | Flag | Enabled | Arch | Class | Role       | Net Type |
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+
  | x3000c0s19b1n0 | Node | 1   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  | x3000c0s19b2n0 | Node | 2   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  | x3000c0s19b3n0 | Node | 3   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  | x3000c0s19b4n0 | Node | 4   | Ready | OK   | True    | X86  | River | Compute    | Sling    |
  +----------------+------+-------+-----+------+---------+------+-------+------------+----------+

Query all types of components:

::

  # sat status --types all
  +----------------+---------------+---------+-----------+---------+---------+------+----------+-------------+----------+
  | xname          | Type          | NID     | State     | Flag    | Enabled | Arch | Class    | Role        | Net Type |
  +----------------+---------------+---------+-----------+---------+---------+------+----------+-------------+----------+
  | x3000c0r24b0   | RouterBMC     | MISSING | Ready     | Warning | True    | X86  | River    | MISSING     | Sling    |
  | x3000c0r24e0   | HSNBoard      | MISSING | On        | OK      | True    | X86  | River    | MISSING     | Sling    |
  | x3000c0s1b0    | NodeBMC       | MISSING | Ready     | OK      | True    | X86  | River    | MISSING     | Sling    |
  | x3000c0s19e1   | NodeEnclosure | MISSING | On        | OK      | True    | X86  | River    | MISSING     | Sling    |
  | x3000c0s26b0n0 | Node          | 5000    | Ready     | OK      | True    | X86  | River    | Application | Sling    |
  | x5000c1        | Chassis       | MISSING | On        | Warning | True    | X86  | Mountain | MISSING     | Sling    |
  | x5000c1b0      | ChassisBMC    | MISSING | Ready     | Warning | True    | X86  | Mountain | MISSING     | Sling    |
  | x5000c1r5      | RouterModule  | MISSING | On        | OK      | True    | X86  | Mountain | MISSING     | Sling    |
  | x5000c1s0      | ComputeModule | MISSING | On        | OK      | True    | X86  | Mountain | MISSING     | Sling    |
  +----------------+---------------+---------+-----------+---------+---------+------+----------+-------------+----------+

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
