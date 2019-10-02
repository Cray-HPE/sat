===========
 SAT-STATUS
===========

----------------
Show node status
----------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **status** [options]

DESCRIPTION
===========

The status subcommand reports the status of nodes on a Shasta system. Node
status is displayed in tabular format, with a row for each node, and columns
corresponding to the identities and conditions of the nodes.

OPTIONS
=======

These options must be specified after the command.

**-s, --sort-column**
        Sort by the selected column. The default is to sort by xname.
        May be specified by the (case insensitive) column, or by index
        (starting at 1). The column can be abbreviated if unambiguous.
        If an ambiguous abbreviation is given, the first matching column
        will be selected.
        Some columns may contain whitespace. If whitespace is necessary
        to unambiguously single out such a column, the whitespace may be
        included by wrapping the column name or abbreviation in quotes.

**-r, --reverse**
        Reverses the order of the nodes.

**-x, --xnames**
        Selects nodes to report from a comma-separated list of xnames, or a single
        xname. Any case may be used, and leading zeros from the integer parts will
        be removed before matching. May be used with **--nids**.

**-n, --nids**
        Selects nodes to report from a comma-separated list of NIDs, or a single
        NID. May be used with **--xnames**.

**-h, --help**
        Print a usage summary and exit.


SEE ALSO
========

sat(8)
