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
with troubleshooting and querying information about the system and its
components at large.

This utility operates via "subcommands", and each has its own manual page.
These are referenced in the **SEE ALSO** section.

OPTIONS
=======

These global options must be specified before the subcommand.

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

FILTERING
=========

For subcommands which support filtering, the option **--filter** should be used.

By default, the **--filter** option accepts a simple query language which can be
used to filter data from any command which returns tabular-formatted
information. In the query language, rows can be filtered by column using
comparisons with the operators =, !=, >, <, >=, and <=. Comparisons using the =
operator can utilize Unix-style wildcards (e.g., '*' or '?').  Furthermore,
multiple comparisons can be combined with the boolean operators 'and' and/or
'or'. A few examples of filter queries:

- 'manfctr = Cray* and capacity >= 192' selects all components manufactured by
    Cray which have at least 192 GiB of memory.

- 'xname = x3000c0s21 and state = ready' selects all nodes which are ready and
    ok on the blade in slot 21 of chassis 0 in cabinet 3000.

A column may be specified by some subsequence of its name, meaning that zero or
more characters may be deleted. For example, a column named 'memory_capacity'
could be specified by filtering against 'mem_cap', 'mem_capacity', or
'mem'. Note, however, that a subsequence must be unique; for example, if some
output has columns 'mem_capacity' and 'mem_frequency', a query against 'mem'
would be ambiguous. Either 'mem_cap' or 'mem_freq' could be used.

Column headers and row contents are not case sensitive during filtering. For
example, to filter against a column 'State', the names 'state', 'State', or even
'StAtE' could be used.

Boolean combinations, typical precedence rules apply; that is, 'and'
combinations have higher precedence than 'or' combinations. For example, for a
hypothetical table with columns foo, bar, and baz, the query 'foo = 1 and bar =
2 or baz = 3' can be visualized as '(foo = 1 and bar = 2) or (baz = 3)'.

CONFIGURATION
=============

SAT can be configured by editing its configuration file. This configuration
file is in TOML format, and is installed at /etc/sat.toml.

The configuration file is installed with commented out values. These indicate
the internal values SAT will use if these values are not provided by the
configuration file and were not specified on the command line. This list
represents the complete set of values that can be set via the configuration
file.

If one of the options in the configuration file has a parallel command-line
parameter, then the value specified on the command-line will override the value
read from the configuration file. Not every parameter in the configuration file
can be overridden on the command-line.

API_GATEWAY
-----------

**host**
        Points to the API gateway.

**cert_verify**
        If "true", then SAT will validate the authenticity of the api-gateway
        via a signed certificate before communicating. Per TOML specifiction,
        this paramter must be "true" or "false". These values are
        case-sensitive.

        This parameter is set to "true" by default.

**username**
        This is the username SAT will use to retrieve a login token if one
        does not already exist. If this parameter is not specified, then SAT
        will use the login name of the user.

**token_file**
        Store the login token between sessions with the api-gateway. If this
        value isn't provided, then SAT will use the default location as
        specified in sat-auth(8).

FORMAT
------

**no_headings**
        If "true", then omit headings from tabular output. Defaults to "false".

**no_borders**
        If "true", then omit borders from tabular output. Defaults to "false".

GENERAL
-------

**site_info**
        Some installation information about the system is site-specific, and
        needs to be manually entered. This file is where that information is
        stored. SAT expects this file to be in YAML format.

LOGGING
-------

**file_name**
        Default location where SAT will write its logs.

**file_level**
        Indicates the minimum log severity that will cause a log to be entered
        into the file.

**stderr_level**
        SAT also prints log messages to stderr, and this parameter sets the
        minimum log severity that will cause a log to be printed to stderr.

REDFISH
-------

**username**
        Default username to use when querying Cray services that are dependent
        on Redfish.

**password**
        Default password to use when querying Cray services that are dependent
        on Redfish. Use caution, as the password is stored as plaintext within
        the SAT configuration file.

SEE ALSO
========

sat-auth(8),
sat-cablecheck(8),
sat-diag(8),
sat-hwinv(8),
sat-setrev(8),
sat-showrev(8),
sat-status(8)
