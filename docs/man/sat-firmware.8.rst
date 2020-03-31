==============
 SAT-FIRMWARE
==============

---------------------
Show firmware version
---------------------

:Author: Cray Inc.
:Copyright: Copyright 2020 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **firmware** [options]

DESCRIPTION
===========

The firmware subcommand reports firmware versions. Tabular output includes
the xname, the ID for the firmware element, and the firmware version. There
can be multiple IDs per xname. The firmware versions for all system components
are reported by default. Alternatively, a set of xnames can be specified.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Get a report of all the firmware versions on the system:

::

  # sat firmware
  +--------------+-------+-------------------------------------------+
  | xname        | ID    | version                                   |
  +--------------+-------+-------------------------------------------+
  | x3000c0s11b0 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s11b0 | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s11b0 | ME    | 04.01.04.251                              |
  | x3000c0s11b0 | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s11b0 | HSBP1 | 01.21                                     |
  | x3000c0s13b0 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s13b0 | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s13b0 | HSBP1 | 01.21                                     |
  | x3000c0s15b0 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s15b0 | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s15b0 | ME    | 04.01.04.251                              |
  | x3000c0s15b0 | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s15b0 | HSBP1 |                                           |
  | x3000c0s17b1 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s17b1 | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s17b1 | ME    | 04.01.04.251                              |
  | x3000c0s17b1 | SDR   | 1.39 (585433 bytes)                       |
  | x3000c0s17b1 | HSBP1 |                                           |
  | x3000c0s17b2 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s17b2 | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s17b2 | ME    | 04.01.04.251                              |
  | x3000c0s17b2 | SDR   | 1.39 (585433 bytes)                       |
  | x3000c0s17b2 | HSBP1 | 01.21                                     |
  | x3000c0s17b3 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s17b3 | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s17b3 | ME    | 04.00.04.294                              |
  | x3000c0s17b3 | SDR   | 1.39 (585433 bytes)                       |
  | x3000c0s17b3 | HSBP1 | 01.21                                     |
  | x3000c0s17b4 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s17b4 | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s17b4 | ME    | 04.00.04.294                              |
  | x3000c0s17b4 | SDR   | 1.39 (585433 bytes)                       |
  | x3000c0s17b4 | HSBP1 | 01.21                                     |
  | x3000c0s1b0  | BMC   | 1.93.870cf4f0                             |
  | x3000c0s1b0  | BIOS  | SE5C620.86B.02.01.0008.031920191559       |
  | x3000c0s1b0  | ME    | 04.01.04.251                              |
  | x3000c0s1b0  | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s1b0  | HSBP1 | 01.21                                     |
  | x3000c0s24b0 | BMC   | 1.93.870cf4f0                             |
  | x3000c0s24b0 | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s24b0 | ME    | 04.01.04.251                              |
  | x3000c0s24b0 | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s24b0 | HSBP1 | 01.21                                     |
  | x3000c0s3b0  | BMC   | 1.93.870cf4f0                             |
  | x3000c0s3b0  | BIOS  | SE5C620.86B.02.01.0008.031920191559       |
  | x3000c0s3b0  | ME    | 04.01.04.251                              |
  | x3000c0s3b0  | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s3b0  | HSBP1 | 01.21                                     |
  | x3000c0s5b0  | BMC   | 1.93.870cf4f0                             |
  | x3000c0s5b0  | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s5b0  | ME    | 04.01.04.251                              |
  | x3000c0s5b0  | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s5b0  | HSBP1 | 01.21                                     |
  | x3000c0s9b0  | BMC   | 1.93.870cf4f0                             |
  | x3000c0s9b0  | BIOS  | SE5C620.86B.02.01.0008.C0001.031920191559 |
  | x3000c0s9b0  | ME    | 04.01.04.251                              |
  | x3000c0s9b0  | SDR   | 1.93 (679092 bytes)                       |
  | x3000c0s9b0  | HSBP1 | 01.21                                     |
  +--------------+-------+-------------------------------------------+

SEE ALSO
========

sat(8)
