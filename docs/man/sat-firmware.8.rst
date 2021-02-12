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


OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

**--snapshots**
        Print versions of devices associated with the provided snapshot
        names. Provide this option with no arguments to print a list
        of available snapshots.

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
  | x3000c0s2b0  | 2          | System ROM                                      | A43 v1.30 (07/18/2020)  |
  | x3000c0s2b0  | 14         | Embedded Video Controller                       | 2.5                     |
  | x3000c0s2b0  | 1          | iLO 5                                           | 2.18 Jun 22 2020        |
  | x3000c0s2b0  | 13         | Marvell 2P 25GbE SFP28 QL41232HQCU-HC OCP3 Adap | 08.50.78                |
  | x3000c0s2b0  | 9          | Intelligent Provisioning                        | 3.45.6                  |
  | x3000c0s2b0  | 12         | Marvell FastLinQ 41000 Series - 2P 25GbE SFP28  | 08.50.78                |
  | x3000c0s2b0  | 5          | Power Management Controller Firmware            | 1.0.7                   |
  | x3000c0s2b0  | 3          | Intelligent Platform Abstraction Data           | 5.5.0 Build 28          |
  | x3000c0s2b0  | 6          | Power Supply Firmware                           | 1.00                    |
  | x3000c0s2b0  | 8          | Redundant System ROM                            | A43 v1.26 (05/11/2020)  |
  | x3000c0s2b0  | 4          | System Programmable Logic Device                | 0x0D                    |
  ...

SEE ALSO
========

sat(8)

.. include:: _notice.rst
