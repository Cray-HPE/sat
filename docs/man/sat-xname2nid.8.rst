===============
 SAT-XNAME2NID
===============

---------------------------------
Translate node xnames to node IDs
---------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **xname2nid** [options] *xnames*

DESCRIPTION
===========

The sat xname2nid subcommand translates xnames to node IDs (nids).
A node xname is translated to a nid. A cabinet, chassis, slot, or
node BMC xname is an ancestor xname of a set of node xnames and
is translated to a list of nids.

ARGUMENTS
=========

*xnames*
        A list of xnames for nodes or cabinets, chassis, slots or
        node BMCs that contain nodes. The xnames are separated by
        a comma or whitespace.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat xname2nid'.

**-f, --format** {**nid**, **range**}
        Display the nids in the format specified.
        If the **range** format is used, the nids are displayed as
        ranges with the nids sorted and duplicate nids removed.
        If the **nid** format is used, the nids are displayed as
        strings with the nids sorted for each xname and displayed in the
        order of the xnames specified.  Defaults to **range**.

EXAMPLES
========

Translate a node xname to a nid:

::

    # sat xname2nid x3000c0s1b0n0
    nid100011

Translate two node xnames to nids:

::

    # sat xname2nid x3000c0s1b0n0,x1000c2s0b0n0
    nid[001064,100011]

Translate two node xnames to nids using nid format:

::

    # sat xname2nid --format nid x3000c0s1b0n0,x1000c2s0b0n0
    nid100011,nid001064

Translate a node BMC xname to nids:

::

    # sat xname2nid x1000c5s2b0
    nid[001168-001169]

Translate a slot xname to nids:

::

    # sat xname2nid x1000c5s0
    nid[001160-001163]

Translate a chassis xname to nids:

::

    # sat xname2nid x1000c5
    nid[001160-001191]

Translate a node xname and a slot xname to nids:

::

    # sat xname2nid x3000c0s1b0n0,x1000c5s1
    nid[001164-001167,100011]

Translate a node xname and a slot xname to nids using nid format:

::

    # sat xname2nid --format nid x3000c0s1b0n0,x1000c5s1
    nid100011,nid001164,nid001165,nid001166,nid001167

Translate a node xname and a slot xname with duplicates to nids:

::

    # sat xname2nid x1000c5s1b1,x1000c5s1
    nid[001164-001167]

Translate a node xname and a slot xname with duplicates to nids using nid format:

::

    # sat xname2nid --format nid x1000c5s1b1,x1000c5s1
    nid001166,nid001167,nid001164,nid001165,nid001166,nid001167

SEE ALSO
========

sat(8)
sat-nid2xname(8)

.. include:: _notice.rst
