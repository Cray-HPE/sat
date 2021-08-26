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

EXAMPLES
========

Translate a node xname to a nid:

::

    # sat xname2nid x3000c0s1b0n0
    nid100011

Translate two node xnames to nids:

::

    # sat xname2nid x3000c0s1b0n0,x1000c2s0b0n0
    nid100011,nid001064

Translate a node BMC xname to nids:

::

    # sat xname2nid x1000c5s2b0
    nid001168,nid001169

Translate a slot xname to nids:

::

    # sat xname2nid x1000c5s0
    nid001160,nid001161,nid001162,nid001163

Translate a chassis xname to nids:

::

    # sat xname2nid x1000c5
    nid001160,nid001161,nid001162,nid001163,nid001164,nid001165,nid001166,nid001167,nid001168,nid001169,nid001170,nid001171,nid001172,nid001173,nid001174,nid001175,nid001176,nid001177,nid001178,nid001179,nid001180,nid001181,nid001182,nid001183,nid001184,nid001185,nid001186,nid001187,nid001188,nid001189,nid001190,nid001191

Translate a node xname and a slot xname to nids:

::

    # sat xname2nid x3000c0s1b0n0,x1000c5s1
    nid100011,nid001164,nid001165,nid001166,nid001167

SEE ALSO
========

sat(8)
sat-nid2xname(8)

.. include:: _notice.rst
