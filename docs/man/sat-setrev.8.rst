============
 SAT-SETREV
============

----------------------------------------------------------
Populate site-specific information about the Shasta system
----------------------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **setrev** [options]

DESCRIPTION
===========

The setrev subcommand is for populating the site-information file. This file
is located at */opt/cray/etc/site_info.yml* by default.

This information is printed out by **sat showrev** during its **--system**
operation; specifically the following fields...

    - Serial number
    - Site name
    - System name
    - System install date
    - System type

This subcommand is required to be run if **sat showrev** is to display this
information - as this information must be manually populated on a Shasta system.

OPTIONS
=======

These options must be specified after the subcommand.

**--sitefile** *file*
        Select a custom location to write the information. The **showrev**
        subcommand has a corresponding option.

SEE ALSO
========

sat(8)
