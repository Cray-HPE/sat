============
 SAT-STATUS
============

----------------
Show node status
----------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
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

**-x, --xnames**
        Selects nodes to report from a comma-separated list of xnames, or
        a single xname. The xname values are case insensitive, and leading
        zeros from the integer parts will be removed before matching. May be
        used with **--nids**.

.. include:: _sat-format-opts.rst

EXAMPLES
========

Sample Output
-------------

::

  # no filter
  $ sat status
  +----------------+------+-------+------+---------+------+---------+----------+
  | xname          | NID  | State | Flag | Enabled | Arch | Role    | Net Type |
  +----------------+------+-------+------+---------+------+---------+----------+
  | x3000c0s19b1n0 | 1    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x3000c0s19b2n0 | 2    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x3000c0s19b3n0 | 3    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x3000c0s19b4n0 | 4    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x5000c1s0b0n0  | 1000 | Ready | OK   | True    | X86  | Compute | Sling    |
  | x5000c1s0b0n1  | 1001 | Ready | OK   | True    | X86  | Compute | Sling    |
  +----------------+------+-------+------+---------+------+---------+----------+

  $ sat status --filter nid=1
  +----------------+------+-------+------+---------+------+---------+----------+
  | xname          | NID  | State | Flag | Enabled | Arch | Role    | Net Type |
  +----------------+------+-------+------+---------+------+---------+----------+
  | x3000c0s19b1n0 | 1    | Ready | OK   | True    | X86  | Compute | Sling    |
  +----------------+------+-------+------+---------+------+---------+----------+

  $ sat status --filter xname=x3000c0s19b4n0
  +----------------+------+-------+------+---------+------+---------+----------+
  | xname          | NID  | State | Flag | Enabled | Arch | Role    | Net Type |
  +----------------+------+-------+------+---------+------+---------+----------+
  | x3000c0s19b4n0 | 4    | Ready | OK   | True    | X86  | Compute | Sling    |
  +----------------+------+-------+------+---------+------+---------+----------+

  # filters are case-insensitive as well
  $ sat status --filter role=compute
  +----------------+------+-------+------+---------+------+---------+----------+
  | xname          | NID  | State | Flag | Enabled | Arch | Role    | Net Type |
  +----------------+------+-------+------+---------+------+---------+----------+
  | x3000c0s19b1n0 | 1    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x3000c0s19b2n0 | 2    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x3000c0s19b3n0 | 3    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x3000c0s19b4n0 | 4    | Ready | OK   | True    | X86  | Compute | Sling    |
  | x5000c1s0b0n0  | 1000 | Ready | OK   | True    | X86  | Compute | Sling    |
  | x5000c1s0b0n1  | 1001 | Ready | OK   | True    | X86  | Compute | Sling    |
  +----------------+------+-------+------+---------+------+---------+----------+

Possible Values
---------------

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
