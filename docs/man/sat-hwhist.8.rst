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

The hwhist subcommand reports the history of the Field Replacement Units(FRUs)
in the system. The FRU history can be reported either by location (xname) or
by FRUID.

If no xnames or fruids are specified, the history of all FRUs is reported
by xname.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

**--by-fru**
        Display the hardware component history by FRU. The by-fru option
        is not valid with the xnames options.  When by-fru is specified
        without any fruids, the history of all FRUs is reported
        by FRUID.

**-fruid** *FRUID*, **--fruids** *FRUID*
        A comma-separated list of FRUIDs to include in the report.
        If this option is used, the by-fru option is automatically set.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Report the FRU history for the processor located at xname: x3000c0s3b0n0p0:

::

  # sat hwhist --xname x3000c0s3b0n0p0
  +-----------------+---------------------------------------------------+-----------------------------+-----------+
  | xname           | FRUID                                             | Timestamp                   | EventType |
  +-----------------+---------------------------------------------------+-----------------------------+-----------+
  | x3000c0s3b0n0p0 | Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6 | 2021-06-02T18:37:31.619581Z | Detected  |
  | x3000c0s3b0n0p0 | Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6 | 2021-06-16T14:42:49.528142Z | Detected  |
  | x3000c0s3b0n0p0 | Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6 | 2021-06-17T17:20:52.326343Z | Detected  |
  | x3000c0s3b0n0p0 | Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6 | 2021-06-24T21:45:22.485414Z | Detected  |
  | x3000c0s3b0n0p0 | Processor.AdvancedMicroDevicesInc.2B48CBA44CEC0D6 | 2021-07-27T00:10:15.649104Z | Detected  |
  +-----------------+---------------------------------------------------+-----------------------------+-----------+

Report the FRU history for the power supply with FRUID: NodeEnclosurePowerSupply.LiteonPower.6K9L10103I1236Ukkj:

::

  # sat hwhist --fruid NodeEnclosurePowerSupply.LiteonPower.6K9L10103I1236U
  +------------------------------------------------------+----------------+-----------------------------+-----------+
  | FRUID                                                | xname          | Timestamp                   | EventType |
  +------------------------------------------------------+----------------+-----------------------------+-----------+
  | NodeEnclosurePowerSupply.LiteonPower.6K9L10103I1236U | x3000c0s17e0t1 | 2021-06-02T18:37:34.623145Z | Detected  |
  | NodeEnclosurePowerSupply.LiteonPower.6K9L10103I1236U | x3000c0s17e0t1 | 2021-06-16T14:42:58.449096Z | Detected  |
  | NodeEnclosurePowerSupply.LiteonPower.6K9L10103I1236U | x3000c0s17e0t1 | 2021-06-17T17:20:53.450429Z | Detected  |
  | NodeEnclosurePowerSupply.LiteonPower.6K9L10103I1236U | x3000c0s17e0t1 | 2021-06-24T21:45:23.952613Z | Detected  |
  | NodeEnclosurePowerSupply.LiteonPower.6K9L10103I1236U | x3000c0s17e0t1 | 2021-07-27T00:10:29.759025Z | Detected  |
  +------------------------------------------------------+----------------+-----------------------------+-----------+


SEE ALSO
========

sat(8)

.. include:: _notice.rst
