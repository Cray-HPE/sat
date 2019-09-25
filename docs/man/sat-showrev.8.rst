=============
 SAT-SHOWREV
=============

-------------------------------------------------
Print version information about the Shasta system
-------------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **showrev** [options]

DESCRIPTION
===========

The showrev subcommand is for printing revision information about the Shasta
System. This includes general version information about the sat system, as
well as version information about installed docker images and rpm packages
on the target node.

OPTIONS
=======

These options must be specified after the command.

**--system**
        Display general version information about the Shasta system. This is
        the default behavior.

**--docker**
        Display information about the containers installed on this node.

**--packages**
        Display information about the installed packages on this node.

**--all**
        Print everything. Equivalent to specifying **--system**,
        **--docker**, and **--packages**.

**-s** *SUBSTR*, **--substr** *SUBSTR*
        Show version information for components whose names or IDs contain
        the substring.

**-n, --no-headings**
        If applicable, do not print table headings.

**-h, --help**
        Print the help message for 'sat showrev'.

SEE ALSO
========

sat(8)
