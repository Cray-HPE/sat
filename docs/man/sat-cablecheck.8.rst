================
 SAT-CABLECHECK
================

-----------------------------------------------------------
Check that cables are correctly connected within the system
-----------------------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **cablecheck** [options] *p2p-file*

DESCRIPTION
===========

The cablecheck subcommand checks the physical cable connectivity within
the system and compares this against an expected configuration provided
within a point-to-point file.

ARGUMENTS
=========

*p2p-file*
        Point-to-point file. This file should contain the expected
        configuration of links between ports. The file can be found
        in the directory "/opt/cray/etc/sct/", with a name that likely
        starts with "Shasta", includes the system name, and ends with
        "_pt_pt.csv". The xnames in the file must have a normal format
        without "." separating any component levels.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat cablecheck'.

SEE ALSO
========

sat(8)
