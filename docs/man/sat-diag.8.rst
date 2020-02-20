==========
 SAT-DIAG
==========

-----------------------------------
Run L1 Rosetta diagnostics at scale
-----------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **diag** [options] *command* [args]

DESCRIPTION
===========

The diag subcommand is used for running L1 diagnostics on an arbitrary
number of Rosetta switches. This tool accepts a list of switch xnames
from the command line, a file, and/or stdin, and will launch a given
command on these hosts. Switches are polled at a specific interval.
A report is printed after all switches have completed their diagnostics,
either to stdout (default) or to files, one for each switch.

ARGUMENTS
=========

*command* [args]
        Specify the alias of a diagnostic command which can be called
        through Redfish, as well as arguments to pass to that command.

OPTIONS
=======

These options must be specified after the subcommand.

**-h**, **--help**
        Display a help message and exit.

**-i** *SECONDS*, **--interval** *SECONDS*
        Specify the interval, in seconds, at which the switches
        should be polled to check the status of the diagnostics.
        Defaults to 10 seconds.

**-t** *SECONDS*, **--timeout** *SECONDS*
        Specify the timeout, in seconds, after which diagnostics  that
        are still running will be cancelled. Defaults to 300 seconds
        (5 minutes).

**--disruptive**
        If this flag is used, the user will not be prompted
        interactively to ask whether they wish to proceed. L1 Rosetta
        diagnostics can disrupt production environments, so this flag
        should be used with caution. This flag is useful for running
        automated scripts which do not have interactive input.

**--split**
        If this flag is supplied, write the contents of stdout returned
        from each switch to its own file. This may help for preserving
        output or for reducing the amount of output printed to the
        terminal.

**--interactive**
        If this flag is supplied, the user will be given an interactive shell
        from which multiple diagnostic commands can be launched sequentially.
        Note that this option may only be supplied if **command** is not
        given. At least one of **command** or **--interactive** must be supplied
        on the command line.

.. include:: _sat-xname-opts.rst

EXAMPLES
========

Run a diagnostic named **runMemTester** with an option to just print its usage
information on two xnames at once::

        sat diag --xname x1000c0r0b0 --xname x1000c0r1b0 runMemTester -h

The xnames can also be specified by providing a path to a file that contains one
xname per line. E.g.::

        sat diag --xname-file my-xnames.txt runMemTester -h

In the example above, the file **my-xnames.txt** contains the following lines::

        x0c0s14b0n0
        x0c0s21b0n0
        x0c0s24b0n0
        x0c0s28b0n0
        x0c0s16b0n0
        x0c0s26b0n0

SEE ALSO
========

sat(8)
