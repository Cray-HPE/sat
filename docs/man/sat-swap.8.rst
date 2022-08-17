==========
 SAT-SWAP
==========

---------------------------------------------------
Disable/enable a component before/after replacement
---------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020-2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **swap** switch [options] *xname*

**sat** [global-opts] **swap** cable [options] *xname* [*xname* ...]

**sat** [global-opts] **swap** blade [options] *xname*

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

The 'swap blade' subcommand disables or enables a compute or UAN blade. This can
be used to replace a given blade with a different blade from the same system or
another system.

ARGUMENTS
=========

*xname*
        The xname of the blade, switch, or one or more xnames describing the
        physical jacks that a cable connects.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat swap'.

**-a, --action** {enable, disable}
        Perform action to enable or disable a blade, ports on a switch, or ports
        connected by a cable. Required if a dry run is not being performed.

**--disruptive**
        Perform disable/enable action without a prompt to continue.

**--dry-run**
        Perform a dry run without action to disable/enable the switch, cable,
        or blade. If swapping a switch or cable, the dry run obtains port links
        and port policies. If swapping a blade, ethernet interface mapping
        files will be saved. This can be used to check in advance there are no
        error conditions.

**-f, --force**
        If specified, the command will continue if there are errors when
        verifying that the specified jacks are connected by a single cable.
        Only valid when swapping a cable.

**-s, --save-ports**
        Save data about the switch or cable ports affected as a JSON file
        in the current working directory with name "<xname>-ports.json".
        For each port that is affected, the xname, port_link, and
        policy_link is included in the JSON output. This option
        can be useful even without enable/disable of the switch ports.

BLADE SWAP OPTIONS
==================

These options may only be specified when using the **sat swap blade**
subcommand, and must be specified after the **blade** subcommand.

**--src-mapping PATH**
        The path to the JSON-formatted ethernet interface mappings file from
        the source system. Such a file is created on the source system when
        **sat swap blade -a disable** is run against the source blade. The path
        to this file should be supplied when the source system blade is swapped
        into the destination system with the *enable* action. This option only
        applies to the *enable* action.

**--dst-mapping PATH**
        The path to the JSON-formatted ethernet interface mappings file from
        the destination system. Such a file is created on the destination system
        when **sat swap blade -a disable** is run against the destination
        blade. The path to this file should be supplied when the source system
        blade is swapped into the destination system with the *enable* action.
        This option only applies to the *enable* action.

EXIT STATUS
===========

| 1: An invalid combination of options was given
| 2: Error getting ports for system
| 3: No ports found for the switch/cable
| 4: Creation of port policy failed
| 5: Disable/enable of one or more ports failed

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

Disable all ports on given jacks, using **--force** to continue even though they
are not connected by a single cable:

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
