=============
 SAT-SHOWREV
=============

------------------------------------------
Print version information about the system
------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2019-2020 Hewlett Packard Enterprise Development LP.
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
about the system and the installed products. This is a mixture of product
version information read from Kubernetes, system information specific to the
host on which the command is running, and site information recorded by the
**sat setrev** command.

The product information read from Kubernetes includes product name, product
version, image names and image recipes (if available). It reads information
from the ``cray-product-catalog`` Kubernetes configuration map. If multiple
versions of the same product are present, all versions will be printed.

**sat showrev** downloads the site information from the configured S3 bucket if
available, otherwise a local copy of the site information file is used, if it
exists. The default local path for the site information file is
``/opt/cray/etc/site_info.yml``.

The following list details the meaning and source of information for each
field.

Interconnect
    Unique list of interconnect names obtained from the Hardware State
    Manager (HSM).

Kernel
    Release version of the kernel on the local host as reported by ``uname``.

Lustre
    Version of Lustre available in the Zypper repositories.

PBS version
    Version of PBS available in the Zypper repositories.

Release version
    Release version as indicated by ``/etc/cray-release``.

SLES version
    Version of SLES read from ``/etc/os-release`` on the local host.

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

**--release-files**
        Display version information installed in the ``/opt/cray/etc/release/``
        directory.  This option is not enabled by default and is included for
        compatibility with previous releases.

**--docker**
        Display information about the containers installed on this node.

**--packages**
        Display information about the installed packages on this node.

**--all**
        Display everything. Equivalent to specifying **--system**,
        **--products**, **--docker**, **--packages**, and **--release-files**.

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

release: /opt/cray/etc/release
        Showrev parses the files in this directory to collect information for
        the product releases. The fields shown in the output report are all
        the fields found in these files, along with the product file name.

EXAMPLES
========

Get product releases:

::

  # sat showrev --products
  ################################################################################
  Product Revision Information
  ################################################################################
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+
  | product_name | product_version | images                                      | image_recipes                               |
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+
  | analytics    | 1.0.0           | Cray-Analytics.x86_64-base                  | MISSING                                     |
  | analytics    | base            | MISSING                                     | MISSING                                     |
  | cos          | 1.4.0           | cray-shasta-compute-sles15sp2.x86_64-1.4.51 | cray-shasta-compute-sles15sp2.x86_64-1.4.51 |
  | pbs          | 0.1.0           | MISSING                                     | MISSING                                     |
  | slurm        | 0.1.0           | MISSING                                     | MISSING                                     |
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
  | slurm        | 0.1.0           | MISSING                                     | MISSING                                     |
  +--------------+-----------------+---------------------------------------------+---------------------------------------------+


SEE ALSO
========

sat(8)

.. include:: _notice.rst
