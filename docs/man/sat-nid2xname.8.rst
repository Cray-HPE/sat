===============
 SAT-NID2XNAME
===============

---------------------------------
Translate node IDs to node xnames
---------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **nid2xname** [options] *nids*

DESCRIPTION
===========

The sat nid2xname subcommand translates node IDs to node xnames.

ARGUMENTS
=========

*nids*
        A list of node IDs and node ID ranges.   A node ID (nid) is
        either an integer or a string of the form nid123456,
        that is “nid” and a six digit zero padded number.  The nids
        and nid ranges are separated by a comma or whitespace.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat nid2xname'.

EXAMPLES
========

Translate a nid to a node xname:

::

    # sat nid2xname nid100001
    x3000c0s1b0n0

Translate two nids to node xnames:

::

    # sat nid2xname 100001,1225
    x3000c0s1b0n0,x1000c7s0b0n0

Translate a nid range to node xnames:

::

    # sat nid2xname 100001-100004
    x3000c0s1b0n0,x3000c0s3b0n0,x3000c0s5b0n0,x3000c0s7b0n0

SEE ALSO
========

sat(8)
sat-nid2xname(8)

.. include:: _notice.rst
