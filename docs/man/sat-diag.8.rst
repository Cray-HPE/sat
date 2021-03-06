==========
 SAT-DIAG
==========

---------------------------
Run L1 diagnostics at scale
---------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **diag** [options] *command* [args]

DESCRIPTION
===========

The diag subcommand is used for running L1 diagnostics on an arbitrary
number of chassis, nodes, and switches in liquid-cooled cabinets and
Slingshot top-of-rack switches. This tool accepts a list of xnames of
controllers (BMCs) of the chassis, node, or switch to target. Note that
the diag subcommand supports only BMCs which have type "RouterBMC" in
the HSM database, i.e. Rosetta switches. This list may be passed on the
command line, from a file, and/or stdin, and will launch a given command
on these controllers. Targets are polled at a specific interval. A
report is printed after all targets have completed their diagnostics,
either to stdout (default) or to files, one for each switch. API gateway
authentication is required.

ARGUMENTS
=========

*command* [args]
        Specify the alias of a diagnostic command which can be called
        through Fox, as well as arguments to pass to that command.

OPTIONS
=======

These options must be specified after the subcommand.

**-h**, **--help**
        Display a help message and exit.

**-i** *SECONDS*, **--interval** *SECONDS*
        Specify the interval, in seconds, at which the targets
        should be polled to check the status of the diagnostics.
        Defaults to 10 seconds.

**-t** *SECONDS*, **--timeout** *SECONDS*
        Specify the timeout, in seconds, after which diagnostics  that
        are still running will be cancelled. Defaults to 300 seconds
        (5 minutes).

**--disruptive**
        If this flag is used, the user will not be prompted
        interactively to ask whether they wish to proceed. L1
        diagnostics can disrupt production environments, so this flag
        should be used with caution. This flag is useful for running
        automated scripts which do not have interactive input.

**--no-hsm-check**
        If this flag is supplied, HSM will not be queried to check if 
        target components are RouterBMCs. (This is useful when running 
        diagnostics when HSM is unavailable.)

**--split**
        If this flag is supplied, write the contents of stdout returned
        from each switch to its own file. This may help for preserving
        output or for reducing the amount of output printed to the
        terminal.

**--interactive**
        If this flag is supplied, the user will be given an interactive shell
        from which multiple diagnostic commands can be launched sequentially.
        Note that this option may only be supplied if **command** is not
        given.

        While in interactive mode, type **quit**, **exit**, or **ctrl-d** to
        exit. **help** is also available as a quick reference.

Exactly one of **command** or **--interactive** must be supplied.

.. include:: _sat-xname-opts.rst

EXAMPLES
========

Run a diagnostic named **runMemTester** with an option to just print its usage
information on two xnames at once:

::

        # sat diag --xname x1000c0r0b0 --xname x1000c0r1b0 runMemTester -h

The xnames can also be specified by providing a path to a file that contains one
xname per line. E.g.:

::

        # sat diag --xname-file my-xnames.txt runMemTester -h

In the example above, the file **my-xnames.txt** contains the following lines:

::

        x9000c1b0
        x9000c1r1b0
        x9000c1r7b0
        x9000c1s0b0
        x9000c1s0b1
        x3000c0r24b0

SEE ALSO
========

sat(8)

.. include:: _notice.rst
