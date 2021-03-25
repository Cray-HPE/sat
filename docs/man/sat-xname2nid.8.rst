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

The sat xname2nid subcommand translates node and node BMC xnames
to node IDs (nids). A node xname is translated to a nid. A node BMC
xname is the parent xname of a set of node xnames and is translated
to a list of nids.

ARGUMENTS
=========

*xnames*
        A list of xnames for nodes or node BMCs.  The xnames are
        separated by a comma or whitespace.

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
    nid100001

Translate two node xnames to nids:

::

    # sat xname2nid x3000c0s1b0n0,x1000c7s0b0n0
    nid100001,nid001225

Translate a node BMC xname to nids:

::

    # sat xname2nid x1000c5s4b0
    nid001177,nid001178

SEE ALSO
========

sat(8)
sat-nid2xname(8)

.. include:: _notice.rst
