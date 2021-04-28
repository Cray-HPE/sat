============
 SAT-SENSORS
============

-----------------------
Display Sensor Readings
-----------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2020-2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **sensors** [options]

DESCRIPTION
===========

The sensors subcommand obtains sensor readings from telemetry data for
one or more BMCs.

This subcommand allows use of the "--xname" options. The provided xnames
must refer to BMCs, which may be of any BMC type: ChassisBMC, NodeBMC, and
RouterBMC, or components that contain such BMCs (such as a chassis). If no
xname is specified, all BMCs are targeted.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

**-t, --types**
        Select xnames that are of this type. Allowed types are **ChassisBMC**,
        **NodeBMC**, and **RouterBMC**. This argument may be reused to select
        more than one type.

**--topics**
        Limit the telemetry topics queried to the topics listed.
        The default is to query all topics.  Allowed topics are
        **cray-telemetry-temperature**, **cray-telemetry-voltage**,
        **cray-telemetry-power**, **cray-telemetry-energy**,
        **cray-telemetry-fan**, and **cray-telemetry-pressure**.

**-b, --batch-size** *BATCHSIZE*
        Number of metrics in each message. Defaults to 16.

**--timeout** *TIMEOUT*
        Total timeout, in seconds, for receiving data from telemetry topics.
        Defaults to 60.

**-r, --recursive**
        Include all BMCs for Chassis xnames specified by xXcC.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst
.. include:: _sat-redfish-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Query cray-telemetry-voltage sensor data for the NodeBMC x9000c3s0b0 (truncated to ten rows):

::

  # sat sensors -x x9000c3s0b0 --topics cray-telemetry-voltage
  +-------------+---------+------------------------+--------------------------------+---------------+------------------+----------------+------------------+-------+---------------------+------------+
  | xname       | Type    | Topic                  | Timestamp                      | Location      | Parental Context | Parental Index | Physical Context | Index | Physical Subcontext | Value      |
  +-------------+---------+------------------------+--------------------------------+---------------+------------------+----------------+------------------+-------+---------------------+------------+
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.422659252Z | x9000c3s0b0   | Chassis          | MISSING        | VoltageRegulator | 0     | Input               | 12.188     |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.686268094Z | x9000c3s0b0   | Chassis          | MISSING        | VoltageRegulator | 0     | Output              | 12.219     |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.422665411Z | x9000c3s0b0n0 | Chassis          | MISSING        | VoltageRegulator | 0     | Output              | 48.020     |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.526852747Z | x9000c3s0b0n0 | Chassis          | MISSING        | VoltageRegulator | 0     | Input               | 384.400000 |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.408473275Z | x9000c3s0b0n1 | Chassis          | MISSING        | VoltageRegulator | 0     | Output              | 48.100     |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.525601474Z | x9000c3s0b0n1 | Chassis          | MISSING        | VoltageRegulator | 0     | Input               | 385.300000 |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:45.394037018Z | x9000c3s0b0n0 | CPU              | 0              | VoltageRegulator | 4     | Output              | 1.098      |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:45.398475031Z | x9000c3s0b0n1 | CPU              | 0              | VoltageRegulator | 4     | Output              | 1.129      |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.295801008Z | x9000c3s0b0n0 | NetworkingDevice | 0              | VoltageRegulator | 0     | Input               | 11.875     |
  | x9000c3s0b0 | NodeBMC | cray-telemetry-voltage | 2021-04-28T18:18:44.696714969Z | x9000c3s0b0n0 | NetworkingDevice | 0              | VoltageRegulator | 0     | Output              | 0.961      |
  +-------------+---------+------------------------+--------------------------------+---------------+------------------+----------------+------------------+-------+---------------------+------------+

Query all sensor data for the ChassisBMC x9000c3b0 and sort by Timestamp (truncated to ten rows):

