==========
 SAT-INIT
==========

---------------------------------------
Create a default SAT configuration file
---------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **init** [options]

DESCRIPTION
===========

The init subcommand generates a default configuration file for SAT.

By default, the configuration file is written to the path specified by the
$SAT_CONFIG_FILE environment variable, or $HOME/.config/sat/sat.toml if the
environment variable is not set.  This can be overridden on the command-line.

The init command will not overwrite an existing configuration file by default,
but this can be overridden on the command-line.

Given a username with the ``--username`` global option, the resulting
configuration file will be written with the specified username in the
"api_gateway" options.  This does not perform authentication.  For
authentication, see sat-auth(8).

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat init'.

**-f, --force**
        Forcibly overwrite an existing configuration file.

**-o, --output** *PATH*
        Specify a custom location to write the configuration file.  The default
        value is the value of the $SAT_CONFIG_FILE environment variable, or
        $HOME/.config/sat/sat.toml.

EXAMPLES
========

Generate a default configuration file in the default location:

::

    # sat init
    Configuration file "/root/.config/sat/sat.toml" generated.
    # ls -l ~/.config/sat/sat.toml
    -rw-r--r-- 1 root root 1924 Nov 10 14:00 /root/.config/sat/sat.toml

Forcibly overwrite the SAT configuration:

::

    # ls -l ~/.config/sat/sat.toml
    -rw-r--r-- 1 root root 1924 Oct 26 18:54 /root/.config/sat/sat.toml
    # sat init --force
    # ls -l ~/.config/sat/sat.toml
    -rw-r--r-- 1 root root 1924 Nov 10 14:00 /root/.config/sat/sat.toml

Write the SAT configuration to an alternate location:

::

    # sat init --output /tmp/config/sat.toml
    Configuration file "/tmp/config/sat.toml" generated.
    # ls -l /tmp/config/sat.toml
    -rw-r--r-- 1 root root 1924 Nov 10 14:50 /tmp/config/sat.toml

Write the SAT configuration with a custom username:

::

    # sat --username satuser init
    Configuration file "/root/.config/sat/sat.toml" generated.
    # cat ~/.config/sat/sat.toml
    ...
    [api_gateway]
    ...
    username = "satuser"
    ...


SEE ALSO
========

sat(8)

.. include:: _notice.rst