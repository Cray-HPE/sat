=============
 SAT-HWMATCH
=============

----------------------------------------------------
Check that hardware matches at blade and node scopes
----------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **hwmatch** [options]

DESCRIPTION
===========

The hwmatch subcommand checks that certain values within processors and
memory modules match at the level of the node (which has multiple
processors and memory modules), at the level of the node card, and/or
at the level of the blade slot. Processor values that must match are
model, core count, and speed. Memory module values that must match are
memory type, memory device type, and size. The number of memory modules
must also match. The memory manufacturer must match for just the node
level, not card or slot levels.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat hwmatch'.
**-l, --level**
        The level at which processor and memory modules are matched: 'slot',
        'card' or 'node'. Multiple levels can be specified by using this
        option multiple times, for example '--level slot --level node'.
        The card level is a subset of slot, whereas the node level indicates
        additonal checking at just the node scope. The level defaults to
        'card'.
**-s, --show-matches**
        Show matches in additon to mismatches (voluminous output).

.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Match at the slot and node level:

::

    # sat hwmatch --level slot --level node
    +-----------+-------+----------+---------------------+---------------+
    | xname     | Level | Category | Field               | Values        |
    +-----------+-------+----------+---------------------+---------------+
    | x1000c1s1 | slot  | node     | Memory Module Count | 16 (2), 0 (2) |
    | x1000c2s1 | slot  | node     | Memory Module Count | 0 (2), 16 (2) |
    | x1000c4s0 | slot  | node     | Memory Module Count | 0 (1), 16 (3) |
    | x1000c4s1 | slot  | node     | Memory Module Count | 16 (2), 0 (2) |
    | x1000c4s2 | slot  | node     | Memory Module Count | 0 (2), 16 (2) |
    | x1000c4s3 | slot  | node     | Memory Module Count | 16 (2), 0 (2) |
    | x1000c4s6 | slot  | node     | Memory Module Count | 0 (2), 16 (2) |
    | x1000c5s2 | slot  | node     | Memory Module Count | 16 (3), 0 (1) |
    | x1000c5s3 | slot  | node     | Memory Module Count | 16 (2), 0 (2) |
    | x1000c6s1 | slot  | node     | Memory Module Count | 16 (2), 0 (2) |
    | x1000c7s0 | slot  | node     | Memory Module Count | 16 (2), 0 (2) |
    | x1000c7s1 | slot  | node     | Memory Module Count | 16 (2), 0 (2) |
    +-----------+-------+----------+---------------------+---------------+

Columns
-------

| *xname*
|
|   The xname of the slot, card, or node where a mismatch was found.
|
| *Level*
|
|   The level in effect: slot, card, or node.
|
| *Category*
|
|   The category: Processor or Memory (modules in the node).
|
| *Field*
|
|   The name of the field in the hardware inventory that did not match
|   ('module-count' being an exception where the number of memory modules
|   in the node is counted).
|
| *Values*
|
|   Values found for the field, separated by commas. The field
|   did not match because more than one unique value was found.
|   Numbers in parentheses indicate how many instances of the
|   value were found.

SEE ALSO
========

sat(8)

.. include:: _notice.rst
