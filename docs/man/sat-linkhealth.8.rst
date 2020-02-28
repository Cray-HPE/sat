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
This information is obtained via Redfish queries, so a valid redfish username
and password for the target hosts is required.

This subcommand allows use of the "--xname" options. The provided xnames
will match against Redfish endpoints that are of type "RouterBMC" as
reported by the Hardware State Manager. The match is considered valid
if the specified xname is a subsequence of the reported ID. If the HSM
is down, then the verbatim xnames are targeted instead.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst
.. include:: _sat-redfish-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

::


    # Some example output from a much larger table. Multiple routers 
    # were queried to compile this information.
    #
    # MISSING means that Redfish did not return a repsonse for that field.

    $ sat linkhealth
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | xname            | cable_present | physical_port | link_status | health | state    | flow_control_configuration | link_speed_mbps |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | x1002c7r7b0bp8p1 | No Device     | 3             | Down        | OK     | Disabled | MISSING                    | 0               |
    | x1002c7r7b0j1p1  | Not Present   | 4             | MISSING     | OK     | Starting | MISSING                    | MISSING         |
    | x1002c7r7b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    | x1000c0r3b0bp8p1 | No Device     | 3             | Up          | OK     | Enabled  | MISSING                    | 100000          |
    | x1000c0r3b0j1p1  | Not Present   | 4             | MISSING     | OK     | Starting | MISSING                    | MISSING         |
    | x1000c0r3b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    | x1000c0r3b0j2p1  | Present       | 22            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+

    # The -x option has more uses than simple output filtering because it cuts
    # down the number of queries made.

    $ sat linkhealth -x x1002c7r7b0
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | xname            | cable_present | physical_port | link_status | health | state    | flow_control_configuration | link_speed_mbps |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | x1002c7r7b0bp8p1 | No Device     | 3             | Down        | OK     | Disabled | MISSING                    | 0               |
    | x1002c7r7b0j1p1  | Not Present   | 4             | MISSING     | OK     | Starting | MISSING                    | MISSING         |
    | x1002c7r7b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+

    # Multiple routers can be queried by specifying -x multiple times.

    $ sat linkhealth -x x1000c0r3b0 -x x1001c4r5b0

    # If one only cares about links that are 'Present', then use the --filter
    # opts.

    $ sat linkhealth --filter cable_present='present'
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | xname            | cable_present | physical_port | link_status | health | state    | flow_control_configuration | link_speed_mbps |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | x1002c7r7b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    | x1000c0r3b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    | x1000c0r3b0j2p1  | Present       | 22            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+

SEE ALSO
========

sat(8)
