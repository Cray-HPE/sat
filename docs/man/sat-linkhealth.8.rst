================
 SAT-LINKHEALTH
================

---------------------------------------------
Report on the health of Rosetta switch links.
---------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **linkhealth** [options]

DESCRIPTION
===========

The linkhealth subcommand reports on the health of links for available xnames.
By default, only configured links that have problems are included in this
report.

This information is obtained via Redfish queries, so a valid redfish username
and password for the target hosts is required.

OPTIONS
=======

These options must be specified after the subcommand.

**--all**
        List all links - including unconfigured links and links that are
        deemed healthy. The filters provided by the **--xname** option
        will not be overridden by this option.

**--configured**
        Report on all configured links - even those that are healthy.

**--unhealthy**
        Report on all links whose status is not "OK" - even those
        that are not "configured".

**-x** *XNAME*, **--xname** *XNAME*
        This option can be used to list the specific xname to query. These
        will match against Redfish endpoints that are of type "RouterBMC" as
        reported by the Hardware State Manager. The match is considered valid
        if the specified xname is a subsequence of the reported ID. If the HSM
        is down, then the verbatim xnames are targeted instead. This option can
        be used multiple times to specify multiple xnames.

**-h, --help**
        Print a usage summary and exit.

.. include:: _sat-format-opts.rst
.. include:: _sat-redfish-opts.rst

EXAMPLES
========

::


    # Some example output from a much larger table. Multiple routers 
    # were queried to compile this information.

    $ sat linkhealth
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | xname            | cable_present | physical_port | link_status | health | state    | flow_control_configuration | link_speed_mbps |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | x1002c7r7b0bp8p1 | No Device     | 3             | Down        | OK     | Disabled | None                       | 0               |
    | x1002c7r7b0j1p1  | Not Present   | 4             | Not found   | OK     | Starting | None                       | Not found       |
    | x1002c7r7b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | None                       | 200000          |
    | x1000c0r3b0bp8p1 | No Device     | 3             | Up          | OK     | Enabled  | None                       | 100000          |
    | x1000c0r3b0j1p1  | Not Present   | 4             | Not found   | OK     | Starting | None                       | Not found       |
    | x1000c0r3b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | None                       | 200000          |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+

    # The -x option has more uses than simple output filtering because it cuts
    # down the number of queries made.

    $ sat linkhealth -x x1002c7r7b0
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | xname            | cable_present | physical_port | link_status | health | state    | flow_control_configuration | link_speed_mbps |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | x1002c7r7b0bp8p1 | No Device     | 3             | Down        | OK     | Disabled | None                       | 0               |
    | x1002c7r7b0j1p1  | Not Present   | 4             | Not found   | OK     | Starting | None                       | Not found       |
    | x1002c7r7b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | None                       | 200000          |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+

    # Multiple routers can be queried by specifying -x multiple times.

    $ sat linkhealth -x x1000c0r3b0 -x x1001c4r5b0

    # If one only cares about links that are 'Present', then use the --filter
    # opts.

    $ sat linkhealth --filter cable_present='present'
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | xname            | cable_present | physical_port | link_status | health | state    | flow_control_configuration | link_speed_mbps |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | x1002c7r7b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | None                       | 200000          |
    | x1000c0r3b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | None                       | 200000          |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+

SEE ALSO
========

sat(8)
