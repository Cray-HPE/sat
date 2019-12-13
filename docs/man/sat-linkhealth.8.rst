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

**-x, --xname**
        List the xnames which should be queried. These will match against
        Redfish endpoints that are of type "RouterBMC" as reported by the
        Hardware State Manager. If the HSM is down, then the verbatim
        xnames are targeted instead. The match is considered valid if
        the specified xname is a subsequence of the reported ID.

**-h, --help**
        Print a usage summary and exit.

.. include:: _sat-format-opts.rst
.. include:: _sat-redfish-opts.rst

SEE ALSO
========

sat(8)
