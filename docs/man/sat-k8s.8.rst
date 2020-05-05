=========
 SAT-K8S
=========

-----------------
Kubernetes Status
-----------------

:Author: Cray Inc.
:Copyright: Copyright 2020 Hewlett Packard Enterprise Development LP.
:Manual section: 8

SYNOPSIS
========

**sat** [global-opts] **k8s** [options]

DESCRIPTION
===========

This command reports a summary of the health of Kubernetes on the system
where it was run. Options may be specified to provide additional details for
the summary.

OPTIONS
=======

These options must be specified after the subcommand.

**--co-located-replicas**
        Display any pods within a replicaset that are co-located on the same
        node, which may reduce resiliency in the event that the node fails.

.. include:: _sat-format-opts.rst
.. include:: _sat-filter-opts.rst

EXAMPLES
========

The base command prints a summary.

::

    # sat k8s
    Summary: There were 8 replica pods that were running on the same node.

Print detailed information about pod names and which nodes are hosting
duplicate replicas.

::

    # sat k8s --co-located-replicas
    +--------------+------------------------------------+----------+------------------------------------------+
    | namespace    | replicaset                         | node     | pods                                     |
    +--------------+------------------------------------+----------+------------------------------------------+
    | istio-system | istio-ingressgateway-84b5cf9b84    | ncn-w001 | istio-ingressgateway-84b5cf9b84-lk42h    |
    |              |                                    |          | istio-ingressgateway-84b5cf9b84-lmpdz    |
    | istio-system | istio-ingressgateway-84b5cf9b84    | ncn-w003 | istio-ingressgateway-84b5cf9b84-srvqw    |
    |              |                                    |          | istio-ingressgateway-84b5cf9b84-vsmdj    |
    | istio-system | istio-ingressgateway-hmn-6cd7949bc | ncn-w002 | istio-ingressgateway-hmn-6cd7949bc-76l42 |
    |              |                                    |          | istio-ingressgateway-hmn-6cd7949bc-brxdp |
    | istio-system | istio-pilot-f88bf9c74              | ncn-w001 | istio-pilot-f88bf9c74-2b28z              |
    |              |                                    |          | istio-pilot-f88bf9c74-g7qpm              |
    | opa          | cray-opa-859b4545b9                | ncn-w003 | cray-opa-859b4545b9-j4vhp                |
    |              |                                    |          | cray-opa-859b4545b9-jmp4m                |
    | services     | cray-rm-pals-66894d47b8            | ncn-w002 | cray-rm-pals-66894d47b8-gdvr9            |
    |              |                                    |          | cray-rm-pals-66894d47b8-j4ksw            |
    | services     | cray-sts-7c88b77b5d                | ncn-w003 | cray-sts-7c88b77b5d-6z6nn                |
    |              |                                    |          | cray-sts-7c88b77b5d-qrccm                |
    | services     | cray-tftp-588fb987c4               | ncn-w002 | cray-tftp-588fb987c4-lc7xj               |
    |              |                                    |          | cray-tftp-588fb987c4-ls58x               |
    | sma          | sma-postgres-persister-6b6674889b  | ncn-w002 | sma-postgres-persister-6b6674889b-g6h4k  |
    |              |                                    |          | sma-postgres-persister-6b6674889b-qmvct  |
    +--------------+------------------------------------+----------+------------------------------------------+

SEE ALSO
========

sat(8)

.. include:: _notice.rst
