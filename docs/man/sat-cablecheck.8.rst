================
 SAT-CABLECHECK
================

------------------------------------------------------------
Check that cables are correctly connected within the system.
------------------------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **cablecheck** [options] *p2p-file*

DESCRIPTION
===========

The cablecheck subcommand checks connectivity within the Shasta system as
compared to an expected configuration as specified within a point-to-point
file.

POSITIONAL ARGUMENTS
====================

*p2p-file*
        Point-to-point file. This file contains the expected configuration
        that Shasta will be compared against.

OPTIONS
=======

These options must be specified after the command.

**-h, --help**
        Print the help message for 'sat cablecheck'.

SEE ALSO
========

sat(8)
