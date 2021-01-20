============
 SAT-SWITCH
============

----------------------------------------------
Disable/enable switch before/after replacement
----------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **switch** [options] *xname*

DESCRIPTION
===========

Note: The 'sat switch' subcommand is deprecated and will be removed in
a future release.  Please use the equivalent 'sat swap switch' command.
For more information, please see sat-swap(8).

The switch subcommand disables the ports on a switch, or enables the
ports on a switch. This can be used during switch replacement, or for
other purposes where disabling/enabling all of the ports on a switch
is useful.

ARGUMENTS
=========

*xname*
        The xname of the switch.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat switch'.

**-a, --action** {enable, disable}
        Perform action to enable or disable the switch. This option is
        required if a dry run is not being performed.

**--disruptive**
        Perform disable/enable action without a prompt to continue.

**--dry-run** 
        Perform a dry run without action to disable/enable the switch.
        The dry run obtains port links and port sets and configurations
        of ports, and creates port sets and deletes port sets. This can
        be used to check in advance there are no error conditions.

**-s, --save-ports**
        Save the switch ports as a JSON file in the current working
        directory with name "<xname>-ports.json". This option can be
        useful even without enable/disable of the switch ports.

EXIT STATUS
===========

| 1: An invalid combination of options was given
| 2: Error getting ports for system
| 3: No ports found for the switch
| 4: Port set to be created already exists
| 5: Creation of port set failed
| 6: Deletion of existing port set failed
| 7: Problem getting port configuration
| 8: Disable/enable of port set failed

EXAMPLES
========

Perform a dry run and save the port set for the switch:

::

    # sat switch --dry-run --save-ports x1000c6r7
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
sat-swap(8)

.. include:: _notice.rst
