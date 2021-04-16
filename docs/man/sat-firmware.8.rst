==============
 SAT-FIRMWARE
==============

---------------------
Show firmware version
---------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020-2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **firmware** [options]

DESCRIPTION
===========

The firmware subcommand reports firmware versions. Tabular output includes
the xname, the name of the firmware element, and the firmware version. Additionally,
some firmware elements may report a different value for the field 'target_name',
so both 'name' and 'target_name' are included in the output.

There can be multiple rows in the table per xname. The firmware versions for
all system components are reported by default. Alternatively, a set of xnames
can be specified.

One or more snapshots may be specified to report firmware versions associated
with a particular snapshot. Xnames and snapshots can be specified together to
return results from the given snapshots pertaining to the given xnames.


OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

**--snapshots**
        Print versions of devices associated with the provided snapshot
        names. Provide this option with no arguments to print a list of
        available snapshots.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Get a report of all the firmware versions on the system (note: output truncated):

::

  # sat firmware
  +--------------+------------+-------------------------------------------------+-------------------------+
  | xname        | name       | target_name                                     | version                 |
  +--------------+------------+-------------------------------------------------+-------------------------+
  | x3000c0r39b0 | Recovery   | Recovery                                        | generic arm64 recovery  |
  | x3000c0r39b0 | Packages   | Packages                                        | na                      |
  | x3000c0r39b0 | Bootloader | Bootloader                                      | 1.0-g550986e-sc-ros-tor |
  | x3000c0r39b0 | FPGA1      | sFPGA-ROS-TOR                                   | 1.04                    |
  | x3000c0r39b0 | FPGA0      | sFPGA-ROS                                       | 1.08                    |
  | x3000c0r39b0 | BMC        | BMC                                             | sc.1.4.409              |
  | x3000c0s2b0  | 11         | TPM Firmware                                    | 73.64                   |
  | x3000c0s2b0  | 10         | Power Management Controller FW Bootloader       | 1.1                     |
  | x3000c0s2b0  | 7          | Power Supply Firmware                           | 1.00                    |
  ...

Get a report of all the firmware versions associated with a particular xname:

::

  # sat firmware --xname x3000c0r39b0
  +--------------+------------+-------------------------------------------------+-------------------------+
  | xname        | name       | target_name                                     | version                 |
  +--------------+------------+-------------------------------------------------+-------------------------+
  | x3000c0r39b0 | Recovery   | Recovery                                        | generic arm64 recovery  |
  | x3000c0r39b0 | Packages   | Packages                                        | na                      |
  | x3000c0r39b0 | Bootloader | Bootloader                                      | 1.0-g550986e-sc-ros-tor |
  | x3000c0r39b0 | FPGA1      | sFPGA-ROS-TOR                                   | 1.04                    |
  | x3000c0r39b0 | FPGA0      | sFPGA-ROS                                       | 1.08                    |
  | x3000c0r39b0 | BMC        | BMC                                             | sc.1.4.409              |
  +--------------+------------+-------------------------------------------------+-------------------------+

Get a report of all the firmware versions associated with a particular snapshot
(note: output truncated):

::

  # sat firmware --snapshots firmware-2021-3-2-23-45-52
  ################################################################################
  firmware-2021-3-2-23-45-52
  ################################################################################
  +--------------+------------+-------------------------------------------------+-------------------------+
  | xname        | name       | target_name                                     | version                 |
  +--------------+------------+-------------------------------------------------+-------------------------+
  | x3000c0r39b0 | Recovery   | Recovery                                        | generic arm64 recovery  |
  | x3000c0r39b0 | Packages   | Packages                                        | na                      |
  | x3000c0r39b0 | Bootloader | Bootloader                                      | 1.0-g550986e-sc-ros-tor |
  | x3000c0r39b0 | FPGA1      | sFPGA-ROS-TOR                                   | 1.04                    |
  | x3000c0r39b0 | FPGA0      | sFPGA-ROS                                       | 1.08                    |
  | x3000c0r39b0 | BMC        | BMC                                             | sc.1.4.409              |
  | x3000c0s2b0  | 11         | TPM Firmware                                    | 73.64                   |
  | x3000c0s2b0  | 10         | Power Management Controller FW Bootloader       | 1.1                     |
  | x3000c0s2b0  | 7          | Power Supply Firmware                           | 1.00                    |
  ...

Get a report of all the firmware versions associated with a particular snapshot
and a particular xname:

::

  # sat firmware --snapshots firmware-2021-3-2-23-45-52 --xname x3000c0r39b0
  ################################################################################
  firmware-2021-3-2-23-45-52
  ################################################################################
  +--------------+------------+-------------------------------------------------+-------------------------+
  | xname        | name       | target_name                                     | version                 |
  +--------------+------------+-------------------------------------------------+-------------------------+
  | x3000c0r39b0 | Recovery   | Recovery                                        | generic arm64 recovery  |
  | x3000c0r39b0 | Packages   | Packages                                        | na                      |
  | x3000c0r39b0 | Bootloader | Bootloader                                      | 1.0-g550986e-sc-ros-tor |
  | x3000c0r39b0 | FPGA1      | sFPGA-ROS-TOR                                   | 1.04                    |
  | x3000c0r39b0 | FPGA0      | sFPGA-ROS                                       | 1.08                    |
  | x3000c0r39b0 | BMC        | BMC                                             | sc.1.4.409              |
  +--------------+------------+-------------------------------------------------+-------------------------+

List all firmware snapshot names:

::

  # sat firmware --snapshots
  firmware-2021-3-2-23-45-52
  firmware-2021-3-2-20-41-55

SEE ALSO
========

sat(8)

.. include:: _notice.rst
