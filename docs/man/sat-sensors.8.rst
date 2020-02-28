============
 SAT-SENSORS
============

-------------------------------
Display Current Sensor Readings
-------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2020 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **sensors** [options]

DESCRIPTION
===========

The sensors subcommand obtains current sensor readings from
one or more BMCs.

OPTIONS
=======

These options must be specified after the subcommand.
The xnames may also be IP addresses.

**-h, --help**
        Print a usage summary and exit.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst
.. include:: _sat-redfish-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Sample Output
-------------

A River node, truncated to ten rows::

  # sat sensors -x x0c0s11b0
  +-----------+---------------+--------------------+------------------+------------------+---------------------+-------+-------------+---------+-------+
  | bmc       | sensor number | electrical context | device context   | physical context | physical subcontext | index | sensor type | reading | units |
  +-----------+---------------+--------------------+------------------+------------------+---------------------+-------+-------------+---------+-------+
  | x0c0s11b0 | 208           | None               | BB +12.0V        | SystemBoard      | None                | None  | Voltage     | 12.157  | V     |
  | x0c0s11b0 | 222           | None               | BB +3.3V Vbat    | SystemBoard      | None                | None  | Voltage     | 3.0745  | V     |
  | x0c0s11b0 | 0             | None               | Power Supply Bay | None             | None                | None  | Voltage     | 176     | V     |
  | x0c0s11b0 | 1             | None               | Power Supply Bay | None             | None                | None  | Voltage     | 8       | V     |
  | x0c0s11b0 | 20            | None               | BB Lft Rear Temp | None             | None                | None  | Temperature | 30      | Cel   |
  | x0c0s11b0 | 23            | None               | Riser 3 Temp     | None             | None                | None  | Temperature | 27      | Cel   |
  | x0c0s11b0 | 32            | None               | BB P1 VR Temp    | None             | None                | None  | Temperature | 32      | Cel   |
  | x0c0s11b0 | 33            | None               | Front Panel Temp | None             | None                | None  | Temperature | 22      | Cel   |
  | x0c0s11b0 | 34            | None               | SSB Temp         | None             | None                | None  | Temperature | 41      | Cel   |
  | x0c0s11b0 | 35            | None               | BB P2 VR Temp    | None             | None                | None  | Temperature | 31      | Cel   |
  +-----------+---------------+--------------------+------------------+------------------+---------------------+-------+-------------+---------+-------+

Specific sensors, from a selection of nodes::

  # sat sensors -x x3000c0s19b1,x3000c0s19b2,x3000c0s19b3,x3000c0s19b4 --filter "number=208 or number=222"
  +--------------+---------------+--------------------+----------------+------------------+---------------------+-------+-------------+---------+-------+
  | bmc          | sensor number | electrical context | device context | physical context | physical subcontext | index | sensor type | reading | units |
  +--------------+---------------+--------------------+----------------+------------------+---------------------+-------+-------------+---------+-------+
  | x3000c0s19b1 | 208           | None               | BB +12.0V      | SystemBoard      | None                | None  | Voltage     | 11.992  | V     |
  | x3000c0s19b1 | 222           | None               | BB +3.3V Vbat  | SystemBoard      | None                | None  | Voltage     | 3.0095  | V     |
  | x3000c0s19b2 | 208           | None               | BB +12.0V      | SystemBoard      | None                | None  | Voltage     | 12.102  | V     |
  | x3000c0s19b2 | 222           | None               | BB +3.3V Vbat  | SystemBoard      | None                | None  | Voltage     | 2.9965  | V     |
  | x3000c0s19b3 | 208           | None               | BB +12.0V      | SystemBoard      | None                | None  | Voltage     | 12.212  | V     |
  | x3000c0s19b3 | 222           | None               | BB +3.3V Vbat  | SystemBoard      | None                | None  | Voltage     | 3.0225  | V     |
  | x3000c0s19b4 | 208           | None               | BB +12.0V      | SystemBoard      | None                | None  | Voltage     | 12.157  | V     |
  | x3000c0s19b4 | 222           | None               | BB +3.3V Vbat  | SystemBoard      | None                | None  | Voltage     | 3.0095  | V     |
  +--------------+---------------+--------------------+----------------+------------------+---------------------+-------+-------------+---------+-------+


SEE ALSO
========

sat(8)
