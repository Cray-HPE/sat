================
 SAT-LINKHEALTH
================

---------------------------------------------
Report on the health of Rosetta switch links.
---------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **linkhealth** [options]

DESCRIPTION
===========

The linkhealth subcommand reports on the health of links for available routers.
A Redfish username and password is required.

This subcommand allows use of the "--xname" options. The provided xnames must
be Router BMCs or components that contain Router BMCs. The xname of a Router BMC
has the form x#c#r#b# (cabinet #, chassis # router #, BMC #). If a cabinet is
specified, then all router BMCs in that cabinet are targeted. If a chassis is
specified, then all router BMCs in that chassis are targeted. If a router is
specified, then all BMSs for the router are targeted. If no xname is specified,
all router BMCs are targeted.

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

Below is some example output from a much larger table. Multiple routers
were queried to compile this information.

MISSING means that Redfish did not return a repsonse for that field.

Get the health of all links in the system (note that this may not scale well to a large system):

::

    # sat linkhealth
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

The **-x** option has more uses than simple output filtering because it cuts
down the number of queries made.

Get the health of all links in a particular router:

::

    # sat linkhealth -x x1002c7r7b0
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | xname            | cable_present | physical_port | link_status | health | state    | flow_control_configuration | link_speed_mbps |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+
    | x1002c7r7b0bp8p1 | No Device     | 3             | Down        | OK     | Disabled | MISSING                    | 0               |
    | x1002c7r7b0j1p1  | Not Present   | 4             | MISSING     | OK     | Starting | MISSING                    | MISSING         |
    | x1002c7r7b0j2p0  | Present       | 21            | Up          | OK     | Enabled  | MISSING                    | 200000          |
    +------------------+---------------+---------------+-------------+--------+----------+----------------------------+-----------------+

Multiple routers can be queried by specifying -x multiple times.

::

    # sat linkhealth -x x1000c0r3b0 -x x1001c4r5b0

If one only cares about links that are 'Present', then use the **--filter** opts.

::

    # sat linkhealth --filter cable_present='present'
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

.. include:: _notice.rst
