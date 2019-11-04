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
        configuration of links between ports.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat cablecheck'.

EXAMPLES
========

The p2p file can be generated using the Shasta Cabling Tool (SCT), which
requires a site configuration file as input. The site configuration file is
created as part of the installation procedure for the system. An example
procedure is shown below.

::

    python scttool session-title site_cfg.yaml

    cat ./out/session-title_pt_pt.csv

SEE ALSO
========

sat(8)
