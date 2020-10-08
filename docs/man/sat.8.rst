=====
 SAT
=====

------------------------
The System Admin Toolkit
------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
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

CONFIGURATION
=============

SAT can be configured by editing its configuration file. This configuration
file is in TOML format, and is installed at /etc/sat.toml. A custom location
may be specified in the SAT_CONFIG_FILE environment variable.

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

BOOTSYS
-------

**max_pod_states**
        Maximum number of pod-state files allowed to accumulate in
        /var/sat/bootsys/pod-states. These files record the state of all pods in
        kubernetes at the time the system is shut down, and the latest one is
        used to verify when the pods are up after reboot. The default value is
        10.

**max_hsn_states**
        Maximum number of hsn-state files allowed to accumulate in
        /var/sat/bootsys/hsn-states. These files record the state of the
        high-speed network at the time the system was shut down, and the latest
        one is used to verify when the HSN is up after reboot. The default value
        is 10.

**cle_bos_template**
        The name of the BOS session template to use for shutting down and
        booting the CLE compute nodes during a shutdown or boot action. If not
        specified, this defaults to searching for a session template that
        matches the pattern "cle-X.Y.Z" where X, Y, and Z are integer version
        numbers. If this option is not specified, and more than one BOS session
        template matches the pattern, the `bootsys` command will fail with a
        message indicating that an explicit CLE BOS template must be specified.

        This config file option can by overridden by the command-line option of
        the same name.

**uan_bos_template**
        The name of the BOS session template to use for shutting down and
        booting the User Access Nodes (UANs) during a shutdown or boot action.
        If not specified, this defaults to "uan".

        This config file option can by overridden by the command-line option of
        the same name.

**discovery_timeout**
        Timeout, in seconds, to wait until node controllers
        (NodeBMCs) reach the powered on state after the HMS
        Discovery cronjob is resumed. Defaults to 600.

**ipmi_timeout**
        Timeout, in seconds, to wait until management NCNs
        reach the desired power state after IPMI power
        commands are issued. Defaults to 60.

**ncn_boot_timeout**
        Timeout, in seconds, to wait until management nodes
        are reachable via SSH after boot. Defaults to 300.

**k8s_timeout**
        Timeout, in seconds, to wait until Kubernetes pods
        have returned to their pre-shutdown state. Defaults to
        600.

**ceph_timeout**
        Timeout, in seconds, to wait until ceph has returned
        to a healthy state. Defaults to 600.

**bgp_timeout**
        Timeout, in seconds, to wait until BGP routes report
        that they are established on management switches.
        Defaults to 600.

**hsn_timeout**
        Timeout, in seconds, to wait until the high-speed
        network (HSN) has returned to its pre-shutdown state.
        Defaults to 300.

**bos_boot_timeout**
        Timeout, in seconds, to wait until compute and
        application nodes have completed their BOS boot.
        Defaults to 900.

**capmc_timeout**
        Timeout, in seconds, to wait until components reach
        powered off state after they are shutdown with CAPMC.
        Defaults to 120.

**bos_shutdown_timeout**
        Timeout, in seconds, to wait until compute and
        application nodes have completed their BOS shutdown.
        Defaults to 600.

**ncn_shutdown_timeout**
        Timeout, in seconds, to wait until management NCNs
        have completed a graceful shutdown and have reached the
        powered off state according to IMPI. Defaults to 300.

FORMAT
------

**no_headings**
        If "true", then omit headings from tabular output. Defaults to "false".

**no_borders**
        If "true", then omit borders from tabular output. Defaults to "false".

**show_empty**
        If "true", then show values for columns even if every value is EMPTY. Defaults to "false".

**show_missing**
        If "true", then show values for columns even if every value is MISSING. Defaults to "false".

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
        (optional) Default username to use when querying Cray services that are
        dependent on Redfish. If not supplied, the user will be queried on the
        command line to give a username when running diagnostics.

**password**
        (optional) Default password to use when querying Cray services that are
        dependent on Redfish. Use caution, as the password is stored as
        plaintext within the SAT configuration file. If not supplied, the user
        will be queried for a password on the command line when running
        diagnostics.

SEE ALSO
========

sat-auth(8),
sat-bootsys(8),
sat-cablecheck(8),
sat-diag(8),
sat-firmware(8),
sat-hwinv(8),
sat-hwmatch(8),
sat-k8s(8),
sat-linkhealth(8),
sat-sensors(8),
sat-setrev(8),
sat-showrev(8),
sat-status(8),
sat-swap(8)
sat-switch(8)

.. include:: _notice.rst
