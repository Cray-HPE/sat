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

**-x** *XNAME*, **--xname** *XNAME*
        This flag can be used to specify an xname on which to run tests.
        This flag can be used multiple times to specify multiple xnames.

**-f** *PATH*, **--xname-file** *PATH*
        Specify a path to a newline-delimited file containing a list
        of xnames on which to run diagnostics.

EXAMPLES
========

The xnames can be specified by providing a path to a file formatted similar
to the following example (ie. each xname on its own line).

::

    x0c0s14b0n0
    x0c0s21b0n0
    x0c0s24b0n0
    x0c0s28b0n0
    x0c0s16b0n0
    x0c0s26b0n0

SEE ALSO
========

sat(8)
