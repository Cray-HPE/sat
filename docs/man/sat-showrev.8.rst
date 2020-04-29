=============
 SAT-SHOWREV
=============

------------------------------------------
Print version information about the system
------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **showrev** [options]

DESCRIPTION
===========

The showrev subcommand prints revision information about the system.
This includes general version information about the system, as well as
version information about installed docker images and rpm packages.

The default behavior of this command is to print general revision information
about the system and the installed products. This is a mixture of information
read from individual product release files in ``/opt/cray/etc/release``,
site-specific information read from ``/opt/cray/etc/site_info.yml``, and various
api calls to other Cray services. The following list details the meaning and
source of information for each field.

Build version
    Not implemented, so it always displays None.

Interconnect
    Unique list of interconnect names obtained from the Hardware State
    Manager (HSM).

Kernel
    Release version of the kernel on the local host as reported by ``uname``.

Lustre
    Version of Lustre available in the Zypper repositories.

PBS version
    Version of PBS available in the Zypper repositories.

SLES version
    Version of SLES read from ``/etc/os-release`` on the local host.

Serial number
    Manually populated by ``sat setrev`` and read back from
    ``/opt/cray/etc/site_info.yml``.

Site name
    Manually populated by ``sat setrev`` and read back from
    ``/opt/cray/etc/site_info.yml``.

Slurm version
    Version of Slurm available in the Zypper repositories.

System install date
    Manually populated by ``sat setrev`` and read back from
    ``/opt/cray/etc/site_info.yml``.

System name
    Manually populated by ``sat setrev`` and read back from
    ``/opt/cray/etc/site_info.yml``.

System type
    Manually populated by ``sat setrev`` and read back from
    ``/opt/cray/etc/site_info.yml``.

The **--docker** option displays information about all installed docker
images in a table. This table is sorted on the docker image name. This
table has 3 columns; one for the image's name, its unique short-id, and
its version.

The **--packages** option displays information about installed RPM packages.
This output is a 2-column table with the first column containing the
package-name and the second containing its version. This table is sorted by
package-name.

OPTIONS
=======

These options must be specified after the subcommand.

**--system**
        Display general version information about the system. When none of the
        other options are specified, this option is enabled by default.

**--products**
        Display version information about the installed products. When none of
        the other options are specified, this option is enabled by default.

**--docker**
        Display information about the containers installed on this node.

**--packages**
        Display information about the installed packages on this node.

**--all**
        Display everything. Equivalent to specifying **--system**,
        **--products**, **--docker**, and **--packages**.

**-s** *SUBSTR*, **--substr** *SUBSTR*
        Show version information for components whose names or IDs contain
        the substring.

**--sitefile** *file*
        Specify custom site information file printed by --system. This file
        must be in a YAML format.

**-h, --help**
        Print the help message for ``sat showrev``.

.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

FILES
=====

This section references the extra files that this command requires for its
operation. Their default locations are also listed.

config: /etc/sat.toml
        The location of the site_info file can be configured within this
        file. The **--sitefile** command-line parameter may also be used.

site_info: /opt/cray/etc/site_info.yml
        Showrev uses this file to display the Serial number, Site name,
        System install date, System name, and System type fields.

release: /opt/cray/etc/release
        Showrev parses this file to collect information for the CLE
        version, General, PE, SLES version, SAT, and Urika fields.

SEE ALSO
========

sat(8)

.. include:: _notice.rst
