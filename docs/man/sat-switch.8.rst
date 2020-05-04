============
 SAT-SWITCH
============

----------------------------------------------
Disable/enable switch before/after replacement
----------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2020 Hewlett Packard Enterprise Development LP.
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
        Print the help message for 'sat switch'.

**-a, --action** {enable, disable}
        Perform action to enable or disable the switch.

**--disruptive**
        Perform disable/enable action without a prompt to continue.

**--over-write**
        In the unexpected event of a port set to be created already
        existing, delete the port set and then create it. The port set
        name is prefixed by "SAT-" and includes the switch xname. Port
        sets are created for the switch and each port. This option is
        for contingencies such as an interrupted command that left port
        sets that would otherwise be deleted.

**--dry-run** 
        Perform a dry run without action to disable/enable the switch.
        The dry run obtains port links and port sets and configurations
        of ports, and creates port sets and deletes port sets. This can
        be used to check in advance there are no error conditions.

**-s, --save-portset**
        Save the switch port set as a JSON file in the current working
        directory with name "<xname>-ports.json". This option can be
        useful even without enable/disable of the switch ports.

EXIT STATUS
===========

| 1: Error getting ports for system
| 2: No ports found for the switch
| 3: Port set to be created already exists
| 4: Creation of port set failed
| 5: Problem getting port configuration
| 6: Disable/enable of port set failed

EXAMPLES
========

Perform a dry run and save the port set for the switch:

::

    # sat switch --dry-run --save-portset x1000c6r7
    # ls x1000*
    x1000c6r7-ports.json

Disable the switch in preparation to replace it:

:: 

    # sat switch --action disable x1000c6r7
    Enable/disable of switch can impact system. Continue? (yes/[no]) yes
    Switch has been disabled and is ready for replacement.

Enable the switch after replacing it and skip the prompt:

:: 

    # sat switch --action enable --disruptive x1000c6r7
    Switch has been enabled.

SEE ALSO
========

sat(8)