::

  # sat sensors -x x9000c3b0 --sort-by Timestamp
  +-----------+------------+----------------------------+--------------------------------+----------+------------------+------------------+-------+---------------------+-------------------------+--------+
  | xname     | Type       | Topic                      | Timestamp                      | Location | Parental Context | Physical Context | Index | Physical Subcontext | Device Specific Context | Value  |
  +-----------+------------+----------------------------+--------------------------------+----------+------------------+------------------+-------+---------------------+-------------------------+--------+
  | x9000c3b0 | ChassisBMC | cray-telemetry-power       | 2021-04-28T18:28:55.900552558Z | x9000c3  | MISSING          | Rectifier        | 1     | Input               | Line1                   | 0.86   |
  | x9000c3b0 | ChassisBMC | cray-telemetry-voltage     | 2021-04-28T18:28:55.948998743Z | x9000c3  | MISSING          | Rectifier        | 1     | Input               | Line2ToLine3            | 479.38 |
  | x9000c3b0 | ChassisBMC | cray-telemetry-power       | 2021-04-28T18:28:55.972008719Z | x9000c3  | MISSING          | Rectifier        | 0     | Output              | MISSING                 | 0.42   |
  | x9000c3b0 | ChassisBMC | cray-telemetry-pressure    | 2021-04-28T18:28:56.008416333Z | x9000c3  | Chassis          | LiquidInlet      | 0     | Input               | MISSING                 | 40.79  |
  | x9000c3b0 | ChassisBMC | cray-telemetry-pressure    | 2021-04-28T18:28:56.016107803Z | x9000c3  | Chassis          | LiquidOutlet     | 0     | Output              | MISSING                 | 24.90  |
  | x9000c3b0 | ChassisBMC | cray-telemetry-voltage     | 2021-04-28T18:28:56.020609014Z | x9000c3  | MISSING          | Rectifier        | 1     | Input               | Line1ToLine2            | 481.05 |
  | x9000c3b0 | ChassisBMC | cray-telemetry-power       | 2021-04-28T18:28:56.044158912Z | x9000c3  | MISSING          | Rectifier        | 0     | Input               | Line3                   | 0.75   |
  | x9000c3b0 | ChassisBMC | cray-telemetry-voltage     | 2021-04-28T18:28:56.067654295Z | x9000c3  | MISSING          | Rectifier        | 0     | Output              | MISSING                 | 385.08 |
  | x9000c3b0 | ChassisBMC | cray-telemetry-power       | 2021-04-28T18:28:56.092433509Z | x9000c3  | MISSING          | Rectifier        | 0     | Input               | Line2                   | 0.73   |
  | x9000c3b0 | ChassisBMC | cray-telemetry-voltage     | 2021-04-28T18:28:56.120402624Z | x9000c3  | MISSING          | Rectifier        | 0     | Input               | Line3ToLine1            | 481.96 |
  +-----------+------------+----------------------------+--------------------------------+----------+------------------+------------------+-------+---------------------+-------------------------+--------+

Query all sensor data for the Chassis x9000c3 recursively to include all BMCs and sort by Timestamp (truncated to ten rows):

::

  # sat sensors -x x9000c3 -r --sort-by Timestamp
  +-------------+------------+----------------------------+--------------------------------+---------------+----------------------+----------------+------------------+---------+---------------------+-------------------------+------------+
  | xname       | Type       | Topic                      | Timestamp                      | Location      | Parental Context     | Parental Index | Physical Context | Index   | Physical Subcontext | Device Specific Context | Value      |
  +-------------+------------+----------------------------+--------------------------------+---------------+----------------------+----------------+------------------+---------+---------------------+-------------------------+------------+
  | x9000c3b0   | ChassisBMC | cray-telemetry-voltage     | 2021-04-28T18:36:11.872311239Z | x9000c3       | MISSING              | MISSING        | Rectifier        | 1       | Input               | Line2ToLine3            | 481.86     |
  | x9000c3b0   | ChassisBMC | cray-telemetry-voltage     | 2021-04-28T18:36:11.924254063Z | x9000c3       | MISSING              | MISSING        | Rectifier        | 1       | Input               | Line1ToLine2            | 483.58     |
  | x9000c3s0b0 | NodeBMC    | cray-telemetry-power       | 2021-04-28T18:36:11.951742109Z | x9000c3s0b0n0 | Chassis              | MISSING        | VoltageRegulator | 0       | Output              | MISSING                 | 473.000    |
  | x9000c3s0b0 | NodeBMC    | cray-telemetry-power       | 2021-04-28T18:36:11.952051048Z | x9000c3s0b0n1 | Chassis              | MISSING        | VoltageRegulator | 0       | Output              | MISSING                 | 564.000    |
  | x9000c3b0   | ChassisBMC | cray-telemetry-voltage     | 2021-04-28T18:36:11.971646561Z | x9000c3       | MISSING              | MISSING        | Rectifier        | 0       | Output              | MISSING                 | 385.12     |
  | x9000c3r7b0 | RouterBMC  | cray-telemetry-power       | 2021-04-28T18:36:12.005161185Z | x9000c3r7b0   | ASIC                 | MISSING        | VoltageRegulator | 7       | Output              | MISSING                 | 11.750     |
  | x9000c3r7b0 | RouterBMC  | cray-telemetry-power       | 2021-04-28T18:36:12.007660739Z | x9000c3r7b0   | ASIC                 | MISSING        | VoltageRegulator | 5       | Output              | MISSING                 | 77.100     |
  | x9000c3r7b0 | RouterBMC  | cray-telemetry-power       | 2021-04-28T18:36:12.009084804Z | x9000c3r7b0   | ASIC                 | MISSING        | VoltageRegulator | 5       | Input               | MISSING                 | 6.220      |
  | x9000c3r7b0 | RouterBMC  | cray-telemetry-power       | 2021-04-28T18:36:12.013204650Z | x9000c3r7b0   | ASIC                 | MISSING        | VoltageRegulator | 4       | Output              | MISSING                 | 46.200     |
  | x9000c3r7b0 | RouterBMC  | cray-telemetry-power       | 2021-04-28T18:36:12.014466967Z | x9000c3r7b0   | ASIC                 | MISSING        | VoltageRegulator | 4       | Input               | MISSING                 | 3.790      |
  +-------------+------------+----------------------------+--------------------------------+---------------+----------------------+----------------+------------------+---------+---------------------+-------------------------+------------+


SEE ALSO
========

sat(8)

.. include:: _notice.rst
