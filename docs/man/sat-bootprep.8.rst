==============
 SAT-BOOTPREP
==============

----------------------------------------------------
Prepare to boot nodes with images and configurations
----------------------------------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2021 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **bootprep** INPUT_FILE [options]

DESCRIPTION
===========

The bootprep command creates CFS configurations, builds IMS images, customizes
IMS images with CFS configurations, and creates BOS session templates which can
then be used to boot nodes in the system, such as compute and application nodes.

ARGUMENTS
=========

**INPUT_FILE**
        The path to a YAML input file that defines the CFS configuration(s) to
        create, the IMS image(s) to build and/or customize, and the BOS session
        templates to create.

        For full details on the schema for the bootprep input file, see the
        FILES section below.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat bootprep'.

FILES
=====

TODO (CRAYSAT-1129): Provide documentation for the bootprep config file schema.

EXAMPLES
========

Create the CFS configurations, build and customize IMS images, and create BOS
session templates as described in the configuration file, ``bootprep_input.yaml``:

::

        # sat bootprep bootprep_input.yaml

SEE ALSO
========

sat(8)

.. include:: _notice.rst
