# Documentation in SAT

All ``sat`` man pages are written in reStructuredText (rst) format and are
converted to man format using the Python program ``rst2man.py`` from the
``docutils`` Python package.

The top-level ``sat`` command has its own man page which describes the ``sat``
command-line utility at a high level, documents the global options accepted by
``sat``, documents the configuration file and its options, and refers the reader
to the individual man pages for each subcommand.

Each subcommand has its own man page that describes the usage of that subcommand
including the options that are specific to that subcommand.

## Guidelines for Subcommand Man Pages

Each subcommand man page should follow these guidelines to ensure that all
subcommands are documented clearly and consistently.

### File Naming and Location

The man page rst file for a subcommand should be named ``sat-SUBCOMMAND.8.rst``
and should be located in ``docs/man/`` within this repository, where
``SUBCOMMAND`` is the name of the subcommand.

### Man Page Makefile

When creating a new man page, ensure it is added to the ``all`` target in
``docs/man/Makefile``.

### Man Page Headers

A subcommand's man page should begin with a title, short description, and
required HEADER information. For example, for a subcommand named ``subcommand``:

    ================
     SAT-SUBCOMMAND
    ================
    
    --------------------------------------------------
    Short description of subcommand in the imperative.
    --------------------------------------------------
    
    :Author: Hewlett Packard Enterprise Development LP.
    :Copyright: Copyright <YEAR> Hewlett Packard Enterprise Development LP.
    :Manual section: 8

Be sure to replace the ``<YEAR>`` above with the correct year.

### Man Page Sections

Each man page should have the following sections in this order: 

* ``SYNOPSIS``
* ``DESCRIPTION``
* ``OPTIONS``
* ``FILES`` (optional)
* ``EXAMPLES`` (optional but recommended)
* ``SEE ALSO``

See the existing man pages in ``docs/man/`` for examples.

### Format of Examples in ``EXAMPLES`` Section

The ``EXAMPLES`` section of each man page should be structured consistently with
other subcommands so that users can easily understand each example. Each example
should be introduced by a short sentence or paragraph describing the example,
and then the example should be shown in a pre-formatted code block with the
command-line prompt indicated by an octothorpe symbol and a space (``# ``). The
example output of the command can be shown without a leading octothorpe. If the
output would be excessively long, it can be truncated or omitted.

For example:

    Get all the items from the foo service that are in the kitchen::
    
            # sat foo --list-items --filter location=kitchen
            +-----------+----------+-----------+
            | name      | location | color     |
            +-----------+----------+-----------+
            | stove     | kitchen  | black     |
            | fridge    | kitchen  | white     |
            | microwave | kitchen  | stainless |
            +-----------+----------+-----------+

### See Also Links

Each man page should mention the top-level ``sat`` man page in its ``SEE ALSO``
section, and it should be included in the ``SEE ALSO`` section of the top-level
man page at ``docs/man/sat.8.rst``.

### Copyright Notice

Each man page should include the copyright and license text notice at the end of
the file as shown below:

    .. include:: _notice.rst

## Building and Viewing Man Pages

To build and view man pages, the Python ``docutils`` package must be installed
in your environment. Then you can run ``make`` in ``docs/man/``. This will
run ``rst2man.py`` on all rst files that have changed and generate the
corresponding man pages. For example:

    (sat) user@local-mbp man $ make
    rst2man.py sat-bootsys.8.rst sat-bootsys.8
    ...

Then you can view them with ``man`` and the path to the man page. Note that you
must use a preceding ``./`` on the path for man to recognize the argument as a
path to a man page file rather than the name of a man page.

    (sat) user@local-mbp man $ man ./sat-bootsys.8
