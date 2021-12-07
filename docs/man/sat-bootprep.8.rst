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

**--input-file INPUT_FILE**
        The path to a YAML input file that defines the CFS configuration(s) to
        create, the IMS image(s) to build and/or customize, and the BOS session
        templates to create.

        For full details on the schema for the bootprep input file, see the
        FILES section below.

**--view-input-schema**
        View the input file schema in json-schema format.

        The input file schema is passed as stdin to the pager specified with the
        `PAGER` environment variable. If no pager is specified, `less -is` is
        used by default.

**--generate-schema-docs OUTPUT_FILE**
        Create a tarball containing documentation for the input file schema in
        HTML format. The documentation is written to a gzipped tar file
        specified by the path given by **OUTPUT_FILE**. The documentation is
        viewable by using a web browser of choice to open `index.html` found in
        the tarball.

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
