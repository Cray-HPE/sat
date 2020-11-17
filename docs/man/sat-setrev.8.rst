============
 SAT-SETREV
============

----------------------------------------------------------
Populate site-specific information about the system
----------------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **setrev** [options]

DESCRIPTION
===========

The setrev subcommand prompts the user for input from stdin in order to populate
the site-information file. This file is used by **sat showrev --system** to
print the following fields:

    - Serial number
    - Site name
    - System name
    - System install date
    - System type

This subcommand is required to be run if **sat showrev** is to display this
information - as this information must be manually populated on the system.

OPTIONS
=======

These options must be specified after the subcommand.

**--sitefile** *file*
        Select a custom location to write the information. The **showrev**
        subcommand has a corresponding option.

FILES
=====

This subcommand requires extra files for its operation, and this section
details the purpose and default location of those files.

site_info: /opt/cray/etc/site_info.yml
        This is the file that will contain the information set by this command.
        This file is written in YAML format, and its location is configurable
        from the **--sitefile** command-line parameter or through the config
        file.

SEE ALSO
========

sat(8)

.. include:: _notice.rst
