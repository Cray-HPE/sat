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
with troubleshooting and querying information about the Shasta system and its
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
        Points to the Cray EX-1 API gateway.

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
        Some installation information about the EX-1 is site-specific, and
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
