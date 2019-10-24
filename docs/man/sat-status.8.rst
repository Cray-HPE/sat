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

Sample Output
-------------

::

  +-------------+-----+---------+-------+---------+------+-------------+----------+
  |    xname    | NID |  State  |  Flag | Enabled | Arch |     Role    | Net Type |
  +-------------+-----+---------+-------+---------+------+-------------+----------+
  | x0c0s11b0n0 | 999 |  Ready  |   OK  |   True  | X86  | Application |  Sling   |
  | x0c0s13b0n0 | 998 | Standby | Alert |   True  | X86  | Application |  Sling   |
  | x0c0s21b0n0 |  4  |  Ready  |   OK  |   True  | X86  |   Compute   |  Sling   |
  | x0c0s24b0n0 |  3  |  Ready  |   OK  |   True  | X86  |   Compute   |  Sling   |
  | x0c0s26b0n0 |  2  |    On   |   OK  |   True  | X86  |   Compute   |  Sling   |
  | x0c0s28b0n0 |  1  |  Ready  |   OK  |   True  | X86  |   Compute   |  Sling   |
  +-------------+-----+---------+-------+---------+------+-------------+----------+

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

OPTIONS
=======

These options must be specified after the subcommand.

**-s, --sort-column**
        Sort by the selected column. The default is to sort by xname.
        May be specified by the (case insensitive) column, or by index
        (starting at 1). The column can be abbreviated if unambiguous.
        If an ambiguous abbreviation is given, the first matching column
        will be selected.
        Some columns may contain whitespace. If whitespace is necessary
        to unambiguously single out such a column, the whitespace may be
        included by wrapping the column name or abbreviation in quotes.

**-r, --reverse**
        Reverses the order of the nodes.

**-x, --xnames**
        Selects nodes to report from a comma-separated list of xnames, or
        a single xname. The xname values are case insensitive, and leading
        zeros from the integer parts will be removed before matching. May be
        used with **--nids**.

**-n, --nids**
        Selects nodes to report from a comma-separated list of NIDs, or a single
        NID. May be used with **--xnames**.

**--no-headings**
        Remove headings from the output table.

**-h, --help**
        Print a usage summary and exit.

NOTES
=====

If **--xnames** and **--nids** are used in combination, any node that matches either
set will be reported (as in a set union or logical OR operation).

SEE ALSO
========

sat(8)
