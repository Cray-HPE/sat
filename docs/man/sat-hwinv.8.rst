===========
 SAT-HWINV
===========

-----------------------------------------------------
Display hardware inventory information for the system
-----------------------------------------------------

:Author: Cray Inc.
:Copyright: Copyright 2019 Cray Inc. All Rights Reserved.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **hwinv** [options]

DESCRIPTION
===========

The hwinv subcommand displays hardware inventory information for the system as
reported by the Hardware State Manager (HSM). This subcommand provides summaries
and listings of all component types known by the HSM.

In the summary output, each type of component is categorized by the values for a
given field. In list output, information about the components of each type is
displayed in a tabular format. Options can be used to control which types of
components are summarized, by which attributes each component type is
summarized, which types of components are listed, and which fields are displayed
for each component type. Both YAML and a human-readable, or "pretty", format are
supported.

The default behavior of this subcommand is to display summaries and lists of all
component types in the system in pretty format. That is, the default behavior is
equivalent to the following invocation::

        sat hwinv --summarize-all --list-all

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat hwinv'.

The following two categories describe the "summarize" and "list" options.
The "summarize" options describe the options that control the summarizing of
components, and the "list" options describe the options that control the
listing of components. Multiple "summarize" and "list" options can be combined
to display multiple views of hardware inventory at once.

SUMMARIZE OPTIONS
-----------------
These options summarize components of certain types in the system by a given
list of fields. For each field, components are grouped into categories based on
their values for that field, and then a count and an optional full listing of
the components in each category is displayed. Whether the full listing of
components in each category is shown depends on the value of the relevant
**--show-\*-xnames** option for the component type.

**--summarize-all**
        Summarize all the components in the system. This is equivalent to specifying
        all the other **--summarize-<component>** options at once.

**--summarize-nodes**
        Summarize the nodes in the system by the values of the given fields.

**--summarize-procs**
        Summarize the processors in the system by the values of the given
        fields.

**--summarize-mems**
        Summarize the memory modules in the system by the values of the given
        fields.

**--node-summary-fields** *NODE_SUMMARY_FIELDS*
        Summarize the nodes by the given comma-separated list of fields. Omit
        this option to summarize by all fields. This option only has an effect
        if nodes are being summarized by the **--summarize-nodes** or
        **--summarize-all** options.

        Fields are not case-sensitive, and spaces in the field name can be
        replaced with underscores. In addition, a subsequence can be specified,
        and all fields that contain that subsequence will be used. A subsequence
        of a field name is a value that can be obtained by deleting characters
        from the field name while maintaining order. It is more permissive than
        a substring.

**--proc-summary-fields** *PROC_SUMMARY_FIELDS*
        Same as **--node-summary-fields** but for processors.

**--mem-summary-fields** *MEM_SUMMARY_FIELDS*
        Same as **--node-summary-fields** but for memory modules.

**--show-node-xnames** *[on|off]*
        Specify 'on' or 'off' to show or hide node xnames in node summaries.
        This only has an effect if nodes are being summarized by the
        **--summarize-nodes** or **--summarize-all** options. Defaults to
        **on**.

**--show-proc-xnames** *[on|off]*
        Like **--show-node-xnames** but for processors. Defaults to **off**.

**--show-mem-xnames** *[on|off]*
        Like **--show-node-xnames** but for memory modules. Defaults to **off**.

LIST OPTIONS
------------
These options list components of certain types in the system.

**--list-all**
        List all the components in the system. This is equivalent to specifying
        all the other **--list-<component>** options at once

**--list-nodes**
        List all the nodes in the system.

**--list-chassis**
        List all the chassis in the system.

**--list-hsn-boards**
        List all the HSN boards in the system. These are all the HSN switches in
        the system.

**--list-compute-modules**
        List all the compute modules in the system. These are the compute blade
        slots in liquid-cooled cabinets.

**--list-router-modules**
        List all the router modules in the system. These are the HSN switch
        slots in liquid-cooled cabinets.

**--list-node-enclosures**
        List all the node enclosures in the system. These are the enclosures for
        nodes in air-cooled cabinets. For nodes in liquid-cooled cabinets, these represent
        the node card associated with two of the nodes in a slot.

**--list-procs**
        List all the processors in the system.

**--list-mems**
        List all the memory modules in the system.

**--node-fields** *NODE_FIELDS*
        Display the given comma-separated list of fields for each node. Omit
        this option to display all fields. This option only has an effect if
        nodes are being listed by the **--list-all** or **--list-nodes** option.

        Fields are not case-sensitive, and spaces in the field name can be
        replaced with underscores. In addition, a subsequence can be specified,
        and all fields that contain that subsequence will be displayed. A
        subsequence of a field name is a value that can be obtained by deleting
        characters from the field name while maintaining order. It is more
        permissive than a substring.

**--chassis-fields** *CHASSIS_FIELDS*
        Same as **--node-fields** but for chassis.

**--hsn-board-fields** *HSN_BOARD_FIELDS*
        Same as **--node-fields** but for HSN boards.

**--compute-module-fields** *COMPUTE_MODULE_FIELDS*
        Same as **--node-fields** but for compute modules.

**--router-module-fields** *ROUTER_MODULE_FIELDS*
        Same as **--node-fields** but for router modules.

**--node-enclosure-fields** *NODE_ENCLOSURE_FIELDS*
        Same as **--node-fields** but for node enclosures.

**--proc-fields** *PROC_FIELDS*
        Same as **--node-fields** but for processors.

**--mem-fields** *MEM_FIELDS*
        Same as **--node-fields** but for memory modules.

.. include:: _sat-format-opts.rst

EXAMPLES
========

List all the nodes in the system and include only the xname, processor
manufacturer, and memory size fields::

        sat hwinv --list-nodes --node-fields xname,processor_manufacturer,memory_size

List all processors and memory modules in the system and show only xname and
serial number for each::

        sat hwinv --list-procs --proc-fields xname,serial_number \
                  --list-mems --mem-fields xname,serial_number

Summarize nodes but only by the value of the cabinet type field, and show only
counts of the nodes in each category, not a full listing of xnames::

        sat hwinv --summarize-nodes --node-summary-fields cabinet_type \
                  --show-node-xnames off

Summarize all components and include xnames for the memory modules and
processors::

        sat hwinv --summarize-all --show-mem-xnames --show-proc-xnames

Summarize all nodes by all possible fields and get output in YAML format::

        sat hwinv --summarize-nodes --format yaml

Get a listing of all nodes, processors, and memory modules in the system,
displaying only their xnames and serial numbers, and providing output in YAML
format::

        sat hwinv --list-nodes --node-fields xname,serial \
                  --list-mems --mem-fields xname,serial \
                  --list-procs --proc-fields xname,serial \
                  --format yaml

Note that in the above example we are specifying the "Serial Number" field using
a prefix of that field name.

Summarize the nodes by information related to their processors, i.e. the
processor manufacturer and processor model::

        sat hwinv --summarize-nodes --node-summary-fields proc

List nodes and display only the node xnames and fields that start with mem and
proc, i.e. fields related to memory and processor information::

        sat hwinv --list-nodes --node-fields xname,proc,mem

SEE ALSO
========

sat(8)
