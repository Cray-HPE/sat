==========
 SAT-SWAP
==========

---------------------------------------------------
Disable/enable a component before/after replacement
---------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **swap** switch [options] *xname*

**sat** [global-opts] **swap** cable [options] *xname* [*xname* ...]

DESCRIPTION
===========

The sat swap subcommand streamlines hardware component replacement by
disabling components before removal and enabling the new components
after installation.

The 'swap switch' subcommand disables or enables the ports on a switch
This can be used during switch replacement, or for other purposes where
disabling/enabling all of the ports on a switch is useful.

The 'swap cable' subcommand disables or enables the ports to which a cable
is connected.  Given one or more jacks that a cable connects, the command
will disable all ports connected by that cable.

ARGUMENTS
=========

*xname*
        The xname of the switch, or one or more xnames describing
        the physical jacks that a cable connects.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat swap'.

**-a, --action** {enable, disable}
        Perform action to enable or disable the ports on a switch
        or connected by a cable.  Required if a dry run is not
        being performed.

**--disruptive**
        Perform disable/enable action without a prompt to continue.

**--dry-run**
        Perform a dry run without action to disable/enable the switch
        or cable.  The dry run obtains port links and port sets and
        configurations of ports, and creates port sets and deletes
        port sets. This can be used to check in advance there are no
        error conditions.

**-f, --force**
        If specified, the command will not verify that the specified
        jacks are connected by a cable.  Only valid when swapping a
        cable.

**-s, --save-ports**
        Save the switch or cable ports as a JSON file in the current
        working directory with name "<xname>-ports.json". This option
        can be useful even without enable/disable of the switch ports.

EXIT STATUS
===========

| 1: An invalid combination of options was given
| 2: Error getting ports for system
| 3: No ports found for the switch/cable
| 4: Port set to be created already exists
| 5: Creation of port set failed
| 6: Deletion of existing port set failed
| 7: Problem getting port configuration
| 8: Disable/enable of port set failed

EXAMPLES
========

Perform a dry run and save the port set for a switch:

::

    # sat swap switch --dry-run --save-ports x1000c6r7
    # ls x1000*
    x1000c6r7-ports.json

Disable a switch in preparation to replace it:

::

    # sat swap switch --action disable x1000c6r7
    Enable/disable of switch can impact system. Continue? (yes/[no]) yes
    Switch has been disabled and is ready for replacement.

Enable a switch after replacing it and skip the prompt:

::

    # sat swap switch --action enable --disruptive x1000c6r7
    Switch has been enabled.

Disable a cable in preparation to replace it:

::

    # sat swap cable --action disable --disruptive x5000c1r3j16
    Ports: x5000c1r3j16p0 x5000c3r7j18p0 x5000c1r3j16p1 x5000c3r7j18p1
    Cable has been disabled and is ready for replacement.

Disable a cable in preparation to replace it, giving both jacks connected
by the cable:

::

    # sat swap cable --action disable --disruptive x5000c1r3j16 x5000c3r7j18
    Ports: x5000c3r7j18p0 x5000c1r3j16p0 x5000c3r7j18p1 x5000c1r3j16p1
    Cable has been disabled and is ready for replacement.

Disable all ports on given jacks, using **--force** to skip checking that they
are connected by a cable:

::

    # sat swap cable --action disable --disruptive --force x5000c1r3j16 x5000c1r4j19
    WARNING: Jacks x5000c1r3j16,x5000c1r4j19 are not connected by a single cable
    Ports: x5000c1r3j16p0 x5000c3r7j18p0 x5000c1r3j16p1 x5000c3r7j18p1 x5000c1r4j19p0 x5000c1r1j15p0 x5000c1r4j19p1 x5000c1r1j15p1
    Cable has been disabled and is ready for replacement.

Use **--dry-run** to determine all linked ports from a single jack:

::

    # sat swap cable --dry-run x5000c1r3j16
    Ports: x5000c1r3j16p0 x5000c3r7j18p0 x5000c1r3j16p1 x5000c3r7j18p1
    Dry run completed with no action to enable/disable cable.


SEE ALSO
========

sat(8)

.. include:: _notice.rst
