=====
 SAT
=====

------------------------
The System Admin Toolkit
------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] *command* [options]

DESCRIPTION
===========

The System Admin Toolkit (SAT) is a command line utility meant to be run from
the Bastion Inception Sentinel (BIS) server. Its purpose is to assist admins
with troubleshooting and querying information about the Shasta system and its
components at large.

This utility operates via "subcommands", and each has its own manual page.
These are referenced in the **SEE ALSO** section.

OPTIONS
=======

These global options must be specified before the command.

**--logfile** *file*
        Set the location of logs for this run. This overrides the value in
        the configuration file.

**--loglevel** *level*
        Set the minimum log severity to report. This overrides the values in
        the configuration file for both stderr and log file (the configuration
        options "logging.file_level" and "logging.stderr_level").

**--username** *username*
        Username to use when loading or fetching authentication
        tokens. Overrides value set in config file.

**--token-file** *token-file*
        Token file to use for authentication. Overrides value derived from other
        settings, or set in config file.

**-h, --help**
        Print the help message for sat.

SEE ALSO
========

sat-cablecheck(8), sat-diag(8), sat-hwinv(8), sat-setrev(8), sat-showrev(8),
sat-status(8), sat-auth(8)
