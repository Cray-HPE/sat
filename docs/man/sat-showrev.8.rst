=============
 SAT-SHOWREV
=============

------------------------------------------
Print version information about the system
------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2021,2023,2024 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **showrev** [options]

DESCRIPTION
===========

The showrev subcommand prints revision information about the system.
This includes general version information about the system, as well as
version information about installed HPE products.

The default behavior of this command is to print general revision information
about the system and the installed products. This consists of three tables:
system-wide information, product information read from Kubernetes, and local
host operating system information.

The system-wide revision information table is a combination of system-wide
information (for example, interconnect) and site-specific information.
Site information is entered with the **sat setrev** command.

The product information read from Kubernetes includes product name, product
version, image names and image recipes (if available). It reads information
from the ``cray-product-catalog`` Kubernetes configuration map. If multiple
versions of the same product are present, all versions will be listed.

Previous versions of **sat showrev** included an "active" column in the product
information table, where products designated "active" within the configuration
map would have a value of ``True`` in this column. This has been removed in the
current version of **sat showrev**, and there is no longer an "active" column.

**sat showrev** downloads this site information from the configured S3 bucket if
available, otherwise a local copy of the site information file is used, if it
exists. The default local path for the site information file is
``/opt/cray/etc/site_info.yml``.

Local host operating system information is specific to the host on which
**sat showrev** is running, and it includes Linux kernel version and operating
system distribution version.

The following list details the meaning and source of information for each
field in the system-wide information table.

Interconnect
    Unique list of interconnect names obtained from the Hardware State
    Manager (HSM).

Serial number
    Manually populated by ``sat setrev`` and read back from the configured S3
    bucket, or ``/opt/cray/etc/site_info.yml``.

Site name
    Manually populated by ``sat setrev`` and read back from the configured S3
    bucket, or ``/opt/cray/etc/site_info.yml``.

Slurm version
    Version of Slurm as indicated by slurmctld.

System install date
    Manually populated by ``sat setrev`` and read back from the configured S3
    bucket, or ``/opt/cray/etc/site_info.yml``.

System name
    Manually populated by ``sat setrev`` and read back from the configured S3
    bucket, or ``/opt/cray/etc/site_info.yml``.

System type
    Manually populated by ``sat setrev`` and read back from the configured S3
    bucket, or ``/opt/cray/etc/site_info.yml``.

The following list details the meaning and source of information for each
field in the local host operating system information table.

Kernel
    Release version of the kernel on the local host as reported by ``uname``.

SLES version
    Version of SLES read from ``/etc/os-release`` on the local host.

    If ``/opt/cray/sat/etc/os-release`` exists, then SLES version will be read
    from that file instead. This is to facilitate running in a containerized
    environment. Inside a SAT container, ``/etc/os-release`` will contain
    information about the container operating system, not the host operating
    system. If ``/opt/cray/sat/etc/os-release`` exists, it is assumed to refer
    to the host operating system.

OPTIONS
=======

These options must be specified after the subcommand.

**--system**
        Display system-wide version information. When none of the other options
        are specified, this option is enabled by default.

**--products**
        Display version information about the installed products. When none of
        the other options are specified, this option is enabled by default.

**--local**
        Display local host operating system version information. When none of
        the other options are specified, this option is enabled by default.

**--release-files**
        The **--release-files** option is no longer supported. Use **--products** to
        see installed product versions instead. This option is not enabled by default.

**--all**
        Display everything. Equivalent to specifying **--system**,
        **--products**, **--local**, and **--release-files**.

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

site_info: /opt/cray/etc/site_info.yml
        Showrev uses this file to display the Serial number, Site name,
        System install date, System name, and System type fields. This file
        is downloaded from the configured S3 bucket on every invocation of
        **sat showrev** if it is available, otherwise a local copy is used.


EXAMPLES
========

Get system revision information:

::

  # sat showrev --system
  ################################################################################
  System Revision Information
  ################################################################################
  +---------------------+----------------------+
  | component           | data                 |
  +---------------------+----------------------+
  | Company name        | HPE                  |
  | Country code        | US                   |
  | Product number      | R4K98A               |
  | Serial number       | 123456               |
  | Site name           | HPE                  |
  | System Description  | Internal test system |
  | System install date | 2020-12-12           |
  | System name         | rocket               |
  | System type         | EX-1C                |
  | Interconnect        | Sling                |
  | Slurm version       | slurm 20.02.3        |
  +---------------------+----------------------+

Get product releases:

::

  # sat showrev --products
  ################################################################################
  Product Revision Information
  ################################################################################
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+
  | product_name | product_version | images                                      | image_recipes                               |
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+
  | analytics    | 1.0.0           | Cray-Analytics.x86_64-base                  | -                                           |
  | analytics    | base            | -                                           | -                                           |
  | cos          | 1.4.0           | cray-shasta-compute-sles15sp2.x86_64-1.4.51 | cray-shasta-compute-sles15sp2.x86_64-1.4.51 |
  | pbs          | 0.1.0           | -                                           | -                                           |
  | sat          | 2.1.0           | -                                           | -                                           |
  | sat          | 2.2.0           | -                                           | -                                           |
  | slurm        | 0.1.0           | -                                           | -                                           |
  | uan          | 2.0.0           | cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0  | cray-shasta-uan-cos-sles15sp1.x86_64-2.0.0  |
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+

Get the Slurm product version:

::

  # sat showrev --products --filter='product_name=slurm'
  ################################################################################
  Product Revision Information
  ################################################################################
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+
  | product_name | product_version | images                                      | image_recipes                               |
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+
  | slurm        | 0.1.0           | -                                           | -                                           |
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+

Get local host operating system information:

::

  # sat showrev --local

  ################################################################################
  Local Host Operating System
  ################################################################################
  +-----------+----------------------+
  | component | version              |
  +-----------+----------------------+
  | Kernel    | 5.3.18-24.29-default |
  | SLES      | SLES 15-SP2          |
  +-----------+----------------------+


SEE ALSO
========

sat(8)

.. include:: _notice.rst
