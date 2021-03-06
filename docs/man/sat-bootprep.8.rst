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

**sat** [global-opts] **bootprep** ACTION [options]

DESCRIPTION
===========

The bootprep command creates CFS configurations, builds IMS images, customizes
IMS images with CFS configurations, and creates BOS session templates which can
then be used to boot nodes in the system, such as compute and application nodes.

ARGUMENTS
=========

**ACTION**
        Specify the action for sat bootprep to execute. This should be ``run``,
        ``generate-docs``, ``generate-example``, or ``view-schema``.

        **run**
                Process an input file, creating CFS configurations, building and
                customizing IMS images, and creating BOS session templates as
                specified in the input file.

        **generate-docs**
                Generate HTML documentation describing the input file schema and
                save it to a gzipped tar file.

        **generate-example**
                Generate an example input file which is an appropriate starting
                point for creating CFS configurations, IMS images, and BOS
                session templates for booting compute nodes and UANs in the
                system.

                The example is generated using hard-coded information about
                which products are expected to provide CFS configuration layers
                and IMS image recipes along with information from the
                cray-product-catalog Kubernetes ConfigMap in the services
                namespace.

                The example can be modified, and the file can be renamed to more
                accurately reflect its contents.

        **view-schema**
                Print the raw JSON Schema definition which is used to validate
                the schema of input files given to the ``run`` action.
    

RUN ARGUMENTS
-------------

This argument only applies to the ``run`` action.

**INPUT_FILE**
        The path to a YAML input file that defines the CFS configuration(s) to
        create, the IMS image(s) to build and/or customize, and the BOS session
        templates to create.

        For full details on the schema for the bootprep input file, use the
        ``generate-docs`` or ``view-schema`` actions.

OPTIONS
=======

These options apply to multiple actions.

**-h, --help**
        Print the help message for 'sat bootprep'.

**--output-dir OUTPUT_DIR, -o OUTPUT_DIR**
        The directory to which created files should be written. Files are
        created by the ``--save-files`` option in the ``run`` action and by the
        ``generate-docs`` and ``generate-examples`` actions. If not specified,
        then the working directory is used. This option is not valid with the
        ``view-schema`` action.


RUN OPTIONS
-----------

These options only apply to the ``run`` action.

**-s, --save-files**
        Save files that could be passed to the CFS and BOS to create CFS
        configurations and BOS session templates, respectively. If
        ``--dry-run`` is specified, then only files for CFS configurations will
        be saved.

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

**--delete-ims-jobs**
        Delete IMS jobs after creating images. Note that deleting IMS jobs makes
        determining image history impossible.

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

        # sat bootprep run bootprep_input.yaml

View the exact input file schema specification:

::

        # sat bootprep view-schema

Generate HTML documentation for the input file schema:

::

        # sat bootprep generate-docs

Generate an example bootprep input file:

::

        # sat bootprep generate-example

SEE ALSO
========

sat(8)

.. include:: _notice.rst
