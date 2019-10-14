=====
 SAT
=====

------------------------
The Shasta Admin Toolkit
------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] *command* [options]

DESCRIPTION
===========

The Shasta Admin Toolkit (SAT) is a command line utility meant to be run from
the Shasta's Bastion / Inception / Sentinel Server (BIS). Its purpose is to
assist Shasta admins with troubleshooting and querying information about
the Shasta system and her components at large.

This utility operates via "subcommands", and each has its own manual page.
These are referenced in the **SEE ALSO** section.

OPTIONS
=======

These global options must be specified before the command.

**--logfile** *file*
        Set the location of logs for this run.

**--loglevel** *level*
        Set the minimum log severity that should be reported. This overrides
        the values in the configuration file.

**-h, --help**
        Print the help message for sat.

SEE ALSO
========

sat-cablecheck(8), sat-diag(8), sat-setrev(8), sat-showrev(8), sat-status(8)
