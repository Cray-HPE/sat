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

        By default, the input file schema is written to stdout. If the
        `SAT_PAGER` environment variable is set, then the input file schema will
        be written to the stdin of the given executable.

**--generate-schema-docs**
        Create a tarball containing documentation for the input file schema in
        HTML format. The documentation is written to a file named
        **bootprep-schema-docs.tar.gz** in the directory specified by the path
        given by **--output-dir**. The documentation is viewable by using a web
        browser to open `index.html` found in the tarball.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat bootprep'.

**-s, --save-files**
        Save files that could be passed to the CFS and BOS to create CFS
        configurations and BOS session templates, respectively.

**--output-dir OUTPUT_DIR, -o OUTPUT_DIR**
        The directory to which files created by the ``--save-files`` and
        ``--generate-schema-docs`` options should be written. If not specified,
        then the current working directory is used.

**--no-resolve-branches**
        Do not look up the HEAD commits of branches name before creating CFS
        configurations. By default, if a branch is specified in a configuration
        layer in the bootprep input file, the HEAD commit of the branch will be
        looked up from the corresponding git repository. If
        ``--no-resolve-branches`` is specified, then the branch name will be
        passed directly to CFS when the configuration is created. CFS determines
        the commit hash for the HEAD of this branch and stores both the branch
        name and commit hash in the layer of the configuration. CFS can use the
        branch name to update the commit hash to the latest HEAD of the branch
        if requested.

**--skip-existing-configs**
        Skip creating any configurations for which a configuration with the same
        name already exists.

**--overwrite-configs**
        Overwrite any configurations for which a configuration with the same
        name already exists.

**--skip-existing-images**
        Skip creating any images for which an image with the same name already
        exists.

**--overwrite-images**
        Overwrite any images for which an image with the same name already
        exists.

**--skip-existing-templates**
        Skip creating any session templates for which a session template with
        the same name already exists.

**--overwrite-templates**
        Overwrite any session templates for which a session template with the
        same name already exists.

**--public-key-file-path PUBLIC_KEY_FILE_PATH**
        The SSH public key file to use when building images with IMS. If neither
        ``--public-key-file-path`` nor ``--public-key-id`` is specified, the default is
        to use the public key located at ~/.ssh/id_rsa.pub.

**--public-key-id PUBLIC_KEY_ID**
        The id of the SSH public key stored in IMS to use when building images
        with IMS. If neither ``--public-key-file-path`` nor ``--public-key-id`` is
        specified, the default is to use the public key located at
        ~/.ssh/id_rsa.pub.

EXAMPLES
========

Create the CFS configurations, build and customize IMS images, and create BOS
session templates as described in the configuration file, ``bootprep_input.yaml``:

::

        # sat bootprep --input-file bootprep_input.yaml

View the exact input file schema specification:

::

        # sat bootprep --view-input-schema

Browse documentation for the input file schema:

::

        # sat bootprep --generate-schema-docs

SEE ALSO
========

sat(8)

.. include:: _notice.rst
