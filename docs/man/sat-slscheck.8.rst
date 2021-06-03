=============
 SAT-SLSCHECK
=============

-----------------------------------------
Perform a Cross-Check Between SLS and HSM
-----------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **slscheck** [options]

DESCRIPTION
===========

The slscheck subcommand performs a cross-check between the
System Layout Service (SLS) and the Hardware State Manager (HSM) to verify
that the components in SLS were actually discovered and are present in HSM.

If no optons are specified, the subcommand will report all items which
are in SLS and not in HSM components or HSM Redfish endpoints.
It will also report component class, role, and subrole mismatches.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print a usage summary and exit.

**-c, --checks**
        Limit the checks of SLS components to the cross-checks listed.
        The default is to perform all cross-checks.  Allowed checks
        are **Class**, **Component**, **RFEndpoint**, and **Role**.
        This argument may be reused to select more than one check.

**-t, --types**
        Limit the types of SLS components to the types listed.
        The default is to cross-check all types.  Allowed types
        are **CabinetPDUController**, **ChassisBMC**, **Node**,
        **NodeBMC**, and **RouterBMC**. This argument may be reused
        to select more than one type.

**-i, --include-consistent**
        Include list of SLS components that are consistent with
        HSM components.  The default is False.

.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

Show all inconsistencies between SLS and HSM:

::

  # sat slscheck
  +----------------+----------------------+-----------+-------------+-------------+-------------------------------------------+
  | xname          | SLS Type             | SLS Class | SLS Role    | SLS Subrole | Comparison Result                         |
  +----------------+----------------------+-----------+-------------+-------------+-------------------------------------------+
  | x1000c0s1b1n0  | Node                 | Mountain  | Compute     | MISSING     | Role mismatch: SLS:Compute,HSM:Management |
  | x3000c0s1b0    | NodeBMC              | River     | MISSING     | MISSING     | SLS component missing in HSM Components   |
  | x3000m0        | CabinetPDUController | River     | MISSING     | MISSING     | Class mismatch: SLS:River,HSM:MISSING     |
  +----------------+----------------------+-----------+-------------+-------------+-------------------------------------------+

Show all mismatches between SLS and HSM component class:

::

  # sat slscheck --check Class
  +---------+----------------------+-----------+---------------------------------------+
  | xname   | SLS Type             | SLS Class | Comparison Result                     |
  +---------+----------------------+-----------+---------------------------------------+
  | x3000m0 | CabinetPDUController | River     | Class mismatch: SLS:River,HSM:MISSING |
  +---------+----------------------+-----------+---------------------------------------+

Show all inconsistencies between SLS and HSM for NodeBMCs:

::

  # sat slscheck --type NodeBMC
  +-------------+----------+-----------+-----------------------------------------+
  | xname       | SLS Type | SLS Class | Comparison Result                       |
  +-------------+----------+-----------+-----------------------------------------+
  | x3000c0s1b0 | NodeBMC  | River     | SLS component missing in HSM Components |
  +-------------+----------+-----------+-----------------------------------------+


SEE ALSO
========

sat(8)

.. include:: _notice.rst
