============
 SAT-HWHIST
============

----------------------------------
Display Hardware Component History
----------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **hwhist** [options]

DESCRIPTION
===========

The hwhist subcommand reports the history of the Field Replaceable Units (FRUs)
in the system. The FRU history can be reported either by location (xname) or
by a unique identifier for that FRU called the FRUID.

If no xnames or FRUIDs are specified, the history of all FRUs is reported
by xname.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

**--by-fru**
        Display the hardware component history by FRU. The by-fru option
        is not valid with the xnames options.  When by-fru is specified
        without any FRUIDs, the history of all FRUs is reported
        by FRUID.

**--fruid** *FRUID*, **--fruids** *FRUID*
        A comma-separated list of FRUIDs to include in the report.
        If this option is used, the by-fru option is automatically set.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Report the FRU history for the processor located at xname: x1000c3s4b0n1p0:

::

  # sat hwhist --xname x1000c3s4b0n1p0
  +-----------------+-------------------------------------------------+-----------------------------+-----------+
  | xname           | FRUID                                           | Timestamp                   | EventType |
  +-----------------+-------------------------------------------------+-----------------------------+-----------+
  | x1000c3s4b0n1p0 | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | 2021-03-18T19:18:01.657016Z | Added     |
  | x1000c3s4b0n1p0 | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | 2021-03-29T16:49:57.983025Z | Removed   |
  | x1000c3s4b0n1p0 | Processor.AdvancedMicroDevicesInc.9KB2525W00087 | 2021-03-29T16:49:57.987507Z | Added     |
  | x1000c3s4b0n1p0 | Processor.AdvancedMicroDevicesInc.9KB2525W00087 | 2021-03-29T19:32:04.43173Z  | Removed   |
  | x1000c3s4b0n1p0 | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | 2021-03-29T19:32:04.43664Z  | Added     |
  | x1000c3s4b0n1p0 | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | 2021-05-13T15:10:42.012758Z | Scanned   |
  | x1000c3s4b0n1p0 | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | 2021-05-21T03:17:25.463946Z | Detected  |
  +-------------------------------------------------+-----------------+-----------------------------+-----------+

Report the FRU history for the processor with FRUID: Processor.AdvancedMicroDevicesInc.9KB2525W00198:

::

  # sat hwhist --fruid Processor.AdvancedMicroDevicesInc.9KB2525W00198
  +-------------------------------------------------+-----------------+-----------------------------+-----------+
  | FRUID                                           | xname           | Timestamp                   | EventType |
  +-------------------------------------------------+-----------------+-----------------------------+-----------+
  | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | x1000c3s4b0n1p0 | 2021-03-18T19:18:01.657016Z | Added     |
  | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | x1000c3s4b0n1p0 | 2021-03-29T16:49:57.983025Z | Removed   |
  | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | x1000c3s4b0n1p1 | 2021-03-29T16:49:57.987507Z | Added     |
  | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | x1000c3s4b0n1p1 | 2021-03-29T19:32:04.43173Z  | Removed   |
  | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | x1000c3s4b0n1p0 | 2021-03-29T19:32:04.43664Z  | Added     |
  | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | x1000c3s4b0n1p0 | 2021-05-13T15:10:42.012758Z | Scanned   |
  | Processor.AdvancedMicroDevicesInc.9KB2525W00198 | x1000c3s4b0n1p0 | 2021-05-21T03:17:25.463946Z | Detected  |
  +-------------------------------------------------+-----------------+-----------------------------+-----------+

Report the FRU history for the memory located at xname: x3000c0s25b0n0d19 and filter by EventType:

::

  sat hwhist -x x3000c0s25b0n0d19 --filter eventtype=Added
  +-------------------+-----------------------------------------+-----------------------------+-----------+
  | xname             | FRUID                                   | Timestamp                   | EventType |
  +-------------------+-----------------------------------------+-----------------------------+-----------+
  | x3000c0s25b0n0d19 | Memory.Micron.18ASF2G72PZ3G2E2.23D75423 | 2021-03-17T20:21:53.403648Z | Added     |
  | x3000c0s25b0n0d19 | Memory.Hynix.HMA82GR7CJR8NXN.3469DF66   | 2021-04-27T13:55:17.509194Z | Added     |
  +-------------------+-----------------------------------------+-----------------------------+-----------+

SEE ALSO
========

sat(8)

.. include:: _notice.rst
