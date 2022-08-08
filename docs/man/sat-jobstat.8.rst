=============
 SAT-JOBSTAT
=============

-------------------------
Jobstat Short Description
-------------------------

:Author: Hewlett Packard Enterprise Development LP.
:Copyright: Copyright 2022 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **jobstat** [options]

DESCRIPTION
===========

Jobstat is a command that allows a user or admin to access application and job data via the command line. The command provides a table showing the user the apid, jobid, user, state, and time-reported of all jobs on the system.

OPTIONS
=======

These options must be specified after the subcommand.

**-h, --help**
        Print the help message for 'sat jobstat'.

**-a, --all**
        Show all application information that is currently documented on the system.

Summarize Remaining Options

EXAMPLES
========

An example usage of the command:

::

    # sat jobstat
+---------------------------------------+--------------+-------+-------------------------------------+-----------+-----------+---------------------+
| apid                                  | jobid        | user  | command                             | state     | num_nodes | node_list           |
+---------------------------------------+--------------+-------+-------------------------------------+-----------+-----------+---------------------+
| 7677b7d3-ec35-4e23-8678-92b823347939  | 49.pbs-host  | 5827  | mpiexec --ppn=1 -n2 ./signals       | completed | 2         | nid000001,nid000002 |
| 76b783af-5c7e-4462-97c0-3dfd0f04b9b3  | 51.pbs-host  | 5827  | mpiexec --ppn=1 -n2 ./signals       | completed | 2         | nid000001,nid000002 |
| 7a85c000-05a9-40cd-8551-00092cead801  | 48.pbs-host  | 5827  | mpiexec -n2 ./signals               | completed | 1         | nid000001           |
| 8b5b14b3-8215-4cbe-bba4-7d7c82d48fef  | 50.pbs-host  | 5827  | mpiexec --ppn=1 -n2 ./signals       | completed | 2         | nid000001,nid000002 |
| 957bbd4c-de3c-424d-99d6-fd2b728b2941  | 54.pbs-host  | 5827  | mpiexec --ppn=1 -n2 ./signals       | completed | 2         | nid000001,nid000002 |
| ba977b71-40b6-40db-aa20-a583edc18be3  | 59.pbs-host  | 5827  | mpiexec --ppn=1 -n2 ./signals-sleep | completed | 2         | nid000001,nid000002 |
| fea2726a-c531-4acd-b158-3fae197999dd  | 57.pbs-host  | 5827  | mpiexec --ppn=1 -n2 ./signals       | completed | 2         | nid000001,nid000002 |
+---------------------------------------+--------------+-------+-------------------------------------+-----------+-----------+---------------------+

SEE ALSO
========

sat(8)

.. include:: _notice.rst
