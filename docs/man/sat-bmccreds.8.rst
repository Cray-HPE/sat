==============
 SAT-BMCCREDS
==============

-----------------
Set BMC passwords
-----------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2021, 2024 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **bmccreds** [options]

DESCRIPTION
===========

The bmccreds subcommand sets BMC Redfish access passwords to user-defined or
randomly generated values.

When generating random passwords, the bmccreds subcommand can set components
within the same chassis, cabinet or entire system to the same randomly-generated
password, or it can use a different password for each component. This grouping
is controlled using the ``--pw-domain`` argument.

The length of generated passwords and the characters allowed in generated
passwords can be controlled with the options ``--password-length``,
``--password-char-sets``, and ``--password-chars``. See below for a full
description of those options.

It is possible to provide xnames to set the password for specific BMCs, or
to provide BMC types (e.g. NodeBMC, RouterBMC, ChassisBMC) to act on all BMCs
of the specified types. If both xnames and types are specified, the given
xnames will be filtered by the given types. If neither xnames nor types are
given, the operation will apply to all BMCs in the system. By default, xnames
are validated with the Hardware State Manager (HSM) to make sure they exist
and are enabled.

The bmccreds subcommand interacts with the System Configuration Service (SCSD)
to set Redfish access credentials on the specified BMCs and prints a report
describing the result of the operation.

OPTIONS
=======

**--password** *PASSWORD*
    Specify BMC password. If this option is not specified and
    **--random-password** is not specified, then the command will prompt for a
    password. Not valid with **--random-password**.

**--random-password**
    Generate random BMC password(s). If this option is not specified and
    **--password** is not given, then the user will be prompted to enter a
    password.  Not valid with **--password**.

**--password-length**
    The desired length of the random BMC password. Only valid with
    **--random-password**.

**--password-char-sets**
    A comma-separated list of allowed character sets to be used in a randomly
    generated password. Only valid with **--random-password**.
    Character sets are as follows: "alpha" includes all uppercase and lowercase
    ASCII letters, "numeric" includes digits 0-9, and "symbols" includes the symbols
    "!@#$%^&*".

**--password-chars**
    Specify explicit list of characters to generate random passwords. Only
    valid with **--random-password**.

**--pw-domain** *DOMAIN*
    Specify the domain or 'reach' of the password. Only valid with
    **--random-password**.

    Options are:

    system
        Use the same password for all specified BMCs (default).
    cabinet
        Use the same password for all BMCs within a cabinet. Use different
        passwords for BMCs in different cabinets.
    chassis
        Use the same password for all BMCs within a chassis. Use different
        passwords for BMCs in different chassis. (Note: this is the same
        as specifying **--pw-domain=cabinet** on air-cooled systems, which
        only have one chassis per cabinet).
    bmc
        Use a different password for all specified BMCs.

**--disruptive**
    Don't prompt for confirmation.

**--no-hsm-check**
    Don't consult HSM to check BMC eligibility. Requires xnames to be specified.
    This is used when BMC passwords need to be set but HSM is unavailable
    (emergency use).

**--include-disabled**
    Include BMCs which are discovered but currently disabled. Without this
    option disabled BMCs are ignored.

**--include-failed-discovery**
    Include BMCs for which discovery failed. Without this option, BMCs with
    discovery errors are ignored.

**--retries** *RETRIES*
    Number of times to retry setting credentials should the operation fail.
    Default: 3.

**--bmc-types** *TYPE [TYPE]...*
    Specify the BMC type to include in the operation. Valid types are: NodeBMC,
    ChassisBMC, and RouterBMC. More than one of these can be specified. The
    default is all BMC types. Types not specified will be excluded from
    consideration.

.. include:: _sat-xname-opts.rst
.. include:: _sat-format-opts.rst

EXAMPLES
========

Set all BMC passwords in the system to a user-defined password:

::

  # sat bmccreds
  BMC password:
  Confirm BMC password:

  +--------------+-----------+----------------------+-------------+----------------+
  | xname        | Type      | Password Type        | Status Code | Status Message |
  +--------------+-----------+----------------------+-------------+----------------+
  | x3000c0s26b3 | NodeBMC   | User, domain: system | 200         | OK             |
  | x3000c0s28b2 | NodeBMC   | User, domain: system | 200         | OK             |
  | x3000c0s15b0 | NodeBMC   | User, domain: system | 200         | OK             |
  ...

