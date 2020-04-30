============
 SAT-SWITCH
============

----------------------------------------------
Disable/enable switch before/after replacement
----------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **switch** [options] *xname*

DESCRIPTION
===========

The switch subcommand disables the ports on a switch, or enables the
ports on a switch. This can be used during switch replacement, or for
other purposes where disabling/enabling all of the ports on a switch
is useful.

ARGUMENTS
=========

*xname*
        The xname of the switch (also called router).

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat cablecheck'.

**--disruptive**
        Perform disable/enable action. Without this option, a trial run
        is performed to obtain port links and port sets, and to create
        port sets and delete them, but without configuring the ports to
        disable/enable them.

**--finish**
        Finish switch replacement by enabling the switch ports. Without
        this option, the switch ports are disabled in preparation for
        switch replacement.

**-s, --save-portset**
        Save the switch port set as a JSON file in the current working
        directory with name "<xname>-ports.json". This option can be
        useful even without enable/disable of the switch ports.

SEE ALSO
========

sat(8)