Set the BMC password for a single BMC to a user-defined password:

::

  # sat bmccreds --xname x3000c0s26b3
  BMC password:
  Confirm BMC password:

  +--------------+-----------+----------------------+-------------+----------------+
  | xname        | Type      | Password Type        | Status Code | Status Message |
  +--------------+-----------+----------------------+-------------+----------------+
  | x3000c0s26b3 | NodeBMC   | User, domain: system | 200         | OK             |
  +--------------+-----------+----------------------+-------------+----------------+


Set all Router BMC passwords in the system to a user-defined password:

::

  # sat bmccreds --bmc-types RouterBMC
  BMC password:
  Confirm BMC password:

  +--------------+-----------+----------------------+-------------+----------------+
  | xname        | Type      | Password Type        | Status Code | Status Message |
  +--------------+-----------+----------------------+-------------+----------------+
  | x3000c0r24b0 | RouterBMC | User, domain: system | 204         | No Content     |
  +--------------+-----------+----------------------+-------------+----------------+

Set every BMC password to the same randomly generated value:

::

  # sat bmccreds --random-password
  +--------------+-----------+------------------------+-------------+----------------+
  | xname        | Type      | Password Type          | Status Code | Status Message |
  +--------------+-----------+------------------------+-------------+----------------+
  | x3000c0s26b3 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s28b2 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s15b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  ...


Set every BMC password to the same randomly generated value of desired length:

::

  # sat bmccreds --random-password --password-length 20
  +--------------+-----------+------------------------+-------------+----------------+
  | xname        | Type      | Password Type          | Status Code | Status Message |
  +--------------+-----------+------------------------+-------------+----------------+
  | x3000c0s4b0  | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s18b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s17b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  ...


Set every BMC password to the same randomly generated value of desired char-sets:

::

  # sat bmccreds --random-password --password-char-sets alpha
  +--------------+-----------+------------------------+-------------+----------------+
  | xname        | Type      | Password Type          | Status Code | Status Message |
  +--------------+-----------+------------------------+-------------+----------------+
  | x3000c0s23b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s29b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s10b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  ...


Set every BMC password to the same randomly generated value of desired length and char-sets:

::

  # sat bmccreds --random-password --password-length 10 --password-char-sets alpha,numeric,symbols
  +--------------+-----------+------------------------+-------------+----------------+
  | xname        | Type      | Password Type          | Status Code | Status Message |
  +--------------+-----------+------------------------+-------------+----------------+
  | x3000c0s27b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s5b0  | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s9b0  | NodeBMC   | Random, domain: system | 200         | OK             |
  ...


Set every BMC password to the same randomly generated value with explicit characters:

::

  # sat bmccreds --random-password --password-chars 'abcd12134!@#'
  +--------------+-----------+------------------------+-------------+----------------+
  | xname        | Type      | Password Type          | Status Code | Status Message |
  +--------------+-----------+------------------------+-------------+----------------+
  | x3000c0s5b0  | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s24b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s2b0  | NodeBMC   | Random, domain: system | 200         | OK             |
  ...


Set every BMC password to the same randomly generated value of desired length with explicit characters:

::

  # sat bmccreds --random-password --password-length 10 --password-chars '123abcd$^&*'
  +--------------+-----------+------------------------+-------------+----------------+
  | xname        | Type      | Password Type          | Status Code | Status Message |
  +--------------+-----------+------------------------+-------------+----------------+
  | x3000c0s23b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s4b0  | NodeBMC   | Random, domain: system | 200         | OK             |
  | x3000c0s10b0 | NodeBMC   | Random, domain: system | 200         | OK             |
  ...


Set every BMC password to different randomly generated values:

::

  # sat bmccreds --random-password --pw-domain bmc
  +--------------+-----------+---------------------+-------------+----------------+
  | xname        | Type      | Password Type       | Status Code | Status Message |
  +--------------+-----------+---------------------+-------------+----------------+
  | x3000c0s26b3 | NodeBMC   | Random, domain: bmc | 200         | OK             |
  | x3000c0s28b2 | NodeBMC   | Random, domain: bmc | 200         | OK             |
  | x3000c0s15b0 | NodeBMC   | Random, domain: bmc | 200         | OK             |
  ...


SEE ALSO
========

sat(8)

.. include:: _notice.rst
